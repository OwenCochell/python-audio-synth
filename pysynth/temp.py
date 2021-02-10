"""
Random test stuff
"""

from pysynth.utils import *
from pysynth.osc import *
from pysynth.synth import *
from pysynth.filters import *
from pysynth.output.base import OutputHandler
from pysynth.output.modules import *
from pysynth.wrappers import querty

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

    audio = AudioValue(500.0, 0, 1000)
    audio.add_event(ExponentialRamp, 800.0, get_time()+10)
    audio.add_event(LinearRamp, 900.0, get_time()+20)

    while True:

        print(audio.value)
        #time.sleep(1)


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

    # Get controller for sine wave oscillator:

    sine = out.bind_synth(SineOscillator(440.0))
    square = out.bind_synth(SquareOscillator(440.0))
    saw = out.bind_synth(SawToothOscillator(440.0))
    tri = out.bind_synth(TriangleOscillator(440.0))

    # Add sine oscillator for default instrument:

    sequencer.add_synth(sine, name=0)
    sequencer.add_synth(square, name=1)
    sequencer.add_synth(saw, name=2)
    sequencer.add_synth(tri, name=3)

    # Start the output handler:

    out.start()

    # Start the sequencer:

    sequencer.start()
    sequencer.stop()
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
