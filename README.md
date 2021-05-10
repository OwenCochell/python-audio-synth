# python-audio-synth
A work in progress modular mono synth written in python

# Disclaimer

This is a huge work in progress!

Some features may not run well, break, or do something unexpected.

We expect pyaudio to be installed if the audio is going to be played over the speakers.

Some parts of this project are written in C code,
for speed purposes as well as functionality.

You can use make to build the necessary C files.
To do this, run make in the root directory like so:

>make

To clean unecessary object files:

>make clean
