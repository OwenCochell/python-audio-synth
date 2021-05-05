"""
MIDI Events - Python classes representing MIDI events.

We implement the following channel voice messages:

    > NoteOff - Turns a note off
    > NoteOn - Turns a note on
    > PolyphonicAftertouch - Represents changes in pressure while the note is on, individually
    > ChannelAftertouch - Like PolyphonicAftertouch, except only the highest aftertouch value is sent
    > ControlChange - Changes the value of a certain synth feature
    (Breath pedal, modulation, volume, phaser, ect.)
    > ProgramChange - Represents a change in instrument for the given channel.
    (Has something to do with patches? Need more research...)
    > PitchWheel - Changes the pitch of the ongoing audio
    > SysEx - Manufacturer and hardware information
    (We don't really care about this one, might implement for fun though...)

Each of these events MUST occur within a channel!

We also offer some MIDI meta-event wrappers:

    > TBD...

MIDI events will contain information and instructions on how the decoder should handle the event.
They might even contain code that will allow them to change the state of the decoder themselves?
"""


class BaseMIDIEvent(object):

    """
    Base MIDI event all MIDI events will inherit!
    """

    def __init__(self) -> None:
        
        self.flags = None  # Flags of the object
        self.time = None  # Object representing time information
        self.raw = None  # Raw bytes of the MIDI event

    @classmethod
    def from_bytes(cls, bytes):

        """
        Creates a MIDI event from raw bytes.

        Our packets should be able to create valid copies of themselves
        given valid byes of MIDI data.
        """

        raise NotImplementedError("Must be overridden in child class!")


    @classmethod
    def from_object(cls, obj):

        """
        Creates a MIDI event from an object.

        Our packets should be able to create valid copies of themselves
        given valid objects contaning MIDI data.

        These objects should use the standardized storage system.
        #TODO: Elaborate. 
        """


class ChannelVoiceEvent(BaseMIDIEvent):

    """
    ChannelVoiceMessages - Represents a packet that represents musical performance information.
    """

    def __init__(self) -> None:

        super().__init__()

        self.channel = None  # Channel number to operate on


class NoteOff(ChannelVoiceEvent):

    """
    NoteOff - Represents a note toggling to off.

    This event tells the decoder to toggle a note off.
    We also contain information on velocity,
    as well as timing information that will help with sequencing.
    """

    def __init__(self, note, velocity) -> None:
        
        super().__init__()

        self.note = note  # MIDI note number
        self.velocity = velocity  # Velocity of the NoteOff event

    @classmethod
    def from_object(cls, obj):
        
        """
        Creates a NoteOff event with the given object.
        """

        temp = cls(obj.note, obj.off_velocity)
        temp.channel = obj.channel

        return temp


class NoteOn(ChannelVoiceEvent):

    """
    NoteOn - Represents a note toggling to on.

    This event tells the docoder to toggle a note on.
    We also contain information on velocity,
    as well as timing information that will help with sequencing. 
    """

    def __init__(self, note, velocity) -> None:
        
        super().__init__()

        self.note = note  # MIDI note number
        self.velocity = velocity  # # Velocity of the NoteOn event

    @classmethod
    def from_object(cls, obj):

        """
        Creates a NoteOn event with the given object.
        """

        temp = cls(obj.note, obj.velocity)

        return temp


class PolyphonicAftertouch(ChannelVoiceEvent):

    """
    Represents a change in pressure for a particular key,
    after the key is pressed down.
    """

    def __init__(self, key, pressure) -> None:
        
        super().__init__()

        self.key = key  # Key with changed pressure
        self.pressure = pressure  # Changed pressure value


class ChannelAfterTouch(ChannelVoiceEvent):

    """
    Represents a channel after touch event,
    which is the greatest change in pressure in a given key after it is pressed down. 
    """

    def __init__(self, pressure) -> None:

        super().__init__()

        self.pressure = pressure  # Changed pressure value


class ControlChange(ChannelVoiceEvent):

    """
    Represents a change in a controller value.
    """

    def __init__(self, param, value) -> None:

        super().__init__()

        self.param = param
        self.value = value


class ProgramChange(ChannelVoiceEvent):

    """
    Represents a program change in the specified channel.

    This usually means that a new instrument should be selected for this channel.
    """

    def __init__(self, num) -> None:
        
        super().__init__()

        self.num = num  # Program number


class PitchWheel(ChannelVoiceEvent):

    """
    Represents a pitch wheel event.
    """

    def __init__(self, num) -> None:

        super().__init__()

        self.bend = num
