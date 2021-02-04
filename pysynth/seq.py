"""
#TODO: Work on this description!
PySynth Sequencer

This file contains the framework for the PySynth sequencer API.

Essentially, a sequencer has three parts:

    input - Gets data from somewhere: midi stream, midi file, stdin, ect.
    decoder - Decodes the input into something we can understand: note on, note off
    sequencer - Sequencer that handles these objects, and acts upon the information inputted

The sequencer is the engine of the process, interpreting and doing things based upon the input data.

The input system simply grabs information form somewhere and sends it to the decoder.
Their might be multiple input modules, and their implementations might differ per platform.

The decoder will take the inputted information and put into a format that we can understand.
(This is probably going to call methods on the sequencer to change the synth values).

Each sequencer will have to be in it's own thread,
as the input module may block for information,
and we don't want to affect our sound.

The best organisation for different music standards(MIDI, MML)
is probably to keep these standards in their own sub-folders in this directory.
Perhaps each subdirectory will have a setup feature,
to auto-configure the sequencer for a particular use case?

If the user wishes to add a standard, then they can configure the sequencer manually.
"""

from typing import NamedTuple
from math import pow, log
from copy import deepcopy


class BaseInput(object):

    """
    BaseInput class that all child input classes should inherit!

    We define some useful functionality here,
    and offer some good use-cases.

    Ideally, we will make communication with the decoder very simple.
    """

    pass


class BaseDecoder(object):

    """
    BaseDecoder class that all child decoders should inherit!

    We define some useful functionality here,
    and offer some good use-cases.

    Probably won't be much more than getting items from a queue,
    and then calling the sequencer.
    """

    pass


class Note(NamedTuple('Note')):

    """
    We represent a Musical Note.

    We use two parameters, 'octave' and 'step'.

    'octave' is the number of octaves we are away from the forth octave,
    or the octave containing the middle pitch, usually A4, or 440.0 hertz.
    If this note is lower, we go down an octave.
    Higher, we go up an octave.

    'step' is the number of half steps we are away from the middle pitch.
    For example, if we wanted a note 4 half steps above the the middle pitch,
    (Again, usually A4 or 440.0 hertz),
    then we would input 4.
    Going down is similar, except we just use negative numbers.

    We offer the option to convert the numbers into frequencies and vice versa.
    If we get one unusually large number,
    then we will split it up into this notation.

    Examples:

        0, 0 - A4
        0, 1 - A4#/B4b
        0, 2 - B4
        0, -2 - G4
    """

    octave: int
    step: int

    def freq_conv(self, middle_pitch=440.0):

        """
        Converts our notes values into frequencies.

        We utilise the following algorithm:

        f = mp * 2 ^ ((o * 12 + s) / 12)

        Where:

        f = Frequency of the given number
        mp = Middle Pitch - Usually A4 or 440.0
        o = The octave we are on
        s = Steps away from the middle pitch

        The user can select their own middle pitch,
        although it is highly recommended to keep it the way it is!

        :param middle_pitch: Middle pitch in hertz to start at
        :type middle_pitch: float
        :return: The frequency of the note in hertz
        :rtype: float
        """

        # Calculate and return the frequency of the note:

        return middle_pitch * pow(2, (((self.octave * 12) + self.step) / 12))

    @staticmethod
    def convert(num):

        """
        Converts a single number into the PySynth notation.

        We use the following equation:

        octave = int(num / 12)
        step = num % 12

        Where:

        octave = Octave of the note
        step = Steps away from middle pitch
        num = Input number

        :param num: Number to convert
        :type num: int
        :return: Converted numbers in a tuple
        :rtype: tuple
        """

        # Convert the number and return it:

        return int(num / 12), 12 % num

    def revert(self):

        """
        Reverts our numbers back into one.

        We use the following formula:

        num = (12 * octave) + step

        Where:

        num = Final number
        octave = Octave value we are on
        step = Steps from the middle pitch

        :return: One number representing the total steps away from the middle pitch
        :rtype: int
        """

        # Convert our numbers and return it:

        return (12 * self.octave) + self.step

    @classmethod
    def from_freq(cls, freq, middle_pitch=440.0):

        """
        Creates a 'Note' from a given frequency.

        We convert the given frequency 'Note' values
        by determining the number of half steps from the given frequency and the middle pitch,
        and then splitting that value up into separate values.

        :param freq: Frequency in hertz
        :type freq: float
        :param middle_pitch: Middle pitch - Usually A4 or 440.0 hertz
        :type middle_pitch: float
        :return: Note object
        :rtype: Note
        """

        # Convert into number of steps:

        steps = int(log(freq/middle_pitch, 2))

        # Convert into two values and return:

        octv, step = cls.convert(steps)

        return cls(octv, step)


