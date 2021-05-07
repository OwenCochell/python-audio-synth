"""
Random test stuff
"""

from pysynth.seq import Sequencer
from pysynth.utils import *
from pysynth.osc import *
from pysynth.synth import *
from pysynth.filters import *
from pysynth.output.base import OutputHandler
from pysynth.output.modules import *
from pysynth.wrappers import querty, mml
from pysynth.wrappers.midi import midi
from pysynth.envelope.amp import *

import time
import pyaudio
import threading
import struct
import wave
import math
import os
import copy

from tkinter import Tk, Frame

BITRATE = 16000
#MAX_AMPLITUDE = 32767.0
#MAX_AMPLITUDE = 127.0

paudio = pyaudio.PyAudio()
stream = paudio.open(format=pyaudio.paFloat32,
                     channels=1,
                     output=True,
                     rate=44100)


def type_test():

    # Tests the audio type test

    audio = AudioValue(0.5, 0, 1000)
    #audio.add_event(ExponentialRamp, 800.0, get_time()+10000000000)
    #audio.add_event(LinearRamp, 500.0, get_time()+20000000000)

    #audio.add_event(ExponentialRamp, 800.0, get_time()+10)
    #audio.add_event(LinearRamp, 500.0, get_time()+20)

    #audio.exponential_ramp(0, get_time() + 2000000000)

    audio.linear_ramp(1, get_time() + 1000000000)

    audio.cancel_all_events()

    audio.linear_ramp(0, get_time() + 2000000000)

    while True:

        thing = audio.value

        print(thing)

        if thing == 0:

            break

        time.sleep(0.01)


def start_stream(osc):

    """
    Starts the audio thread and starts streaming data
    """

    thread = threading.Thread(target=stream_data, args=[osc])
    thread.daemon = True
    thread.start()

    return thread


def stream_data(data, time=None):

    """
    Streams data to PyAudio.
    Data is a oscillator we iterate over

    :param data: Data to stream
    """

    for num, i in enumerate(data):

        #print(i)

        stream.write(struct.pack('f', i))

        if time and num > time:

            # We are done

            return


def write_wave(data, seconds):

    """
    Writes a specified amount of wave data:
    :param data: Data to write
    :param seconds: Seconds to write
    """

    # Open the wave file:

    wav = wave.open('blorck.wav', 'wb')

    wav.setnchannels(1)
    wav.setsampwidth(4)
    wav.setframerate(44100.0)

    iter(data)

    for i in range(44100*seconds):

        value = next(data)

        wav.writeframesraw(struct.pack('<f', value))

    wav.close()


class KeyboardHandler:

    """
    Handles keyboard input, removing and adding
    oscillators to an AudioCollection as necessary.
    """

    def __init__(self, aud, keys):

        self.aud = aud  # Audio collection to maintain
        self.keys = keys  # Mapping keys to oscillators.

        # Mapping keys to oscillators to generate

        self.osc_keys = {'z': SineOscillator, 'x': SquareOscillator, 'c': SawToothOscillator, 'v': TriangleOscillator}

    def remove_key(self, key):

        """
        Removes an oscillator from the AudioCollection.

        :param key: Oscillator to remove
        """

        print("Removed key: {}".format(key.keysym))

        if key.keysym in self.osc_keys:

            # DO nothing,

            return

        if self.keys[key.keysym] not in self.aud._objs:

            # Nothing, return

            return

        self.aud.remove_module(self.keys[key.keysym])

    def add_key(self, key):

        """
        Adds an oscillator from the AudioCollection.

        :param key: Oscillator to add
        """

        print("Added Key: {}".format(key.char))

        if key.char in self.osc_keys:

            # Generate a new oscillator mp

            self.keys = gen_oscs(self.osc_keys[key.char])

            return

        if self.keys[key.char] in self.aud._objs:

            # Nothing, return

            return

        self.aud.add_module(self.keys[key.char])


def gen_oscs(osc):

    """
    Generates a list of oscillators
    :param osc: Oscillator to use to generate our list
    :return: List of keys mapped to oscillators
    """

    oscs = {}
    keys = ['q', 'a', 'w', 's', 'e', 'd', 'r', 'f', 't', 'g', 'y', 'h', 'u', 'j', 'i', 'k', 'o', 'l', 'p']

    # Generating oscillators and mapping them to keys:

    for note in range(-17, 2):

        oscs[keys[note+17]] = osc()
        oscs[keys[note + 17]].freq = 440 * (2 ** (1 / 12)) ** note
        iter(oscs[keys[note + 17]])

    return oscs


