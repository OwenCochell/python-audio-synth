"""
PySynth converters.

We handle the conversion of signed floats into something else.

For example, the WaveModule requires bytes for audio information.
PySynth only understands floats, and will send floats to the output modules.

Because of this,
output handlers can optionally specify a converter.
All information received will be automatically converted by the converters.

Your module can use these converters, so they don't have to convert values themselves.
"""

import struct


class BaseConverter(object):

    """
    BaseConverter - Class all child converters must inherit!

    A converter allows for the automatic, under the hood conversion of audio information.

    Output modules can add converters to themselves, and configure them accordingly.
    Because of the broad use case,
    we keep the implementation very open.

    It is up to the OutputModule to properly attach and configure converters!
    """

    def convert(self, inp):

        """
        Convert class - This is what the output module will be calling.

        You can safely assume that the input will be signed floats.
        You can return anything you like,
        although a bytes object might be the most relevant bet.

        :param inp: Input to convert
        :type inp: float
        :return: Anything that the converter thinks is relevant
        """

        pass


class NullConvert(BaseConverter):

    """
    Like the name says,
    we simply do nothing!
    """

    def convert(self, inp):

        return inp


class FloatToByte(BaseConverter):

    """
    Converts signed floats into bytes!

    You can specify the byte order when instantiating,
    the default being little-endian.
    If you want big endian, then pass True to the 'big' parameter when instantiating.

    :param big: Determines if we should use big endian
    :type big: bool
    """

    def __init__(self, big=False):

        self.char = ('>' if big else '<') + 'f'  # Prefix char, working with floats and specified byte order
        self.struct = struct.Struct(self.char)  # Optimised struct class

    def convert(self, inp):

        """
        Converts the given float into bytes,
        using the byte order specified when instantiating.

        :param inp: Audio input
        :type inp: float
        :return: Float in bytes
        :rtype: bytearray
        """

        # Convert and return:

        return self.struct.pack(inp)


class IntToByte(BaseConverter):

    """
    Converts signed ints into bytes!

    Like FloatToByte, you can specify a the byte order,
    the default being little-endian.

    :param big: Determines if we use big endian
    :type big: bool
    """

    def __init__(self, big=False):

        self.char = ('>' if big else '<') + 'h'  # Prefix char, working with ints is specified byte order
        self.struct = struct.Struct(self.char)  # optimised struct class

    def convert(self, inp):

        """
        Converts the signed ints into bytes!

        :param inp: Input of ints
        :type inp: int
        :return: Int in bytes
        :rtype: bytearray
        """

        return self.struct.pack(inp)
