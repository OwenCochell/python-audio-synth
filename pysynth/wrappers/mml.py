"""
Sequencer wrapper for Music Marco Language.

This standard is very open ended, so we take some liberties to describe it.
"""

from pysynth.seq import BaseInput, BaseDecoder, Sequencer, Note, SeqCommand

import time


class MMLSeeker:

    """
    A string seeker optimized for MML.

    We allow for easy parsing and traversing of strings containing MML data,
    and have some uses that are specific to MML.
    """

    def __init__(self, source):

        self.source = source  # Original string - content we are iterating over
        self.index = 0  # Index of the string we are in

    def reset(self):

        """
        Resets our index to zero,
        effectively restarting the seek.
        """

        # Set our index to zero:

        self.index = 0

    def set(self, index):

        """
        Sets the seeker to the given index.

        :param index: Index to set the seeker to
        :type index: int
        """

        # Check if our index is valid:

        if index < len(self.source):

            # Valid index, lets set it:

            self.index = index

    def get(self):

        """
        Gets the character at out current index.

        :return: Character at position
        :rtype: str
        """

        return self.source[self.index]

    def peek(self):

        """
        Peaks ahead at the next character,
        without incrementing our index.

        :return: Character at next position
        :rtype: str
        """

        # Check if we have another character:

        if not self.has_next():

            # Return nothing:

            return ' '

        # Return character at the next position:

        return self.source[self.index + 1]

    def forward(self):

        """
        Increments the index by one.

        We also make sure that our current value is valid,
        not a space.
        """

        # Iterate until we find something:

        while self.has_next():

            # Move forward:

            self.index += 1

            # Check the value residing here:

            if self.get() != ' ':

                # We have a value! return

                return

        raise Exception("Unable to move forward, index out of bounds!")

    def read_until(self, match):

        """
        Read until we match with a certain character.

        We act as a generator, continuously yielding until
        we reach our target.

        :param match: String to match with
        :type match: str
        :return: Character at our position
        :rtype: str
        """

        # Iterate until we find our position:

        while self.has_next():

            # Go to our next value:

            self.forward()

            # Get the current position:

            temp = self.get()

            # Check if it is our match:

            if temp == match:

                # It is! Return and exit!

                return

            # No dice, lets yield:

            yield temp

    def has_next(self):

        """
        Checks to see if another character is available.

        We do this by comparing our index to the length of the source string.

        :return: True for success, False for failure
        :rtype: bool
        """

        # Compare our index:

        if self.index < len(self.source) - 1:

            # Less than, let's return True

            return True

        # No good, return False

        return False


class BaseMMLInput(BaseInput):

    """
    Base class for MML Inputs.

    We essentially provide methods for loading string data,
    and moving it forward as we need to.
    """

    def __init__(self):

        super(BaseMMLInput, self).__init__()

        self.source = None  # Source of all string data

    def load_string(self, data):

        """
        Loads string data into the MMLSeeker.

        :param data: String data to seek
        :type data: str
        """

        # Create a new seeker and load string data

        self.source = MMLSeeker(data)

        # Add the seeker to the decoder:

        self.decoder.source = self.source

    def run(self):

        """
        Continuously move the seeker forward and call the decoder.
        """

        for event in self.decoder.command.events:

            print(event)

        # Run the SeqCommand instance:

        self.seq.run_commands()

        print("Done running")


class StringMMLInput(BaseMMLInput):

    """
    We iterate over a given string.
    """

    def __init__(self):

        super(StringMMLInput, self).__init__()


