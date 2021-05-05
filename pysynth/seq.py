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
A decoder can simply call the functions of the sequencer to invoke the notes,
or it can generate a SeqCommand chain,
that the sequencer will accept and act upon.

The sequencer will generate a pair of input/decoder modules,
each running in their own thread,
based upon the number of tracks we have.

The best organization for different music standards(MIDI, MML)
is probably to keep these standards in their own sub-folders in this directory.
Perhaps each subdirectory will have a setup feature,
to auto-configure the sequencer for a particular use case?

If the user wishes to add a standard, then they can configure the sequencer manually.
"""


from dataclasses import dataclass
from math import pow, log
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pysynth.utils import BaseEvent, get_time

import time
import threading
import multiprocessing


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

        We use 'find_beats()' to determine the amount of beats the note type takes up.

        Once we have determined the number of beats this note takes up,
        we will then multiply the value by the beats per second,
        which we can calculate using the beats per minute.

        We then return the amount of time, in seconds, a note will take.

        :param note_type: Type of note to calculate rest time for
        :type note_type: float
        :return: Number of nanoseconds we must sleep for
        :rtype: float
        """

        # Find the number of beats this note type takes up:

        beats = self.find_beats(note_type)

        # Multiply this by the time per beat, convert to nanoseconds, and return:

        return (beats * (1 / (self.tempo / 60))) * 1000000000

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


class BaseCommand(object):

    """
    BaseCommand - Parent class all commands should inherit.

    Each command should do a certain operation,
    such as toggling a note, sleeping, changing tempo, ect.

    We also keep information on the time this event will start,
    and the time this event will end.
    This allows the SeqCommand to keep new events in time.
    """

    def __init__(self, name=None, legnth=0) -> None:
        
        self.time_start = 0  # Time this event will start, in nanoseconds
        self.time_stop = 0  # Time this event will stop, in nanoseconds
        self.length = legnth  #  Length of this event in nanoseconds
        self.name = name

    def _bind(self, com, seq):

        """
        Binds the sequencer command instance,
        and sequencer instances to this object.

        This is called upon adding the event.

        :param com: SeqCommand instance we are attached to
        :type com: SeqCommand
        :param seq: Sequencer instance we are controlling
        :type seq: Sequencer
        """

        # Bind our items:

        self.seq = seq
        self.seq_com = com

        if self.name is None:

            # Update the name with the default name:

            self.name = self.seq_com.name

    def _set_start(self, start):

        """
        Sets the starting time for this object.

        We also take this opportunity to calculate
        the absolute stop time using the legnth. 
        """

        # Start time of this event:

        self.time_start = start

        # Stop time of this event:

        self.time_stop = start + self.length

    def run(self):

        """
        Main run method, all your logic should reside here!

        This is the function that SeqCommand will invoke when running,
        and where this event should do it's operations.

        We accept no parameters, they should have been passed upon instantiation.
        """

        raise NotImplementedError("Must be overridden in child class!")


class NoteOn(BaseCommand):

    """
    We handle toggling notes on.

    We will keep the notes on indefinitely,
    unless we are provided with a length,
    which we will wait for the time and kill the note.

    If a name is not provided, 
    then we will use the default name attached to the SeqCommand. 

    :param start: Start time of the note
    :type start: int
    :param note: Note instance of the note to start
    :type note: Note
    :param length: Length of the note
    :type length: float
    :param name: Name of the instrument
    :type name: int, str
    """

    def __init__(self, note, length=0, name=None):

        super().__init__(name=name, legnth=length)

        self.note = note  # Note to turn on

    def run(self):

        """
        We toggle the given note to be on.

        If length is not given, then the note will not be stopped.
        """

        # Toggle the note:

        print("Starting note: {}".format(self.note))

        self.seq.start_note(self.note, name=self.name, time_start=self.time_start + self.seq_com.offset, 
        time_stop=self.time_stop + self.seq_com.offset)

        return


class NoteOff(BaseCommand):

    """
    We handle toggling notes off.

    We will turn the note off immediately if a length is not specified.
    If a length is specified, then we will wait the time before stopping the note.

    :param note: Note instance of the note to stop
    :type note: Note
    :param length: Time to wait before stopping the note
    :type length: float
    :param name: Name of the instrument to stop
    :type name: int, str
    """

    def __init__(self, note, length=0, name=None):

        super().__init__(name=name, legnth=length)

        self.note = note  # Note instance to stop

    def run(self):

        """
        We toggle the given note to off.
        """

        # Turn the note off:

        self.seq.stop_note(self.note, name=self.name, time_stop=self.time_stop)


