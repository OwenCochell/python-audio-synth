"""
PySynth oscillators for generating numbers
#TODO: Fix description
"""

import math
import random

from pysynth.utils import BaseModule


class BaseOscillator(BaseModule):

    # TODO: Fix this description!:
    """
    BaseOscillator class, all oscillators will inherit this class.
    We offer functionality for iteration and comparison(?)

    The parameters will remain constant for all child oscillators.
    """

    def val_calc(self):

        """
        Calculates and returns the inner value of the function.
        This is based off of frequency and sampling rate.

        :return: Number inside function
        :rtype: float
        """

        return math.pi * self.freq.value * (float(self.index) / float(self.sample_rate))

    def __next__(self):

        """
        Gets the next value and returns it.

        :return: Next computed value
        :rtype: float
        """

        val = self.get_next()

        self.index += 1

        return val


class SineOscillator(BaseOscillator):

    """
    SineOscillator, generates audio data,
    oscillating over a sine wave
    """

    def get_next(self):

        """
        Calculates the next number in our sine wave.

        :return: Number at this point
        """

        sine = math.sin(2.0 * self.val_calc())

        return sine


class SquareOscillator(BaseOscillator):

    """
    SquareOscillator, oscillates over a square wave.
    """

    def start(self):

        """
        Prepares the SquareOscillator for iteration.
        We create a SineOscillator to pull values from.
        """

        # Create a SineOscillator:

        self._sine = SineOscillator()

        # Set the oscillator AudioParameter to ours:

        self._sine._info.freq = self._info.freq

    def get_next(self):

        """
        Calculates the next value in the oscillator.
        Under the hood, we use a SineOscillator to generate values,
        which we then alter to from a square waveform.

        :return: next number in the wave
        :rtype: float
        """

        # Get next value from sine oscillator:

        val = next(self._sine)

        if val > 0:

            # Make value max:

            return 1.0

        if val < 0:

            # Make value negative

            return -1.0

        # Return zero:

        return 0.0


class SawToothOscillator(BaseOscillator):

    #TODO: Fix this!
    """
    Oscillates over a sawtooth waveform.
    """

    def get_next(self):

        """
        Calculates the next value in the SawTooth wave.
        Under the hood, we use a SineOscillator to generate values,
        and we divide each value by pi.

        :return: Next value in the SawTooth wave
        :rtype: float
        """

        if self.index == 0:

            # Zero, lets return zero:

            return 0

        return -(2 / math.pi) * math.atan(1 / math.tan(self.val_calc()))


class TriangleOscillator(BaseOscillator):

    """
    Continuously oscillates over a Triangle waveform.
    """

    def start(self):

        """
        Prepares the object for iteration.
        We assign an '_index' parameter to keep track of our index.
        """

        # Create a SineOscillator

        self._sine = SineOscillator()
        self._sine._info.freq = self._info.freq

    def get_next(self):

        """
        Calculate and return the next value in our triangle waveform.
        """

        # Get our value:

        return (2 / math.pi) * math.asin(next(self._sine))


class WhiteOscillator(BaseOscillator):

    """
    WhiteOscillator, continuously generates white noise.
    """

    def get_next(self):

        """
        Computes the next value.
        We randomly generate values, so their is not much calculating to do here.

        :return: Randomly generated number
        :rtype: float
        """

        return random.uniform(-1, 1)


class ZeroOscillator(BaseOscillator):

    """
    Returns zero every time!
    """

    def get_next(self):

        """
        Returns zero.

        :return: Zero
        :rtype: float
        """

        return 0.0


class ImpulseOscillator(BaseOscillator):

    """
    Works as an impulse function, common in DSP.

    Essentially, if the index is zero, we return one.
    Otherwise, we simply return zero.

    This is only relevant for testing purposes, and will not generate any meaningful audio.
    """

    def get_next(self):

        """
        Calculates the value of the impulse oscillator.

        If index is zero, return one.
        If index is not zero, return zero.

        :return: Value of the impulse function
        :rtype: float
        """

        if self.index == 0:

            # Index is zero, return 1.0

            return 1.0

        # Index is not zero, return zero

        return 0.0
