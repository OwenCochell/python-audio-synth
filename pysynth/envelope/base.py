"""
Base components for envelopes.

Envelopes are modules that change a certain parameter of the sound over time.
This parameter can be anything, although we offer built in envelopes that can handle some common use cases.

The envelope sub-module is split up into the following files:

    > base.py - This file! Defines framework and uses cases
    > amp.py - Contains envelopes for changing the amplitude(loudness) of the sound
    > filt.py - Contains envelopes for changing the filtered frequencies of the sound
    (Is this redundant? Should filters be able to do this themselves?)
    > freq.py - Contains envelopes for changing the frequency this chain is operatting at
    (Again, redundant? Already some basic parameter time programming, is this necessary?)

Each file contains diffrent implementations of an envelope,
which is how the envelope is controlled,
but each envelope in each file will affect the same thing.
"""


from pysynth.utils import BaseModule


class BaseEnvelope(BaseModule):

    """
    Base class for envelopes - All child envelopes should inherit this class!

    Each sub-file will have a base implementation for their own envelopes.
    """

    pass