class Sequencer(object):

    """
    PySynth sequencer - Doing all the dirty work!

    We do all the work of invoking each synth component,
    altering their operation, and eventually stopping them.

    We allow for the registration of synths on a per-note basis,
    as well as synths with different names.
    This is useful if the info we are receiving has information for different types of synths,
    like if we are working with multiple instruments.

    We have our own method of representing notes. We use a 'Note' object to represent this.
    Each 'note' object has an octave and a number of steps from the halftone,
    which is by default 440.0 hertz.
    We will do the process of converting these 'note' objects into a frequency a synth can use.
    Synths can register themselves using either notes or frequencies,
    and notes can be invoked using either notes or frequencies.

    Ideally, this class will act as a parent for a wrapper.
    A wrapper will configure the sequencer for whatever operation is being attempted.
    This can include the following:

        - Register instrument names
        - Pre-configure a range of supported notes
        - Add relevant input/decoder handlers
        - Optimise the storage of the sequencer

    A wrapper will take away many complications with configuration,
    allowing the developer to quickly start using sequencers.

    :param middle_freq: Middle frequency to use when calculating output frequency
    :type middle_freq: float
    """

    def __init__(self, middle_freq=440.0):

        self._synths = {}  # Mapping synths to notes
        self._input = None  # Input Module - Gets our info from somewhere
        self._decoder = None  # Decoder module - Decodes our info
        self._on = {}  # Dictionary of synths and their notes that are on

        self.middle = middle_freq  # Middle frequency to use when decoding note numbers

    def bind_input(self, inp):

        """
        Binds a given input module to this sequencer.

        We do a brief check to make sure that they inherit BaseInput.

        :param inp: Input module to add
        :type inp: BaseInput
        """

        # Check if given input module is valid:

        assert isinstance(inp, BaseInput), "Given input module MUST inherit BaseInput!"

        # Valid class! Lets bind this module to us

        self._input = inp

    def bind_decoder(self, dec):

        """
        Binds a given decoder to this sequencer.

        We do a brief check to make sure that they inherit BaseDecoder

        :param dec:  Decoder module to add
        :type dec: BaseDecoder
        """

        # Check if given input module is valid:

        assert isinstance(dec, BaseDecoder), "Given decoder module MUST inherit BaseDecoder!"

        # Valid class! Lets bind this module to us:

        self._decoder = dec

    def add_synth(self, name, synth, notes=None):

        """
        Adds the given synth(Or synth collection) to the sequencer.

        You can specify the notes to add, which should be in a list in 'notes'.
        If no notes are specified, then this synth will be made the default synth for this name.
        If the sequencer attempts to start a note that is not configured,
        then a copy of the default synth will be made, started, and registered to that note.

        For speed reasons, it is recommended to either register all notes individually,
        or run 'pre-load' after specifying a certain note range.
        If you don't do these operations, then the first time a note is played, a copy will have to be made
        of the default synth, which can cause latency and slowdowns.

        If notes are specified, then the synth will be registered to each name with those notes.

        Synths are organised by names, which can really be anything.
        Each name has a sub-section where it is registered to notes.
        You can treat these names as different kinds of instruments.
        Any wrappers(Such as MIDI or MML) will auto-configure these names for you.

        :param name: name of the synth to add
        :type name: str
        :param synth: Synth instance to add
        :type: iter
        :param notes: Musical notes to register the synth under
        :type notes: None, list
        """

        # Determine if the name is in our collection:

        if name not in self._synths:

            # Add the name to the collection:

            self._synths[name] = {}

        if notes is not None:

            # We must register the synths under specified notes

            for note in notes:

                # Add the synth as the note:

                self._synths[name][note] = deepcopy(synth)

        else:

            # just make the synth the default for that name:

            self._synths[name]['d'] = synth

    def start_note(self, note, name=None):

        """
        Starts a synth at the specified note and name.

        This will start and invoke the synth at the specified note.
        If necessary, we will also configure the synth to operate at
        the specified frequency.

        If a name is not provided, then we will simply search for relevant
        synths in the first name that we have registered.

        :param note: Note to turn on
        :type note: Note
        :param name: Name of the synth to turn on
        """

        pass

    def stop_note(self, note, name=None):

        """
        Stops a synth at the specified note and name.

        This will stop the synth at the specified note.

        If a name is not provided, then we will simply
        use the first registered name.

        :param note: Note to stop
        :type note: Note
        :param name: Name os the synth to stop
        """

        pass

    def get_state(self, note, name=None):

        """
        Gets the state of a note with the specified name.

        We return True if the note is on,
        and False if the note if off.

        :param note: Note to get the state of
        :type note: Note
        :param name: Name of the synth to check
        :return: True for on, False for off
        :rtype: bool
        """

        pass
