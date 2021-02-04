"""
This file contains tools for preforming synthesis with multiple oscillators.
"""

import math


class BaseSynth(object):

    """
    Base synthesiser object all synths will inherit.

    The synthesisers will operate like oscillators,
    merging multiple and outputting information in a generator like fashion.

    We offer some common features, such as support for iteration,
    and a framework all synths should follow.
    """

    def start(self):

        """
        Prepares the synth for iteration.
        Sub-synths can put anything they like here.

        This method should also be called when preparing the oscillator for iteration,
        i.e '__iter__' is called.
        """

        pass

    def calc_next(self):

        """
        This function will return the next value computed value.
        Most of the math should reside here.

        :return: Float representing the next number in the waveform
        :rtype: float
        """

        raise NotImplemented("Sub-synths should implement this method!")

    def __iter__(self):

        """
        Prepares the oscillator for iteration.
        We call the 'start' method to prepare the oscillator,
        and return ourselves for iteration.

        :return: This synth
        :rtype: BaseSynth
        """

        # Start the synth:

        self.start()

        # Return this synth:

        return self

    def __next__(self):
        """
        Gets the next value and returns it.

        :return: Next computed value
        :rtype: float
        """

        return self.calc_next()


class FMSynth(BaseSynth):

    """
    Preforms FM synthesis.
    Takes a carrier oscillator, modulator oscillator,
    and a modulation constant(?)
    """

    def __init__(self, carry, mod, const):

        self.carry = carry  # Carrier oscillator
        self.mod = mod  # Modulator oscillator
        self.const = const  # Modulation constant

    def calc_next(self):

        """
        Modulate the carrier wave and return the value.

        :return: Float
        :rtype: float
        """

        val = math.cos(self.carry.calc_next() + self.const * self.mod.calc_next())

        return val
