
"""
Base file for ALSA MIDI events.

We specify a ALSAInput module that can read MIDI information from ALSA.

Because we are using ctypes to interfact with ALSA,
we also implement some buffer structures to allow for communication.
"""

import ctypes

from pysynth.seq import BaseInput
from pysynth.wrappers.midi.events import *

# Map the number types to 

type_map = {6: NoteOn,
            7: NoteOff}

class ALSAEvent(ctypes.Structure):

    """
    Main ALSA Event structure.

    We are here to facilitate communication between C ALSA events and python.
    """

    _fields_ = [('type', ctypes.c_ubyte),  # Type of MIDI event
                #('raw_bytes', ctypes.c_ubyte),  # Raw bytes of the MIDI event
                #('flags', ctypes.c_ubyte),  # Flags of the MIDI event
                ('tick_time', ctypes.c_uint),  # Tick time of this MIDI event
                ('time_sec', ctypes.c_uint),  # Real time of this MIDI event in seconds
                ('time_nano', ctypes.c_uint),  # Real time of this MIDI event in nanoseconds
                ('note', ctypes.c_ubyte),  # Note value, only for note messages
                ('velocity', ctypes.c_ubyte),  # Note on velocity, only for note on messages
                ('off_velocity', ctypes.c_ubyte),  # Note off velocity, only for note off messages
                ('duration', ctypes.c_uint),  # Note duration, only for note on messages
                ('param', ctypes.c_uint),  # Controller number, only for controller messages
                ('value', ctypes.c_int),  # Controller value, only for controller messages
                ('channel', ctypes.c_ubyte)] # Channel number of the MIDI event 


class ALSAInput(BaseInput):

    """
    ALSAInput - Gets MIDI events from ALSA.

    We use external C++ code to pull events from ALSA.
    We only pull the values, convert them, and pass them onto the decoder.
    """

    def __init__(self):

        super().__init__()

        self.midi_alsa = ctypes.CDLL('pysynth/wrappers/midi/alsa/midi_alsa.so')  # Instance of the ALSA MIDI C wrapper
    
    def start(self):

        """
        Starts the connection to ALSA.

        We allow the C wrappers to take over this operation.
        """

        self.midi_alsa.midi_open()

        self.midi_alsa.midi_read.restype = ctypes.c_void_p

    def run(self):

        """
        Continuosly pull MIDI events from ALSA and handle them.

        In this case, we just print them.
        """

        while True:

            # Get a value from ALSA:

            val = self.midi_alsa.midi_read()

            # Convert it into a MIDI event:

            event = ALSAEvent.from_address(val)

            if event.type not in type_map.keys():

                # Junk event, let's continue

                continue

            # Lets decode it using our type_map:

            pack = type_map[event.type].from_object(event)

            # Send it along to the decoder:

            self.decoder.decode(pack)