def old_keyboard_input():

    """
    Maps certain keys to a keyboard,
    and adding the notes as we press/release keys.
    """

    oscs = gen_oscs(SineOscillator)

    print(oscs)

    # Create AudioCollection for output

    collec = AudioCollection()
    collec.add_module(ZeroOscillator())

    # Create KeyBoardHandler:

    hand = KeyboardHandler(collec, oscs)

    # Start streaming the AudioCollection:

    start_stream(collec)

    # Disabling continuous keypresses:

    os.system("xset r off")

    # Creating TKinter data:

    root = Tk()
    f = Frame(root, width=100, height=100)
    f.bind("<KeyPress>", hand.add_key)
    f.bind("<KeyRelease>", hand.remove_key)
    f.pack()
    f.focus_set()
    root.mainloop()

    os.system("xset r on")


def pitch_comp(osc):

    """
    Tests the pitch of the incoming oscillator.
    :param osc:
    """

    sine = SineOscillator(freq=osc.freq.value)

    print("Pitch One:")

    stream_data(sine, time=220500)

    print("Pitch Two:")

    stream_data(osc, time=220500)


def chord_test():

    """
    Tests if the additive synthesis is producing valid chords
    """

    osc1 = TriangleOscillator(freq=440.0)
    osc2 = TriangleOscillator(freq=880.0)
    osc3 = TriangleOscillator(freq=1320.0)
    osc4 = TriangleOscillator(freq=1760.0)

    thing = AudioCollection()

    thing.add_module(osc1, start=True)

    start_stream(thing)

    time.sleep(1)
    thing.add_module(osc2, start=True)
    time.sleep(1.5)
    thing.add_module(osc3, start=True)
    time.sleep(1.76)
    thing.add_module(osc4, start=True)


def avgfilt_test():

    """
    Tests Moving Average Filter
    """

    # Set up a sine wave:

    sine = SineOscillator()

    # Set up a filter:

    filter = MovingAverage(101)

    filter.bind(sine)

    sine.freq = 1234.0

    print(sine.freq.value)
    print(filter.freq.value)

    # Start the stream:

    start_stream(filter)


def fm_test():

    """
    Tests FM Synthesis
    """

    osc1 = SineOscillator(freq=440)
    osc2 = SineOscillator(freq=6160)

    oscmain = SineOscillator(freq=440)

    collec = AudioCollection()

    twomain = FMSynth(oscmain, osc2, 1)

    oneandtwo = FMSynth(twomain, osc1, 5)

    collec.add_node(oneandtwo)

    start_stream(twomain)


def keyboard_input():

    # Tests the QUERTY sequencer, and the QUERTYKeyboard input module.

    # Create the QWERTY wrapper

    sequencer = querty.QWERTYWrapper()

    # Create the output handler:

    out = OutputHandler()
    pyaudo = PyAudioModule()
    pyaudo.special = True
    out.add_output(pyaudo)

    #out.add_output(WaveModule("test_seq.wav"))

    # Configure for keyboard:

    sequencer.load_keyboard()

    attack = 1000000000
    decay = 1000000000
    sustain = 0.2
    release = 1000000000

    env1 = ADSREnvelope(attack, decay, sustain, release)
    env2 = ADSREnvelope(attack, decay, sustain, release)
    env3 = ADSREnvelope(attack, decay, sustain, release)
    env4 = ADSREnvelope(attack, decay, sustain, release)

    env1.bind(SineOscillator(440.0))
    env2.bind(SquareOscillator(440.0))
    env3.bind(SawToothOscillator(440.0))
    env4.bind(TriangleOscillator(440.0))

    # Get controller for sine wave oscillator:

    sine = out.bind_synth(env1)
    square = out.bind_synth(env2)
    saw = out.bind_synth(env3)
    tri = out.bind_synth(env4)

    # Add sine oscillator for default instrument:

    sequencer.add_synth(sine, name=0)
    sequencer.add_synth(square, name=1)
    sequencer.add_synth(saw, name=2)
    sequencer.add_synth(tri, name=3)

    # Start the output handler:

    out.start()

    # Start the sequencer:

    sequencer.start()
    sequencer.join()
    sequencer.stop()
    out.stop()


