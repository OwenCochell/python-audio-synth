"""
This file contains filters for altering gain, frequencies, and others.
"""

from math import cos, pi, sqrt, pow, e

from pysynth.utils import AudioBuffer, BaseModule


class BaseFilter(BaseModule):

    """
    Base filter that all filters MUST inherit!

    We implement some useful functionality,
    and offer a framework for other filters
    to base themselves upon.
    """

    def sinc_n(self, x):

        """
        Normalised sinc function.

        sin(2PI * x) / (PI * x)

        We automatically handle division by zero and other quirky things.
        Read all about it here:

        https://en.wikipedia.org/wiki/Sinc_function

        :param x: Value of our sample
        :param x: float
        :return: Output of the normalised sinc function
        :rtype: float
        """

        pass


class FirstOrderRecursiveFilter(BaseFilter):

    """
    Parent class for all first order recursive filters.

    We operate under this formula:

    y[n] = a0 * x[n] + a1 * x[n-1] + a2 * x[n-2] + a3 * x[n-3] + ...
        + b1 * y[n-1] + b2 * y[n-2] + b3 * y[n-3] + ...

    Where:

    n = current index
    x[n] = Input signal
    y[n] = Output signal

    a = A recursive coefficient
    b = B recursive coefficient

    Read all about it here:

    http://www.dspguide.com/ch19/1.htm

    This filter takes an arbitrary number of recursive coefficients as two lists,
    one representing A coefficients and the other representing B coefficients.

    After the coefficients have been loaded, we utilise the algorithm above to filter out the input signal.
    It does not matter what we are filtering out,
    that should be determined by sub-classes that calculate the coefficients.
    """

    def start(self):

        """
        Prepares this filter for iteration.

        We only set up the audio buffers, which hold previously calculated values.
        """

        # Determine the size of the input buffer:

        self.inp = AudioBuffer(len(self.a) - 1, no_fill=True)
        self.inp.fill_buffer(ignore_global=True)

        # Determine the size out of the output buffer:

        self.out = AudioBuffer(len(self.b), no_fill=True)
        self.out.fill_buffer(ignore_global=True)

    def reg_coeff(self, a, b):

        """
        Registers the given coefficients with this filter.

        Each parameter should be a list containing the recursive coefficients in use.

        :param a: Tuple containing all A coefficient values.
        :type a: tuple
        :param b: Tuple contaning all B coefficient values
        :type b: tuple
        """

        # Set both lists:

        self.a = tuple(a)
        self.b = tuple(b)

    def hertz_to_frac(self, freq):

        """
        Given a frequency, calculate the frequency fraction as a fraction of the sampling rate(Between 0 - 0.5).

        We use the following equation:

        freq / (S * 0.5)

        Where:

        freq = frequency in hertz
        S = sampling rate - sampled values per second

        :param freq: Frequency in hertz
        :type freq: float
        :return: frequency fraction
        :rtype: float
        """

        # Calculate the cutoff value and return it

        return freq / (self.sample_rate * 0.5)

    def frac_to_hertz(self, frac):

        """
        Given a frequency fraction(Between 0 - 0.5), calculate the frequency in hertz.

        We use the following equation:

        frac * S * 0.5

        Where:

        frac = cutoff value
        S= sampling rate - sampled values per second

        :param frac: Frequency fraction
        :type frac: float
        :return: Frequency in hertz of the cutoff value
        :rtype: float
        """

        # Calculate the frequency in hertz and return it:

        return frac * self.sample_rate * 0.5

    def calc_cutoff(self, frac):

        """
        Calculates the cutoff value for this filter, given the frequency fraction.

        We utilise the following equation:

        2 - cos(2 * PI * frac) - sqrt((2 - cos(2 * PI * frac))^2 - 1)

        where:

        frac = frequency fraction

        :param frac: Frequency fraction
        :type frac: float
        :return: Cutoff value for the specified frequency
        :rtype: float
        """

        # Calculate the cutoff value and return it

        return 2 - cos(2 * pi * frac) - sqrt(pow(2 - cos(2 * pi * frac), 2) - 1)

    def calc_time(self, time_cost):

        """
        Calculates the time value for this filter, given a time constant.

        We utilise the following equation:

        e ^ (-1 / time_const)

        Where:

        time_const = Time constant - the number of samples it takes to decay to the 36.8% of the final value

        :param time_cost: Time constant
        :param: int
        :return: Time value
        :rtype: float
        """

        # Calculate and return the time value:

        return pow(e, -1/time_cost)

    def get_next(self):

        """
        Sends the input signal through the filter and outputs the filtered data.

        :return: Filtered data
        :rtype: float
        """

        # Gets our next value from the source buffer:

        curr = self.get_input()

        # Add this value to the input value:

        self.inp.pop()
        self.inp.appendleft(curr)

        # Calculate A value:

        final = 0

        for num, a in enumerate(self.a):

            # Calculate the value at this position:

            final = final + (a * self.inp[0])

        # Calculate B value:

        for num, b in enumerate(self.b):

            # Calculate the value at this position:

            final = final + (b * self.out[num])

        # Add the final value to the output:

        self.out.pop()
        self.out.appendleft(final)

        # Return the value:

        return final


