#!/bin/bash

# Deleting exsiting files:

rm midi_alsa.o
rm midi_alsa.so

gcc -o midi_alsa.o -fPIC -c midi_alsa.c -lasound
gcc -o midi_alsa.so -shared midi_alsa.o -lasound