def freq_conv(num, middle_pitch=440.0):

    # Calculate and return the frequency of the note:

    return middle_pitch * pow(2, (((num) / 12)))


def mixing_test():

    # Tests mixing operations:

    pass


def mml_test():

    # Tests the MML wrapper

    #song = '$ t120 o4 l4 e f+ b > c+ d < f+ e > c+ < b f+ > d c+ <e f+ b > c+ d < f+ e > c+ < b f+ > d c+'
    #song = '$o4 c r e r g r b r;$o4 r d r f r a r <c'
    #song = 'o4 c d e f g a b <c d'

    #song = "o4 l1 ca"

    #song = "t60 l4 o4 /: [ceg] [fac]1 :/4"

    #song = "t92 l8 o4 [>cg<cea]2. [>cg<ceg]4 [>>a<a<c+fa+]2. [>>a<a<c+ea]4 " \
    #       "[>>f<fg+<cg]2. [>>f<fg+<cf]4 [>>g<gg+b<g+]2." \
    #       "[>>g<g<g]4 o3 l32 v6 cdef ga b<c de fg"

    #song = "t92 l4 o4 [>>a<a<c+fa+]"
    #song = 'o3 l32 v6 cdefgab<cdefg'
    #song = 't30 a'
    #song = "t92 [>>f<fg+<cg]2. [>>f<fg+<cf]4 [>>g<gg+b<g+]2. [>>g<g<g]4 o3 t92 l32 v6 cdef ga b<c de fg"
    #song = 't60 [>>g<g<g]4'

    #song = 't60 o3 l4 cdefgab<c> l8 cdefgab<c> l16 cdefgab l32 cdefgab'

    song1 = "t92 l8 o4 $ [>cg<cea]2. [>cg<ceg]4 [>>a<a<c+fa+]2. [>>a<a<c+ea]4 " \
           "[>>f<fg+<cg]2. [>>f<fg+<cf]4 [>>g<gg+b<g+]2. r4; " \
           "t92 $ l1 o3 v12 r r r r2 r8 l32 v6 cdef ga b<c de fg;"

    song = "t60 l4 o4 a+ r a+;" \
           "t60 l4 o4 r  r >a+"

    song = "t120$l8 o3 >g+2.. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <c4. >d+ a+ g+2. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <c2." 

    song = "t120$l8 o3 >g+2.. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <c4. >d+ a+ g+2. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <c2." 

    song = 't60 l1 a r8 a. r8 a.. r8 a...'


    song = "t105 l8 o5 q75 v100 " \
        "ab-> c4c4c4 c4.faf fedc<b-4 [gb-]2 [fa]4 agb-a>c<b- >c+dc<b-ag f2[ea]g f4r4" \
        "[fa][eg] [eg]2[gb-][fa] [fa]2>c<b b>dfd<b>d c4.<b-" \
        "ab-> c4c4c4 c4.faf fedc<b-4 [gb-]2 [fa]4 agb-a>c<b- >c+dc<b-ag f2[ea]g f4r4;" \
        "t105 l8 o4 q75 v75" \
        "r4 f>c<a>c<a>c< f>c<a>c<a>c< g>c<b->c<b->c< [e>c]2 [f>c]4 [b->d]2.^2 [<b->b-]4 [ca]2[cb-]4 [fa]4 <f4>" \
        "r4 c4>c4r4< c4>c4r4< [cdf]4[cdf]4[cdf]4 [ce]4r4" \
        "r4 f>c<a>c<a>c< f>c<a>c<a>c< g>c<b->c<b->c< [e>c]2 [f>c]4 [b->d]2.^2 [<b->b-]4 [ca]2[cb-]4 [fa]4 <f4>;" \


    song2 = "t120$l8 o4 v9rr g  g4  g+ a+4  d4  d4  d+2 d  c   g   g4 g+   a+4 d4 d4 d+2 rr g g4 g+ a+4 d4 d4 d+2 d c g g4 g+ a+4 d4 d4 d+2.;" \
           "t120$l8 o4 v9 rr d+ d+2 r  >a+4 a+4 <c2 >a+ g+ <d+ d+2 r  >a+4 a+4 a+2 rr d+ d+2 r >a+4 a+4 <c2 >a+ g+ <d+ d+2 r >a+4 a+4 a+2.;" \
           "t120$l8 o4 v9 rr c  c2  r  >f4  f4  g2  a+  g+ <c  c2 >f  f4   r   f g2< rr c c2 r >f4 f4 g2 a+ g+ <c c2 >f f4 r f g2.<;" \
           "t120$l8 o3 v8 >g+2.. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <c4. >d+ a+ g+2. g+ a+4. a+ <c2 >a+ g+2.. a+4 a+4 <r2." \

    #song = 't60 o3 l4 cdefgab<c> l8 cdefgab<c> l16 cdefgab l32 cdefgab'

    #song = '$ t120 o4 l4 e f+ b > c+ d < f+ e > c+ < b f+ > d c+ <e f+ b > c+ d < f+ e > c+ < b f+ > d c+'

    sec = mml.MMLWrapper()

    sec.load_string(song2)

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)


    # --== Instrument Selection: ==--
    # Uncomment the instrument you want to use!

    #osc = SineOscillator(freq=440.0)
    #osc = SquareOscillator(freq=440.0)
    osc = SawToothOscillator(freq=440.0)
    #osc = TriangleOscillator(freq=440.0)

    final = osc
    # --== End Instrument Selection! ==--

    # --== Other Output Options: ==--
    # Uncomment to write to a wav file:

    #wave = WaveModule('saw_test.wav')
    #out.add_output(wave)

    # --== End Other Output Options! ==--

    # --== ADSR Options: ==--
    # Configure the parameters for the ADSR envelope:

    attack = 10000000
    decay = 100000
    sustain = 0.2
    release = 5000000

    # Uncomment to enable the envelope:

    #env = ADSREnvelope(attack, decay, sustain, release)
    #env.bind(osc)
    #final = env

    # --== End ADSR Options! ==--

    amp = AmpScale()
    amp.bind(final)
    final = amp

    cont = out.bind_synth(final)

    sec.add_synth(cont)

    # Start output handler:

    out.start()

    # Start the sequencer:

    sec.start()
    sec.join()

    print("Done joining")

    print("Stopping sequencer...")

    sec.stop()

    print("Stopping output...")

    out.stop()