class BasicFilter(FirstOrderRecursiveFilter):

    """
    An implementation of a simple first order recursive filter.

    The FirstOrderRecursiveFilter does all the heavy lifting,
    we just generate the A and B coefficients and pass them along.

    We utilise very simple algorithms to generate these coefficients:

    LOW PASS - Allow frequencies below cutoff:

    a0 = 1 - x
    b1 = x

    HIGH PASS - Allow frequencies above cutoff:

    a0 = (1+x)/2
    a1 = -(1+x)/2
    b1 = x

    BAND PASS - Allow frequencies within band:

    a0 = 1 - K
    a1 = 2(K-R) * cos(2 * PI * freq)
    a2 = R^2 - K
    b1 = 2 * R * cos(2 * PI * freq)
    b2 = -R^2

    BAND REJECT - Reject frequencies within band:

    a0 = K
    a1 = -2 * K * cos(2 * PI * freq)
    a2 = K
    b1 = 2 * R * cos(2 * PI * freq)
    b2 = -R^2

    Where:

    x = Filter response - frequency or time based
    B = Band width
    freq = cutoff frequency
    R = 1 - 3B
    K = (1 - 2 * R * cos(2 * PI * freq) + R^2) / (2 - 2 * cos(2 * PI * freq))

    This filter is very simple,
    and may not be as robust or preform as well as other filters.

    We offer methods for acquiring these coefficients,
    but more importantly we pass them along to our parent.

    Have a read on our coefficient equations here:

    http://www.dspguide.com/ch19/2.htm

    :param resp: Filter response. Can be frequency/time value, or anything else. For band filters,
        this value should be a frequency cutoff value
    :type: resp: float
    :param band_width: Bandwidth of the filter, represented as a fraction of he sampling frequency.
        Only used by band filters
    :type band_width: float
    :param filt_type: Type of filter to generate, options listed above.
        You should use the filter constants to define this.
    :type: filt_type: int
    :param param_type: Determines what we should convert the given filter response to,
        option being frequency, time, or raw, raw being no conversion is done.
        You should use the BasicFilter constants to define this.
    :type param_type: int
    """

    LOW = 0
    HIGH = 1
    BP = 2
    BR = 3

    FREQ = 0
    TIME = 1
    RAW = 2

    def __init__(self, resp, band_width=None, filt_type=0, param_type=2):

        # Init our parent class:

        super(BaseFilter, self).__init__()

    def gen_lp(self, resp):

        """
        Generates low pass A and B coefficients given a filter response.

        :param resp: Filter response
        :type resp: float
        :return: Two tuples containing A and B coefficients, respectively
        :rtype: tuple
        """

        # Generate our coefficients and exit:

        return tuple([1-resp]), tuple([resp])

    def gen_hp(self, resp):

        """
        Generates high pass A and B coefficients given a filter response.

        :param resp: Filter response
        :type resp: float
        :return: Two tuples containing A and B coefficients, respectively
        :rtype: tuple
        """

        # Generate our coefficients and exit:

        return ((1+resp)/2), (-(1+resp)/2)


