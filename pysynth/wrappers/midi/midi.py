"""
Sequencer wrapper for the MIDI protocol.

We will be offering support for live MIDI control,
as well as MIDI playback from a file.

How will we get this MIDI info?
Don't know. As of now we are pulling events from ALSA,
but this is platform dependent.
Windows may have a diffrent method that we may use.
I would also like to read raw midi information from a bus,
but that may not be implemented.
We will see how this looks.

The MIDI wrapper will utilise the same format as the Sequencer.
The input module will get info from somewhere, convert it into a MIDI event,
and then pass it along to the decoder, which will handle and change the state of the Sequencer.
So, in actuality, the input module will be doing most of the decoding.
Go figure.

We have the following Input modules:
(* denotes a dependency, ! denotes not implemented yet)

    > ALSAInput - Gets MIDI data from the ALSA sequencer!
    > MIDIReader - Reads MIDI information from a file!

We have the following Decoder modules:

    > LiveDecoder - Changes the synth in real time!
    > PlaybackDecoder - Creates a SeqCommand based upon the given MIDI information!
    > MIDIDump - Does not alter the state of the synth, only prints/outputs MIDI event data somewhere!

We only focusing on reading MIDI information!
We will not attempt to send or transmit any MIDI info.
We also don't care about system information messages.
(Maybe, lets see about this one...)

#TODO Figure this out:

This is rapidally getting out of scope!

MIDI support is getting too big too fast.
This is outside of the scope of basic sequencing.

Support for ALSA will be added,
and basic MIDI handling and decoding will also be added.

However, at a later date, the MIDI wrappers will be removed and replaced with something else.
Most likely, I will be making a separate MIDI handling library that can optionally be installed
alongside pysynth to add MIDI support.

The external MIDI library will handle getting and decoding MIDI events,
and putting these events into a standardized format.
We will offer a decoder that will handle the process of changing the state of the sequencer.
The input type will be handled in the MIDI library.
We will offer wrappers for these operations.
"""

import ctypes

from pysynth.seq import BaseInput, BaseDecoder, Sequencer, Note, SeqCommand
from pysynth.wrappers.midi.events import *
from pysynth.wrappers.midi.alsa.base import ALSAInput


class MIDInput(BaseInput):

    """
    Base MIDI input module.

    We will probably offer a standardized method for converting MIDI events
    into something the decoder can understand.

    As of now we are empty, but this will change with time.
    """

    pass


class MIDIDecoder(BaseDecoder):

    """
    Base MIDI decoder module.
    """

    pass


class MIDILiveDecoder(MIDIDecoder):

    """
    Changes the state of sequencer live.

    We are best used in an environment the wants to play MIDI events live!
    """

    def __init__(self):

        super().__init__()

    def decode(self, event):

        """
        Decodes a given MIDI event.

        We only support note on and off events as of now.
        """

        if isinstance(event, NoteOn):

            # Turn the given synth on:

            note = Note.from_num(event.note - 69)

            # Toggle the note:

            self.seq.start_note(note)

            return

        if isinstance(event, NoteOff):

            # Turn the given synth off:

            note = Note.from_num(event.note - 69)

            # Toggle the note:

            self.seq.stop_note(note)


class MIDIWrapper(Sequencer):

    """
    MIDI Wrapper - Allows for the easy addition of MIDI modules.
    """

    def __init__(self, middle_freq=440.0):

        super().__init__(middle_freq=middle_freq)

    def alsa_live(self):

        """
        Load the ALSA input module and the live decoder module.
        """

        self.bind_decoder(MIDILiveDecoder())
        self.bind_input(ALSAInput())