class Chord(BaseCommand):

    """
    We represent a chord,
    multiple notes that are on at the same time
    for a time period.
    """

    def __init__(self, notes, length, name=None):

        super().__init__(name=name, legnth=length)

        self.notes = list(notes)  # Number of notes to toggle

    def run(self):

        """
        We toggle the notes in the chord on
        for the given length.
        """

        for note in self.notes:

            # Toggle the note to on:

            self.seq.start_note(note, name=self.name, time_start=self.time_start + self.seq_com.offset, 
            time_stop=self.time_stop + self.seq_com.offset)


class Rest(BaseCommand):

    """
    We act as a rest,
    stopping the execution of commands for a period of time.

    Great for putting pauses in the music.

    :param length: Time to sleep for
    :type length: float
    """

    def __init__(self, length):

        super().__init__(legnth=length)

    def run(self):

        """
        We do nothing, our presence is enough.
        """

        pass


class Repeat(BaseCommand):

    """
    We change our index back to a certain location,
    emulating repeats in a song.

    We can repeat a certain number of times,
    or indignantly.

    :param pos: Position to repeat back to
    :type pos: int
    :param num: Number of times to repeat, -1 for indefinitely
    :type num: int
    """

    def __init__(self, pos, num=-1):

        super().__init__()

        self.pos = pos  # Position to move back to
        self.num = num  # Number of times to repeat

    def run(self):

        print("Checking repeat...")

        # Check if we should stop repeating:

        if self.num == 0:

            # Stop repeating

            return

        # Otherwise, subtract from num:

        self.num -= 1

        # Move our index back to the given position:

        print("Setting index to : {}".format(self.pos))

        self.seq_com.index = self.pos

        # Set the offset time to now:

        self.seq_com.offset += self.time_stop

        print("New offset: {}".format(self.seq_com.offset))