class MovingAverage(BaseFilter):

    """
    Python implementation of the Recursive Moving Average Filter.

    We utilise recursion to find the average values,
    although we use summation to find the first value.

    We utilise this equation:

    y[i] = y[i-1] + x[i+p] - x[i-q]

    p = (M - 1) / 2
    q = p+1

    where M = number of points, and i is current index.

    The total number of points MUST BE AN ODD NUMBER!!!

    Might not be very useful for audio synthesis,
    but totally something cool to have.

    :param pointsize: Number of points to include in the calculations.
    :type pointsize: int
    """

    def __init__(self, pointsize):

        super(MovingAverage, self).__init__()

        if pointsize % 2 == 0:

            raise TypeError("Pointsize must be odd!")

        self.buffer = None  # AudioBuffer to use, creates it during 'start()'

        self.size = pointsize

        self.prev = 0  # Previous value calculated
        self.upper = int((self.size-1) / 2)  # Upper bound to calculate
        self.lower = self.upper + 1  # Lower bound to calculate

    def start(self):

        """
        Start method, creates a buffer to hold all values.

        By now, the user should have bound the source to this object.
        """

        self.buffer = AudioBuffer(self.upper+self.lower+1+self.size, self.input)

    def calc_conv(self, start=0):

        """
        Calculates the next given point via convolution.

        :param start: Starting value of the operation
        :type start: int
        :return: Average sum at the given point
        :rtype: float, int
        """

        total = 0

        for num in range(start, self.size+start):

            # Retrieve value and add it to total

            total = total + self.buffer[num]

        # Divide total value by size:

        return total / self.size

    def calc_recursive(self):

        """
        Calculates the current value recursively.
        """

        # Calculate and return our value:

        return (self.prev + self.buffer[self.lower+self.upper] - self.buffer[0]) / self.size

    '''
    def calc_next(self):

        """
        Calculates the next value in the Moving Average Filter.
        """

        val = self.calc_conv()

        self.buffer.popleft()

        return val
'''

    def calc_next(self):

        """
        Calculates the next value in the Moving Average Filter.

        The first 'lower' values are calculated via convolution.
        After these values are calculated, then the recursive algorithm is used.

        :return: Next calculated value
        :rtype: float, int
        """

        final = 0

        if self.index < self.lower:

            # Calculate next value via convolution:

            self.prev = self.calc_conv(start=self.index)

            return self.prev

        # Done, lets start the recursive operation:

        # Calculate next value via recursion:

        self.prev = self.calc_recursive()

        # Popping the buffer so we can get our next value:

        self.buffer.popleft()

        return self.prev


class JanckedOut(BaseFilter):

    """
    Totally Jancked Filter that messes up everything that goes into it!
    """

    def __init__(self, pointsize):

        super(JanckedOut, self).__init__()

        if pointsize % 2 == 0:

            raise TypeError("Pointsize must be odd!")

        self.buffer = None  # AudioBuffer to use, creates it during 'start()'

        self.size = pointsize

        self.prev = 0  # Previous value calculated
        self.upper = int((self.size-1) / 2)  # Upper bound to calculate
        self.lower = self.upper + 1  # Lower bound to calculate

    def start(self):

        """
        Start method, creates a buffer to hold all values.

        By now, the user should have bound the source to this object.
        """

        self.buffer = AudioBuffer(self.upper+self.lower+1+self.size, self.input)

    def calc_conv(self, start=0):

        """
        Calculates the next given point via convolution.

        :param start: Starting value of the operation
        :type start: int
        :return: Average sum at the given point
        :rtype: float, int
        """

        total = 0

        for num in range(start, self.size+start):

            # Retrieve value and add it to total

            total = total + self.buffer[num]

        # Divide total value by size:

        return total / self.size

    def calc_recursive(self):

        """
        Calculates the current value recursively.
        """

        # Calculate and return our value:

        return self.prev + self.buffer[self.size-self.upper] - self.buffer[0]

    def calc_next(self):

        """
        Calculates the next value in the Moving Average Filter.

        The first 'lower' values are calculated via convolution.
        After these values are calculated, then the recursive algorithm is used.

        :return: Next calculated value
        :rtype: float, int
        """

        final = 0

        if self.index < self.lower:

            # Calculate next value via convolution:

            self.prev = self.calc_conv(start=self.index)

            return self.prev

        # Done, lets start the recursive operation:

        # Calculate next value via recursion:

        self.prev = self.calc_recursive()

        # Popping the buffer so we can get our next value:

        self.buffer.popleft()

        return self.prev


class AmplScale(BaseFilter):

    """
    We scale the amplitude by the factor given.
    """

    pass


class AmpFilter(BaseFilter):

    """
    We remove amplitudes that fall within certain parameters.
    """

    pass