def delay():

    # Tests the delay function of OutputControl

    osc = TriangleOscillator(freq=440.0)

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)

    cont = out.bind_synth(osc)

    out.start()

    cont.start(time=3000000000 + get_time())

    cont.stop(time=5000000000 + get_time())

    time.sleep(8)

    out.stop()


def deepcopy():

    # Tests the deep copy of synths

    # OutputHandler:

    out = OutputHandler()

    # PyAudio module:

    pyaud = PyAudioModule()
    pyaud.special = True

    out.add_output(pyaud)

    osc = SineOscillator(freq=440.0)

    final = out.bind_synth(osc)

    # Make a deep copy:

    thing = copy.deepcopy(final)


def audio_param():

    # Tests the audio parameter as it alters the frequency of the pitch

    # Create a simple sine oscillator:

    osc = SineOscillator(freq=440)

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)

    sine = out.bind_synth(osc)

    out.start()

    # Start the oscillator:

    sine.start()

    # Have the frequency go up to 550 in 5 seconds:

    sine.info.freq.exponential_ramp(550.0, get_time()+5000000000)

    time.sleep(5)

    # Have the frequency go back down to 440 in 10 seconds:

    sine.info.freq.linear_ramp(440.0, get_time()+60000000000)

    sine.join()

    out.stop()


def test_output():

    # Creates and registers a oscillator. Used for testing output.

    osc1 = TriangleOscillator(freq=440.0)
    osc2 = TriangleOscillator(freq=880.0)
    osc3 = TriangleOscillator(freq=1320.0)
    osc4 = TriangleOscillator(freq=1760.0)

    out = OutputHandler()

    out.add_output(WaveModule("test.wav"))

    # Add the PyAudio module:

    pyaud = PyAudioModule()
    pyaud.special = True

    out.add_output(pyaud)

    # Add the WaveModule:

    # Bind the synth:

    final = out.bind_synth(osc1)
    final2 = out.bind_synth(osc2)
    final3 = out.bind_synth(osc3)
    final4 = out.bind_synth(osc4)

    # Start the OutputHandler:

    #out.start()

    # Start the synth:

    final.start()

    out.start()

    time.sleep(1)
    final2.start()

    time.sleep(1)
    final3.start()

    time.sleep(1)
    final4.start()

    time.sleep(1)

    final4.stop()
    time.sleep(1)
    final3.stop()
    time.sleep(1)
    final2.stop()
    time.sleep(3)
    final.stop()

    out.stop()