class SeqCommand:

    """
    Sequencer Command - Easy to use sequencer event programming.

    We allow for the programming and scheduling of sequencer events.
    We are best used in a situation where we are reading musical events from somewhere,
    NOT in a live environment.

    Decoders can program us with events for the sequencer to execute.
    We are then passed along to the sequencer and the events are executed.
    This prevents decoding latency, and allows us to keep events and tracks synchronized.

    We offer convenience methods for common musical events, such as toggling notes,
    resting, looping, tempo changes, and chords.
    All of this functionality is provided via methods that add and configure the necessary events.
    These convenience methods also keep the timing accurate,
    so the decoder does not have to do any time calculations.
    If the decoder wants to add events based on time without the help of convenience methods,
    then they can certainly do so. 

    We also keep time statisticsand offer some time operations,
    so the Sequencer's job it a bit easier.

    ALL TIME OPERATIONS MUST BE IN NANO SECONDS!

    This is what the sequencer understands, and it is what the sequencers to use to determine timing.
    """

    def __init__(self, seq) -> None:
        
        self.seq = seq  # Sequencer instance
        self.events = []  # List of events
        self.offset = 0  # Timeoffset - great for going 'back in time'
        self.index = 0  # Event index we are currently on
        self.name = None  #  Name of the synth chain to invoke

    def note(self, num, length, index=-1, name=None):

        """
        We schedule a note event with the given note number,
        length, and index of the event to add.

        The 'num' parameter can be a integer, or a 'Note' object.
        If it is an integer, then it will be converted into a note.

        The 'length' is the length of the note.
        We will block and remove the note at the end of this time.

        Index is the index to insert the event at.
        Be default, the command is appended to the end of the event list,
        but you could place it elsewhere if necessary.

        :param num: Number of the note to play
        :type num: int, Note
        :param length: Length of the note to play
        :type length: float
        :param index: Index to insert the command at
        :type index: int
        :param name: Name of the synth to add
        :type name: int, str
        """

        # First, check to see if we are working with a note:

        if type(num) != Note:

            # Convert into a note:

            num = Note.from_num(num)

        # Create an event:

        self.add_event(NoteOn(num, length, name=name), index)

    def rest(self, length, index=-1):

        """
        Adds a rest event of given length.

        This adds a period of empty time to the SeqCommand,
        meaning that any notes scheduled after this event
        will not start during this period.

        The decoder can manually schedule notes during this time,
        and they will be invoked normally. 

        :param length: Time to rest for
        :type length: float
        :param index: Index to add the event at
        :type index: int
        """

        # Create and add the event:

        self.add_event(Rest(length), index)

    def repeat(self, pos, num, index=-1):

        """
        Repeats back to the given index a number of time.

        If the number of times is -1,
        then we will repeat indefinitely.

        :param pos: Index to repeat back to
        :type pos: int
        :param num: Number of times to repeat
        :type num: int
        :param index: Index to add the event at
        :type index: int
        """

        # Create and add the event:

        self.add_event(Repeat(pos, num), index)

    def chord(self, notes, length, index=-1, name=None):

        """
        Creates a chord with a given length.

        We do this by creating a Chord event.

        :param notes: Notes to be included in the chord
        :type notes: list
        :param length: Length of the chord
        :type length: float
        :param index: Index to add the event at
        :type index: int
        :param name: Name of the instrument to toggle
        :type name: str, int
        """

        # Check if we should convert the notes:

        for num, note in enumerate(notes):

            if type(note) != Note:

                # Lets convert the note:

                note = Note.from_num(note)

                notes[num] = note

        # Create and ass the Chord event:

        print("Creating chord with notes: {}".format(notes))

        self.add_event(Chord(notes, length, name=name), index)

    def add_event(self, event, index):

        """
        Adds an event at the given index.

        We use the accumulated time from the events before us to determine the start time.

        :param event: Event to add
        :type event: BaseEvent
        :param index: Index to add the event to
        :type index: int
        """

        # Bind info to the event:

        event._bind(self, self.seq)

        # Add the event:

        if index == -1:

            # Just append the item:

            self.events.append(event)

            # Set the index:

            index = len(self.events) - 1

        else:

            self.events.insert(index, event)

        # Set the start time:

        event._set_start(self._get_acctime(index))

    def _get_acctime(self, index):
        
        """
        Gets the accumulated time at the given index.

        The accumulated time is the total time elapsed in the events before us.
        We simply get the stop time for the event directly behind us in the event list.

        :param index: Index to get the accumulated time for
        :type index: int
        """

        # Check if we are working with index 0:

        if index == 0:

            # We are the start, meaning acc time will be zero:

            return 0

        # Get the stop time for the event ahead of us:

        return self.events[index-1].time_stop

    def run(self, time):

        """
        Runs the given commands, and starts manipulating the sequencer.

        We run ALL events that are less than the given time value,
        and that are more than our current index.
        We also add the offset to the start time,
        as it will be used to support features like repeating.

        Normally, we return True when we have done our work.
        When we are done iterating, then we will return False.

        :param time: Time value, all events less than this will be ran
        :type time: int
        :retrun: True when successful, False when done
        """

        # Find all events that fall within our parameters:

        events = 0

        for event in self.events[self.index:]:

            if event.time_start + self.offset < time:

                # Found a valid event, lets run it:

                event.run()
                events += 1
            
                continue

            # Nothing, lets update our index and continue:

            self.index += events

            print("New index: {}".format(self.index))

            return True

        # We really are done, let's return False

        return False


