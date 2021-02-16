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


from dataclasses import dataclass
from math import pow, log
from copy import deepcopy


class BaseInput(object):

    """
    BaseInput class that all child input classes should inherit!

    We define some useful functionality here,
    and offer some good use-cases.

    Ideally, we will make communication with the decoder very simple.
    """

    def __init__(self):

        self.seq = None  # instance of the sequencer
        self.decoder = None  # instance of the decoder
        self.running = False  # Value determining if we are running

    def start(self):

        """
        Function called when the input module is started.

        The input module is started when the Sequencer is started,
        and before the control thread is started.

        You can put any setup code here to prepare your input module.
        """

        pass

    def stop(self):

        """
        Function called when this input module is stopped.

        The input module is stopped when the Sequencer is stopped,
        and before the control thread is stopped.

        You can put any shutdown code in here to stop your input module.
        """

        pass

    def run(self):

        """
        Main run method of the input module.

        Ideally, we will continuously get our input from somewhere,
        and then pass it onto the decode() method of the decoder,
        which will then pass instructions onto the sequencer.
        """

        raise NotImplementedError("Must be implemented in child class!")


class BaseDecoder(object):

    """
    BaseDecoder class that all child decoders should inherit!

    We define some useful functionality here,
    and offer some good use-cases.

    Probably won't be much more than getting items from a queue,
    and then calling the sequencer.

    As of now, we are synchronous,
    meaning that we operate in one control thread.
    The input module calls us, we interpret, we call the sequencer.
    This may change with time, so watch out!

    We purposely keep this class ambiguous,
    as decoding could have many different styles and configurations.
    """

    def __init__(self):

        self.seq = None  # Instance of the sequencer
        self.input = None  # Instance of the input module
        self.running = False  # Value determining if we are running

        self.tempo = 0  # Tempo in beats per minute
        self.beats_per_measure = 4  # Used to determine the amount of beats per measure

    def start(self):

        """
        Function called when this decoder is started.

        The decoder is started when the Sequencer is started,
        and before the control thread is started.

        You can put any setup code here to prepare your decoder.
        """

        pass

    def stop(self):

        """
        Function called when this decoder is stopped.

        The decoder is stopped when the Sequencer is stopped,
        and before the control thread is stopped.

        You can put any shutdown code in here to stop your decoder.
        """

        pass

    def find_time_type(self, note_type):

        """
        Finds the amount of time the note will take given it's note type,
        beats per measure, and tempo.

        We use 'find_beats()' to determine the amount of beats the note ype takes up.

        Once we have determined the number of beats this note takes up,
        we will then multiply the value by the beats per second,
        which we can calculate using the beats per minute.

        We then return the amount of time, in seconds, a note will take.

        :param note_type: Type of note to calculate rest time for
        :type note_type: float
        :return: Number of seconds we must sleep for
        :rtype: float
        """

        # Find the number of beats this note type takes up:

        beats = self.find_beats(note_type)

        # Multiply this by the time per beat and return:

        return beats * (1 / (self.tempo / 60))

    def find_beats(self, note_type):

        """
        Finds the amounts of beats the given note represents, given the beats per bar,
        and tempo.

        The note_type represents the fraction of the note compared to he bpb.
        If the bpm is 4, then 1 represents 1 beat, 2 represents 2 beats, 3 represents 4/3 beats, ect.
        In normal note notation, a 1 is a whole note, 2 is half note, 4 is quarter note, 8 is eight note, ect.

        We also support fractions of notes,
        meaning that if you provide 2.5, then we will interpret this note as a dotted half note.
        After we determine the number of beats the note represents,
        we multiply the number of beats by this decimal, and add it to the total.
        So if we have 4 BPB, the tempo is 60 BPM, and we provide 4.5,
        then we will rest for 1.5 seconds.

        :param note_type: Type of not to calculate number of beats for
        :type note_type: float
        :return: Number of beats this note represents
        :rtype: float
        """

        # First, find the number of beats this value takes up:

        beats = self.beats_per_measure / int(note_type)

        # Next, add the amount of fraction beats to this value:

        beats = beats + (beats * (note_type % 1))

        # Return

        return beats

    def decode(self, *args, **kwargs):

        """
        The main decoder method!

        All inputs from the Input module will be sent here for decoding.

        As of now, we utilise a synchronous model for sequencer decoding,
        meaning that only one thread is used, and queues are not used.

        This means that all input will be sent here, in whatever format is agreed upon
        between modules.
        """

        raise NotImplementedError("Must be implemented in child class!")


