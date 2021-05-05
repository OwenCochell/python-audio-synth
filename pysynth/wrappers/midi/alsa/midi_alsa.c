#include <alsa/asoundlib.h>

typedef struct ALSAEvent
{
    unsigned char type;
    //const unsigned char* raw_bytes;
    //unsigned char flags;
    unsigned int tick_time;
    unsigned int time_sec;
    unsigned int time_nano;
    unsigned char note;
    unsigned char velocity;
    unsigned char off_velocity;
    unsigned int duration;
    unsigned int param;
    signed int value;
    unsigned char channel;
} ALSAEvent;


static snd_seq_t *seq_handle;
static struct ALSAEvent event;
static int in_port;

#define CHK(stmt, msg) if ((stmt) < 0) {puts("ERROR: "#msg); exit(1);}
void midi_open(void) {
    CHK(snd_seq_open(&seq_handle, "default", SND_SEQ_OPEN_INPUT, 0),
        "Could not open sequencer!");

    CHK(snd_seq_set_client_name(seq_handle, "MIDI Listener"),
        "Could not set client name!");

    CHK(in_port = snd_seq_create_simple_port(seq_handle, "listen:in",
        SND_SEQ_PORT_CAP_WRITE|SND_SEQ_PORT_CAP_SUBS_WRITE,
        SND_SEQ_PORT_TYPE_APPLICATION),
        "Could not open port!");
}

snd_seq_event_t *midi_read_raw(void) {

    snd_seq_event_t *ev = NULL;
    snd_seq_event_input(seq_handle, &ev);
    return ev;
}

void create_pack(const snd_seq_event_t *ev) {
    
    /* Create the ALSAEvent: */

    event.type = ev->type;

    printf("Internal event type %d\n", event.type);

    //event.raw_bytes = ev->data.raw8.d;
    //event.flags = ev->flags;
    event.tick_time = ev->time.tick;
    event.time_sec = ev->time.time.tv_sec;
    event.time_nano = ev->time.time.tv_nsec;
    event.note = ev->data.note.note;
    event.velocity = ev->data.note.velocity;
    event.off_velocity = ev->data.note.off_velocity;
    event.duration = ev->data.note.duration;
    event.param = ev->data.control.param;
    event.value = ev->data.control.value;
    event.channel = ev->data.note.channel;

    printf("New event location %p\n", &event);

}

void midi_process(const snd_seq_event_t *ev) {

    printf("Event type: %d\n", ev->type);

    if ((ev->type == SND_SEQ_EVENT_NOTEON)
        ||(ev->type == SND_SEQ_EVENT_NOTEOFF)) {
            const char *type = (ev->type==SND_SEQ_EVENT_NOTEON) ? "on " : "off";
            printf("[%d] Note %s: %2x vel(%2x)\n", ev->time.tick,
                type,
                ev->data.note.note,
                ev->data.note.velocity);
        }
        else if(ev->type == SND_SEQ_EVENT_CONTROLLER)
            printf("[%d] Control: %2x val(%2x)\n", ev->time.tick,
                ev->data.control.param,
                ev->data.control.value);
        else
            printf("[%d] Unknown: Unhandled Event Received\n", ev->time.tick);
}


ALSAEvent *midi_read(void) {

    const snd_seq_event_t *thing = midi_read_raw();

    midi_process(thing);

    create_pack(thing);

    printf("--== ALSA Event data: ==--\n");
    printf("Type: %d\n", event.type);
    printf("Note: %d\n", event.note);

    return &event;

}