class SeqCommandOld:

    """
    Sequencer Command - easy to use sequencer event programming.

    We allow for the programming and scheduling of sequencer events,
    optimized specifically for speed.

    Decoders can program us with events for the sequencer to execute.
    We are then passed along to the sequencer and the events are executed in an efficient way.
    This prevents decoding latency, and can keep different tracks synchronized.

    We support very common commands, such as turning notes on/off,
    resting, looping, tempo changes, and chords.
    All of this functionality is provided via methods,
    and the internal storage of commands is highly optimized.

    Our events are classes that change the state of the sequencer,
    or this class.
    We offer methods for creating common events,
    such as notes on/off.
    If you wanted custom functionality that we do not offer by default,
    you could create an event and register it normally.
    """

    def __init__(self, seq, tempo=120, notes_per_measure=4):

        self.seq = seq  # Sequencer instance to work with
        self.events = []  # List of sequencer events
        self.tempo = tempo  # Tempo in beats per minute
        self.notes_per_measure = notes_per_measure  # number of notes per measure

        self.index = 0  # Index we are at in the command list

    def note(self, num, length, index=-1, name=None):

        """
        We schedule a note event with the given note number,
        length, and index of the event to add.

        The 'num' parameter can be a integer, or a 'Note' object.
        If it is an integer, then it will be converted into a note.

        The 'length' is the length of the note.
        We will block and remove the note at the end of this time.

        Index is the index to insert the event at.
        Be default, the command is appended to the end of the event list,
        but you could place it elsewhere if necessary.

        :param num: Number of the note to play
        :type num: int, Note
        :param length: Length of the note to play
        :type length: float
        :param index: Index to insert the command at
        :type index: int
        :param name: Name of the synth to add
        :type name: int, str
        """

        # First, check to see if we are working with a note:

        if type(num) != Note:

            # Convert into a note:

            num = Note.from_num(num)

        # Create an event:

        self.add_event(NoteOn(num, length, name=name), index)

    def rest(self, length, index=-1):

        """
        Adds a rest event of given length.

        This effectively stops this sequencer command,
        and rests for a period of time.

        :param length: Time to rest for
        :type length: float
        :param index: Index to add the event at
        :type index: int
        """

        # Create and add the event:

        self.add_event(Rest(length), index)

    def repeat(self, pos, num, index=-1):

        """
        Repeats back to the given index a number of time.

        If the number of times is -1,
        then we will repeat indefinitely.

        :param pos: Index to repeat back to
        :type pos: int
        :param num: Number of times to repeat
        :type num: int
        :param index: Index to add the event at
        :type index: int
        """

        # Create and add the event:

        self.add_event(Repeat(pos, num), index)

    def chord(self, notes, length, index=-1, name=None):

        """
        Creates a chord with a given length.

        We do this by creating a Chord event.

        :param notes: Notes to be included in the chord
        :type notes: list
        :param length: Length of the chord
        :type length: float
        :param index: Index to add the event at
        :type index: int
        :param name: Name of the instrument to toggle
        :type name: str, int
        """

        # Check if we should convert the notes:

        for num, note in enumerate(notes):

            if type(note) != Note:

                # Lets convert the note:

                note = Note.from_num(note)

                notes[num] = note

        # Create and ass the Chord event:

        print("Creating chord with notes: {}".format(notes))

        self.add_event(Chord(notes, length, name=name), index)

    def add_event(self, event, index):

        """
        Adds an event at the given index.

        We also append this object,
        s well as the sequencer instance.

        :param event: Event to add
        :type event: BaseCommand
        :param index: Index to add the event to
        :type index: int
        """

        # Bind info to the event:

        event._bind(self, self.seq)

        # Add the event:

        if index == -1:

            # Just append the item:

            self.events.append(event)

            return

        self.events.insert(index, event)

    def run(self, cond=True):

        """
        Runs the sequencer commands,
        and start manipulating the sequencer.

        This is a blocking function,
        and we will block until we reach then end.

        This should be called when the events are setup and configured.

        You can also pass a conditional to determine when we stop.
        Once this value becomes False, then we will stop our command loop.

        :param cond: Conditional to check after each event
        """

        while self.index < len(self.events) and cond:

            # Get the event at this potion and run it:

            self.events[self.index].run()

            # Increment our index:

            self.index += 1


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
        self._coms = []  # List of sequencer commands to run
        self._input = BaseInput()  # Input Module - Gets our info from somewhere
        self._decoder = BaseDecoder()  # Decoder module - Decodes our info
        self._on = {}  # Dictionary of synths and their notes that are on

        self.thread = None  # Threading control instance for modules
        self.default_name = 'default'  # Name to be used if no name is specified
        self.middle = middle_freq  # Middle frequency to use when decoding note numbers

        self.lookahead = 75 * 1000000  # Lookahead in nanoseconds
        self.interval = 50 / 1000  # Wait interval in seconds

        self.running = True  # Value determining if we are running

    def lookahead_ms(self, look):

        """
        Sets the lookahead using the given value in microseconds.

        We automatically convert the microseconds into nanoseconds,
        as this sequencer works with nanoseconds.
        """

        self.lookahead = look * 1000000

    def interval_ms(self, wait):

        """
        Sets the waiting interval using the given value in microseconds.

        We automatically convert the microseconds into seconds,
        as this is what time.sleep() understands.
        """

        self.interval = wait / 1000

    def start(self):

        """
        Starts the sequencer, control thread, and bound modules.
        """

        # Start each component:

        self._input.running = True
        self._input.start()

        self._decoder.running = True
        self._decoder.start()

        # Start the control thread;

        self.thread = threading.Thread(target=self._input.run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):

        """
        Stops the sequencer, control thread, and bound modules.
        """

        self.running = False

        # Stop the modules:

        self._input.running = False
        self._decoder.running = False

        self._input.stop()
        self._decoder.stop()

        # Stop the running synths:

        self.stop_all()

    def join(self):

        """
        Joins all the track threads,
        and blocks until each of them are done.
        """

        self.thread.join()

    def bind_input(self, inp):

        """
        Binds a given input module to this sequencer.

        We do a brief check to make sure that they inherit BaseInput.

        :param inp: Input module to add
        :type inp: BaseInput
        """

        # Check if given input module is valid:

        assert isinstance(inp, BaseInput), "Given input module MUST inherit BaseInput!"

        # Valid class! Lets bind this module to us:

        self._input = inp

        # Bind everything:

        self._bind_comps()

    def add_seqcom(self, com):

        """
        Adds the given SeqCommand instance to this sequencer.

        If we are ever invoked, 
        then we will run each SeqCommand in our collection.

        We do a quick check to make sure the thing we are adding is a SeqCommand.

        :param com: SeqCommand instance to add
        :type com: SeqCommand
        """

        # Check to make sure it is a SeqCommand

        assert isinstance(com, SeqCommand), "Given command chain MUST inherit SeqCommand!"

        # Valid class, lets add it:

        self._coms.append(com)

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

        # Bind everything:

        self._bind_comps()

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

        Synths are organized by names, which can really be anything.
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

    def start_note(self, note, name=None, time_stop=0, time_start=0):

        """
        Starts a synth at the specified note and name.

        This will start and invoke the synth at the specified note.
        If necessary, we will also configure the synth to operate at
        the specified frequency.

        If a name is not provided, then we will simply search for relevant
        synths in the first name that we have registered.

        We also allow for specifying the time_start and time_stop
        parameters, which determine when a note will start and stop.
        If neither of these are specified, then the note will start immediately,
        and will play indefinitely until stopped.

        :param note: Note to turn on
        :type note: Note
        :param name: Name of the synth to turn on
        """

        # Lets find our synth:

        synth = self._find_synth(note, name=name)

        # Add the synth note to the output:

        self._on[self._resolve_name(name)].append(note.revert())

        if time_stop > 0 and time_start > 0:

            # Schedule a time event:

            synth.time_event(time_start, time_stop)

        synth.start()

    def stop_note(self, note, name=None):

        """
        Stops a synth at the specified note and name.

        This will stop the synth at the specified note.

        If a name is not provided, then we will simply
        use the first registered name.

        :param note: Note to stop
        :type note: Note
        :param name: Name of the synth to stop
        :param time_stop: Time to stop the synth
        :type time_stop: int
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

                try:

                    self.stop_note(Note.from_num(synth_num))

                except:

                    # Don't care about errors, continue

                    continue

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

    def run_commands(self):

        """
        Runs the given SeqCommand instances.

        This is where the magic happens with SeqCommands.
        We handle and invoke each track at the same time, 
        to ensure that they remain synchronized.

        We use a lookahead method for scheduling synth components.
        We lookahead a given amount of time, schedule the events
        that occur within that time, and then sleep until the next cycle.

        This is a blocking method,
        meaning that we will block until we reach the end of the SeqCommand,
        or this sequencer is stopped. 
        """

        start = get_time()

        for com in self._coms:

            # Set the offset for each SeqCommand

            com.offset = start
        
        while self.running and self._coms:

            # Get our time value:

            time_now = get_time() + self.lookahead

            # Iterate over the commands:

            for com in self._coms:

                # Have the command invoke the synths that are ready:

                if com.run(time_now):

                    # Did our work, lets continue:

                    continue

                # SeqCommand is done, lets remove it

                self._coms.remove(com)

            # Wait until next cycle:

            time.sleep(self.interval)

        # Check if we should block:

        if self.running:

            # We are done, block until the notes are done playing:

            for name in self._on:

                for note in self._on[name]:

                    # Find the synth for the on note and block:

                    self._find_synth(Note.from_num(note), name=name).join()      

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

    def _bind_comps(self):

        """
        Binds all components together.

        This is called multiple times to ensure that all components are aware of eachother.
        """

        # Binds the modules to each other:

        self._input.decoder = self._decoder
        self._decoder.input = self._input

        # Bind ourself to the components:

        self._input.seq = self
        self._decoder.seq = self
