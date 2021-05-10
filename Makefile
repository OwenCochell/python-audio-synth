CC ?= gcc
CFLAGS = -lasound
ALSAROOT = pysynth/wrappers/midi/alsa

# object files to generate
OBJ = \
      ${ALSAROOT}/midi_alsa.o

all: ${OBJ} ${ALSAROOT}/midi_alsa.so

${ALSAROOT}/midi_alsa.o: ${ALSAROOT}/midi_alsa.c
	${CC} -fPIC -c ${ALSAROOT}/midi_alsa.c -o ${ALSAROOT}/midi_alsa.o ${CFLAGS}

${ALSAROOT}/midi_alsa.so: ${OBJ}
	${CC} -shared -o ${ALSAROOT}/midi_alsa.so ${OBJ} ${CFLAGS}

clean:
	rm -f ${ALSAROOT}/*.o