class MMLDecoder(BaseDecoder):

    """
    We handle all MML inputs from inputs.

    We also handle some features of tracks?
    Maybe thread based? Asyncio?
    Perhaps the input module should invoke this?
    """

    def __init__(self):

        super(MMLDecoder, self).__init__()

        self._reset_values()

        self.command = None  # Sequencer command instance

        self.notes = []  # List of notes in an ongoing chord
        self.source = None  # Source of all MML input, usually provided by the input module
        self.note_map = {'c': -9, 'd': -7, 'e': -5, 'f': -4, 'g': -2, 'a': 0, 'b': 2}  # Mapping notes to note values

    def _reset_values(self):

        """
        Resets(Or sets) this decodes values back to normal.

        This is called upon each new track,
        as each track will have their own configurations.
        """

        self.octave = 0  # Current octave we are set at
        self.tempo = 120  # Tempo in beats per minute
        self.default_length = 4  # Default length to apply when not specified
        self.beats_per_measure = 4  # Number of beats per measure, used to determine lengths of notes
        self.name = None  # Name of the instrument to register
        self.loop_index = 0  # Index of initial loop
        self.num_processed = 0  # Number of items processed
        self.loop = False  # Value determining if we are restarting the loop

    def start(self):

        """
        We setup and configure the Sequencer Command instance.

        We also parse the source string for input.
        """

        # Create the SeqCommand instance

        self.command = SeqCommand(self.seq)

        # Parse over the input text:

        while True:

            # Decode the next character

            self.decode()

            # Move the source forward:

            try:

                self.source.forward()

            except:

                # We are done decoding, lets exit:

                break

        if self.loop:

            # Add a endless repeat:

            print("Adding repeat:")

            self.command.repeat(0, -1)

        self.seq.add_seqcom(self.command)

    def decode(self, chord=False):

        """
        Decodes the given MML input.

        We may change our state,
        or toggle a note to be on in the sequencer.

        We also have the option to operate in chord mode,
        meaning that we do not attempt to stop notes.

        :param chord: Determines if we are working with a chord
        :type chord: bool
        """

        # Get our input from the source:

        inp = self.source.get()

        print(inp)

        # Check to see if we are reading a note:

        if inp in self.note_map:

            # Lets handle and read the note:

            self.read_note(no_time=chord)

            if not chord:

                # Increment our invalid index:

                self.num_processed += 1

            return

        # Check if we are resting:

        if inp == 'r':

            # We are resting, get length

            time_amount = self.read_length()

            # Add a rest event:

            self.command.rest(self.find_time_type(time_amount))

            self.num_processed += 1

            return

        # Check if we are reading a chord:

        if inp == '[':

            # Lets continuously read until we reach the end:

            for _ in self.source.read_until(']'):

                # Pass the input onto ourselves:

                self.decode(chord=True)

            # We are done, let's determine the length:

            length = self.find_time_type(self.read_length())

            # Add the event to the SeqCommand:

            self.command.chord(self.notes, length)

            print("Adding chords with notes: {}".format(self.notes))
            print("Length: {}".format(length))

            self.notes.clear()

            self.num_processed += 1

            return

        # Check if we are going up or down an octave:

        # OG: < increased, > decreased

        if inp in ['<', '>']:

            # Determine if we are going up or down:

            if inp == '<':

                # Increase the octave:

                self.octave += 1

                return

            if inp == '>':

                # Decrease the octave:

                self.octave -= 1

                return

        # Check if we are starting a loop:

        if inp == '/' and self.source.peek() == ':':

            # We are starting a loop, lets set our start index:

            self.source.forward()

            self.loop_index = self.num_processed

            return

        if inp == ':' and self.source.peek() == '/':

            # We are at the end of a loop!

            self.source.forward()

            # Add a repeat event to the SeqCommand:

            self.command.repeat(self.loop_index, self.read_number())

            return

        # Check if we are working with endless looping:

        if inp == '$':

            # We are endlessly looping, let's add it at the end:

            self.loop = True

            return

        # Check if we are changing our octave:

        if inp == 'o':

            # Octave is changing, let's read the value:

            self.octave = self.read_number() - 4

            return

        # Check for a velocity value

        if inp == 'v':

            # Reading a velocity value;

            length = self.read_number()

        # Check for a change in default length:

        if inp == 'l':

            # Default length is changing, let's read the value:

            self.default_length = self.read_length()

            return

        # Check for change in tempo:

        if inp == 't':

            # Tempo is changing, let's read the value:

            self.tempo = self.read_length()

            return

        # Check for track change:

        if inp == ';':

            # Change in track, let's reset ourselves:

            if self.loop:

                # We are forever looping, lets add it:

                self.command.repeat(0, -1)

            # Add our current command chain:

            self.seq.add_seqcom(self.command)

            # Create a new SeqCommand:

            self.command = SeqCommand(self.seq)

            return

    def read_note(self, no_time=False):

        """
        Reads a note at the current position.

        We also handle the processing of accidentals, and
        the reading of note lengths.

        Once the note is invoked, we calculate the time the note will take,
        and then disable it.
        If we are working with chords and don't want each note to be waited on,
        then you can pass True to the 'no_time' parameter.
        If the no_time parameter is true, then we will keep a record of the notes invoked,
        and will only stop those notes specified.

        :param no_time: Value determining if we should wait calculate note time
        :type no_time: bool
        """

        # Lets get the note value at this position:

        note = self.source.get()

        # Decode the note into value:

        note_num = self.note_map[note]

        # Read for accidentals and apply them:

        note_val = Note(self.octave, note_num + self.read_accidental())

        if no_time:

            # Lets just add the note to the lists:

            self.notes.append(note_val)

            return

        # Let's get the note length:

        length = self.read_length()

        # Calculate the amount of time to keep the note on:

        time_amount = self.find_time_type(length)

        print("Adding note {} with time {}".format(note_val, time_amount))

        # Add the note to the SeqCommand:

        self.command.note(note_val, time_amount)

    def read_accidental(self):

        """
        Reads an accidental for the current note.

        The accidental must ALWAYS pre-pend the note.
        We return the offset of the note,
        weather that be -1 or 1 step.

        If we encounter an integer, then this is the note length,
        and we will simply return 0 for no change.
        :return: Offset of the note, -1 for flat, 1 for sharp
        :rtype: int
        """

        # Get the next value in the audio collection:

        val = self.source.peek()

        # Otherwise, determine the accidental:

        if val in ['+', '#']:

            # We have a sharp note, return offset of 1:

            self.source.forward()

            return 1

        if val in ['-']:

            # We have a flat, return offset og -1

            self.source.forward()

            return -1

        # No accidental, return nothing:

        return 0

    def read_length(self):

        """
        Reads the length of an arbitrary item,
        be it a note, rest, chord, ect.

        We assume our current index is the item(or end of the item)
        we wish to figure out the length of.

        We will continue to read values and push the seeker forward
        until we find no more integers.
        We also handle doted notes!

        We return the length of the note, 1 for whole, 2 for half, 4 for quarter, ect.

        :return: length of the value we are currently on
        :rtype: int
        """

        # Lets get the note length:

        length = self._read_ints()

        # Check if source is dot:

        last = 1
        final = 0

        while True:

            if self.source.peek() == '.':

                # We have a dotted note, let's add 0.5 to our value:

                self.source.forward()

                last = last * 0.5
                final += last

                continue

            break

        length = length + final if length else self.default_length + final

        # We are done, let's return:

        return length if length else self.default_length

    def read_number(self):

        """
        Reads the number after an arbitrary item,
        taking dots into account and converting them into floats.

        We assume our current index is the item we want the length of.
        Like 'read_length()', we will continue to push the seeker forward
        until we stop reading ints.

        :return: Returns the number after the current position
        :rtype: float
        """

        final = 0

        # Read initial ints:

        ints = self._read_ints()

        if ints:

            # Have some values, add them to the final value:

            final += ints

        # Check to see if we are working with decimals:

        if self.source.peek() == '.':

            # Working with decimals, move forward and read:

            self.source.forward()

            final = float(str(final) + '.' + str(self.read_length()))

        # Lets return:

        return float(final)

    def _read_ints(self):

        """
        Continuously reads ints from the source until we reach a non-integer value.

        Not very useful on our own,
        we act as a backend to 'read_length()' and 'read_number()',
        which offer some useful dot logic.

        :return: Integer read
        :rtype: int
        """

        final = ''

        while self.source.has_next:

            # Get the next value in the source:

            val = self.source.peek()

            # Check if the value is an int:

            if val.isdigit():

                # It is! Let's add it to the final string:

                final = final + val

                self.source.forward()

                continue

            # Next value is NOT an int, let's return.

            break

        return int(final) if final != '' else False


class MMLWrapper(Sequencer):

    """
    MML Wrapper for the PySynth sequencer!

    We auto-load the MMLDecoder,
    and offer easy-to-use methods for loading other input modules.
    """

    def __init__(self, middle_freq=440.0):

        super(MMLWrapper, self).__init__(middle_freq=middle_freq)

        # Load the MMLDecoder

        self.bind_decoder(MMLDecoder())

    def load_string(self, data):

        """
        Creates a StringMMLInput module and binds it to this sequencer.

        :param data: String to add to the input module
        :type data: str
        """

        # Bind the StringMMLInput

        self.bind_input(StringMMLInput())

        # Load the input into the StringMMLInput:

        self._input.load_string(data)