@dataclass
class Note:

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

    __slots__ = ("octave", "step")

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

        return int(num / 12), num % (12 if num > 0 else -12)

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

    @classmethod
    def from_num(cls, num):

        """
        Creates a Note object from a number of steps away from A.

        Under the hood, we convert the number into pysynth notation,
        and then create an instance with those values

        :param num: Number to use when creating
        :type num: int
        :return: Note object representing the inputted number
        :rtype: Note
        """

        # Get converted values:

        octave, step = cls.convert(num)

        # Return:

        return cls(octave, step)

    def __eq__(self, other):

        """
        Ensures equality between two note objects.

        We check to make sure the values of the
        given Note is equal to ours.

        :param other: Note object to compare
        :type other: Note
        :return: True for equal to, False for not equal to
        :rtype: bool
        """

        # Check to make sure we are working with Notes:

        assert isinstance(other, Note), Exception("Can only compare Notes to Notes!")

        # Check if we are true:

        return self.octave == other.octave and self.step == other.step


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

        self.thread = None  # Control thread instance
        self.default_name = 'default'  # Name to be used if no name is specified
        self.middle = middle_freq  # Middle frequency to use when decoding note numbers

    def start(self):

        """
        Starts the sequencer, control thread, and bound modules.
        """

        # Starts the decoder module first:

        self._decoder.running = True
        self._decoder.start()

        # Start the input module:

        self._input.running = True
        self._input.start()

        # Start the run method in the input:

        self._input.run()

    def stop(self):

        """
        Stops the sequencer, control thread, and bound modules.
        """

        # Stop the input module:

        self._input.running = False
        self._input.stop()

        # Stop the decoder module:

        self._decoder.running = False
        self._decoder.stop()

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

        # Lets give them relevant information:

        inp.seq = self
        inp.decoder = self._decoder

        # Lets give our decoder relevant information:

        if self._decoder is not None:

            # Add ourselves to the decoder:

            self._decoder.input = inp

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

        # Lets add some relevant information:

        dec.seq = self
        dec.input = self._input

        # Add ourselves to the input module:

        if self._input is not None:

            # Add ourselves to the input module:

            self._input.decoder = dec

    def add_synth(self, synth, name=None, notes=None):

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

        :param synth: Synth instance to add
        :type: iter
        :param name: name of the synth to add
        :type name: str, int
        :param notes: Musical notes to register the synth under
        :type notes: None, list
        """

        if name is None:

            # Lets set the default name:

            name = self.default_name

        # Determine if the name is in our collection:

        if name not in self._synths:

            # Add the name to the collection:

            self._synths[name] = {}
            self._on[name] = []

        if notes is not None:

            # We must register the synths under specified notes

            for note in notes:

                # Add the synth as the note:

                temp_synth = deepcopy(synth)

                # Set the oscillating frequency:

                temp_synth.freq = note.freq_conv(middle_pitch=self.middle)

                self._synths[name][note.revert()] = temp_synth

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

        # Lets find our synth:

        synth = self._find_synth(note, name=name)

        # Add the synth note to the output:

        self._on[self._resolve_name(name)].append(note.revert())

        # Start the synth:

        synth.start()

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

        # Resolve the values:

        name = self._resolve_name(name)

        synth = self._find_synth(note, name)

        note_value = note.revert()

        if note_value not in self._on[name]:

            # Note is not currently on!

            raise Exception("Note is not currently on!")

        # Stop the synth:

        synth.stop()

        # Remove it from output:

        self._on[name].remove(note_value)

    def stop_all(self):

        """
        Stops all synths that are currently started.
        """

        # Iterate over the outputting synths:

        for name in self._on:

            for synth_num in self._on[name]:

                # Stop the synth:

                self.stop_note(Note.from_num(synth_num))

    def get_state(self, note, name=None):

        """
        Gets the state of a note with the specified name.

        We return True if the note is on,
        and False if the note is off.

        :param note: Note to get the state of
        :type note: Note
        :param name: Name of the synth to check
        :return: True for on, False for off
        :rtype: bool
        """

        # Resolve the name:

        name = self._resolve_name(name)

        # Check if not value is present in output

        return note.revert() in self._on[name]

    def _resolve_name(self, name):

        """
        Takes the given name and resolves it.

        If the name exists and is valid,
        then we simply return it.

        If the name is None,
        then we return the first name registered.

        If the name is invalid and does not exist,
        then we raise an exception.

        :param name: Name to be found
        :type name: str
        :return: Resolved name
        :rtype: str
        """

        # Determine if the synth is None:

        if name is None:

            # Simply return the first name:

            return list(self._synths.keys())[0]

        # Determine if name does not exist:

        if name not in self._synths.keys():

            # Raise an exception!

            raise Exception("Name not valid!")

        # Otherwise, return the name as usual:

        return name

    def _find_synth(self, note, name=None):

        """
        Finds a synth by the given note and name.

        If a name is not specified, then we simply use the first registered name.

        If no note is found in the name,
        then a new one is created from the default synth via 'deepcopy'.

        :param note: Noe of the synth to start
        :type note: Note
        :param name: Name of the synth collection to start
        :type name: str
        :return: Synth at that position
        :rtype: BaseModule
        """

        # Resolve the name:

        name = self._resolve_name(name)

        # Get the synth at the given note

        note_val = note.revert()
        synth = None

        if note_val in self._synths[name].keys():

            # Found our synth, let's grab it!

            synth = self._synths[name][note_val]

        else:

            # Not present, let's make a copy of the default synth:

            if 'd' not in self._synths[name].keys():

                # Default synth not present!

                raise Exception("Default Synth not present!")

            # Lets make a deep copy of the default:

            synth = deepcopy(self._synths[name]['d'])

            # Lets set the oscillating frequency:

            synth.freq = note.freq_conv(middle_pitch=self.middle)

            # Lets register it to the given note:

            self._synths[name][note_val] = synth

        # Synth has been found or registered!

        return synth