def module_connection():

    # Tests the connectivity features of modules

    mod1 = SineOscillator(freq=640.0)
    mod2 = DummyModule()
    mod3 = DummyModule()
    mod4 = DummyModule()

    mod2.bind(mod1)
    mod3.bind(mod2)
    mod4.bind(mod3)

    print("Connected modules: {}".format(mod4.info.connected))
    print("Should be 4!")

    print("Chain frequency: {}".format(mod4.info.freq))
    print("Should be 640.0!")


class DummyWait(BaseModule):

    """
    Passes values from the inputs attached,
    but continues to play for 5 seconds after we are released.
    """

    def __init__(self):

        super().__init__()

        self.finishing = False
        self.wait = 5000000000
        self.start_time = 0

    def start(self):
        
        self.finishing = False
        self.wait = 5000000000
        self.start_time = 0

    def finish(self):

        print("Dummy module finishing...")

        self.finishing = True

        self.start_time = get_time()

        print("Starting time: {}".format(self.start_time))

    def get_next(self):
        
        # Check if we are finishing

        if self.finishing:

            if get_time() > self.start_time + self.wait:

                # We are done, lets say we are finished:

                print("Dummy module done!")
                print("Current time: {}".format(get_time()))
                print("Target time: {}".format(self.start_time + self.wait))

                self.done()

                return None

        # Otherwise, lets just return the input:

        return self.get_input()


def fade_test():

    # Tests the ability for synths to continue to play after they have been stopped

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)

    osc = TriangleOscillator(freq=440.0)

    dummy = DummyWait()

    dummy.bind(osc)

    cont = out.bind_synth(dummy)

    sec = Sequencer()
    sec.add_synth(cont)

    print(cont.info.connected)
    print(cont.info.done)

    out.start()

    print("Starting controller...")

    cont.start()

    print("Waiting...")

    time.sleep(5)

    print("Stopping controller...")

    cont.stop()

    time.sleep(5)

    print(("Waiting..."))

    time.sleep(5)

    print("Synth should be stopped!")

    print("Starting synth...")

    cont.start()

    print("Waiting...")

    time.sleep(5)

    print("Stopping cont...")

    cont.stop()

    print("Waiting three seconds to interrupt...")

    time.sleep(3)

    print("Interrupting!")

    cont.start()

    cont.stop()

    print("Finished!")

    #sec.start()


def adsr_test():

    # Tests the ADSR envelope

    attack = 1000000000
    decay = 1000000000
    sustain = 0.5
    release = 1000000000

    # Create the OutputHandler:

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)

    osc = SawToothOscillator(freq=440.0)

    env = ADSREnvelope(attack, decay, sustain, release)

    env.bind(osc)

    cont = out.bind_synth(env)

    out.start()

    print("Starting:")

    cont.start()

    time.sleep(5)

    print("Stopping:")

    cont.stop()

    time.sleep(5)


def MIDI_test():

    # Tests if we can get MIDI info from ALSA

    out = OutputHandler()

    pyaud = PyAudioModule()
    pyaud.special = True
    out.add_output(pyaud)

    osc = SineOscillator(freq=440.0)
    #osc = SquareOscillator(freq=440.0)
    #osc = SawToothOscillator(freq=440.0)
    #osc = TriangleOscillator(freq=440.0)

    attack = 1000000000
    decay = 1000000000
    sustain = 0.2
    release = 1000000000

    env = ADSREnvelope(attack, decay, sustain, release)
    env.bind(osc)

    cont = out.bind_synth(env)

    seq = midi.MIDIWrapper()
    seq.alsa_live()

    seq.add_synth(cont)

    out.start()
    seq.start()

    seq.join()

    seq.stop()
    out.stop()
