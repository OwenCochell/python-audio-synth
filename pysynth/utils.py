"""
General utilities used by PySynth
"""


import time

from collections import deque


def get_time():

    """
    Gets the current time and returns it.

    We use the most accurate clock available and we return the time in nanoseconds.

    Great for event calculations.

    :return: Time in nano seconds
    :rtype: float
    """

    return time.perf_counter()


def amp_clamp(val):

    """
    Clamps an incoming value to either -1 or 1.

    :param val: Value to clamp
    :type val: float
    :return: Clamped value
    :rtype: float
    """

    if val > 1.0:

        # Too big, clamp it

        return 1.0

    if val < -1.0:

        # Too small, clamp it

        return -1.0

    # No changes necessary

    return val


class BaseModule(object):

    """
    PySynth base module - Class all modules will inherit!

    A 'synth chain' is a collection of modules strung together.
    A 'module' is a component in this chain.
    If a module is 'linked' to another, then it will get it's input from the linked module.

    Here is an example of a synth chain:

    osc -> LP_filt(200) -> asdr(0.2, 0.5, 0.7, 1) -> out

    In this example, an oscillator is attached to a filter,
    which is attached to an asdr envelope, with is then sent to output.

    This class handles modules receiving inputs, traversing the synth,
    starting the synth, and stopping the synth.
    We also keep track of certain attributes, like the frequency of this synth chain,
    as well as the sampling rate of this synth chain.

    Most of these features will be utilised by the sequencer,
    like for changing the frequency of the oscillator(s),
    and for stopping and starting components.

    However, the functionality defined within could be useful to other modules,
    as they may need to access the parameters of modules connected to them.

    If a module inheriting this class defines it's own '__init__()' method,
    then it MUST call the '__init__()' method of the BaseModule it inherits!
    """

    def __init__(self, freq=440.0, samp=44100.0):

        self.input = AudioCollection()  # AudioCollection, allows for multiple inputs into a single node
        self.output = None  # AudioCollection of the node we get connected to
        self.index = 0  # Index of this object
        self.started = False  # Value determining if we have started iteration
        self._info = ModuleInfo(freq=freq, samp=samp)  # ModuleInfo class for storing info

    def start(self):

        """
        Function called when we are getting prepared for iteration.
        'start' is invoked when '__iter__()' is called.

        The module should assume that if 'start()' is called,
        then the module should be reset to it's initial state.

        The module can put any setup code here they like.
        """

        pass

    def stop(self):

        """
        Function called when we are stopping the chain.
        'stop()' will be invoked by the sequencer when this synth chain this module is apart of it stopped.

        The module can put any stop code here they like.
        """

        pass

    def get_next(self):

        """
        This is the function called when we need an item from the module.
        'get_next()' is invoked upon each call to '__next__'.

        MODULES MUST ALWAYS RETURN FLOATS!

        We only understand floats, and if something else is returned,
        then their is a very high chance that their will be trouble.
        A module must only other types if they understand what is receiving them!

        Most likely, a module's math operations will go here,
        but they don't have too if it makes more sense to put them elsewhere.

        :return: Next value from this item
        :rtype: float
        :raise: NotImplemented: If this class is not overridden
        """

        raise NotImplemented("This method should be overridden in the child class!")

    def get_input(self):

        """
        Gets a value from the AudioCollection attached to us.
        The user can optionally specify a number of values to retrieve.

        If we receive 'None' from the module connected to us,
        then we will forward it to the module that is ahead of us,
        as 'None' means this synth is stopping, and we should pass it up
        so synths further down the line can know.

        :return: Item from the AudioCollection
        :rtype: float
        """

        # Get an item from the audio collection:

        item = next(self.input)

        if item is None:

            # We are None! Stop this object somehow...

            self.stop()

        return item

    def get_inputs(self, num):

        """
        Gets a number of items from the AudioCollection.

        We return these items as a tuple.

        :param num: Number of items to retrieve
        :type num: int
        :return: Tuple of items from AudioCollection
        """

        # Get a number of items from the collection:

        final = []

        for i in range(num):

            # Get input:

            item = self.get_input()

            if item is None:

                # We are None! Already handled, lets return

                return None

            final.append(i)

        # Convert to tuple and return:

        return tuple(final)

    def bind(self, module):

        """
        Binds an iterable to this class.

        We register the iterable to the AudioCollection,
        and then let it take it from here.

        We also bind their information to us.

        :param module: Iterable to add. This should ideally inherit BaseModule
        :type module: iter
        """

        # Add the iterable to the AudioCollection:

        self.input.add_module(module)

        # Add their info to us:

        self._info = module._info

        # Add ourselves to the output:

        module.output = self

    def unbind(self, module):

        """
        Unbinds an iterable from this class.

        We tell AudioCollection to remove the module.

        :param module: Module to remove
        :type module: iter
        """

        # Remove the module from the AudioCollection:

        self.input.add_module(module)

        # Unregister info:

        module.info = ModuleInfo()

        # Remove ourselves from the output:

        module.output = None

    def traverse_link(self):

        """
        Traverses the links attached to this module.

        We act as a generator, so one could iterate over us in a for loop.
        We utilise recursion to traverse the entire link, ad we do it like so:

            - yield ourselves
            - Tell our audio collection to traverse over the items it is connected to
            - yield the items received from the AudioCollection
            - Exit when all links have been traversed

        Because each node has an AudioCollection,
        we will be able to traverse the links until we reach the end.

        This operation can be invoked at any point in the synth,
        and will will traverse back to the start.

        :return: Objects in the link
        :rtype: BaseModule
        """

        # First, yield ourselves:

        yield self

        # Now, continue until we reach a 'StopIteration' exception

        for mod in self.input.traverse_link():

            # yield the module:

            yield mod

    @property
    def freq(self):

        """
        Getter for the frequency of this module.

        :return: Frequency for this module
        :rtype: AudioValue
        """

        # Get the frequency and return it:

        return self._info.freq

    @freq.setter
    def freq(self, freq):

        """
        Setter for the frequency.

        Under the hood, AudioCollection schedules an event at this instant
        to set the value to.

        If you want more fined control for chaining this value,
        then you should instead get the AudioValue,
        and schedule an event.

        :param freq: Frequency to set
        :type freq: float
        """

        # Set the frequency:

        self._info.freq.value = freq

    @property
    def sample_rate(self):

        """
        getter for the sampling rate of this module.

        :return: Sampling rate of this module
        :rtype: float
        """

        return self._info.rate

    @sample_rate.setter
    def sample_rate(self, samp):

        """
        Setter for the sampling rate.

        :param samp: Sampling rate to set
        :type samp: float
        """

        self._info.rate = samp

    @property
    def info(self):

        """
        Getter for info of this module.

        :return: Info for this module
        :rtype: Moduleinfo
        """

        return self._info

    @info.setter
    def info(self, info):

        """
        Setter for the info of this module.

        We traverse the other links in out chain,
        and set their values to this info instance.

        :param info: ModuleInfo instance to add to module, and links
        :type info: Moduleinfo
        """

        # Add this info to our value:

        self._info = info

        # Add this info to all links:

        for link in self.input._objs:

            # Set the info instance:

            link.info = self._info

    def __iter__(self):

        """
        Prepares this module for operation.

        We do a few things here:

            - Set our index to 0
            - Call our start method
            - Tell our AudioCollection to prepare all input modules
            - Set our 'started' attribute to True

        This allows us to start all sub-modules in the synth chain.
        This utilises some form of recursion,
        as all modules will call sub-modules to start their own components.

        :return: This module
        :rtype: BaseModule
        """

        # Call the start method:

        self.start()

        # Reset the index value:

        self.index = 0

        # Prepare the sub-modules:

        self.input.start_modules()

        # Set our started value:

        self.started = True

        # Return ourselves:

        return self

    def __next__(self):

        """
        Gets the next value in this module and returns it.

        We call 'get_next()' to get this value,
        and then we increase the index of this module.

        :return: Next computed value
        :rtype: float
        """

        val = self.get_next()

        self.index += 1

        return val


class ModuleInfo:

    """
    Common info shared between modules.

    Instead of setting each parameter manually,
    we simply provide a 'ModuleInfo' to each module as it's added to the link.

    This allows us to save time when updating the module info,
    as we only need to change one 'ModuleInfo' instance to change the values of eveything.

    Each module creates it's own 'ModuleInfo' instance,
    but it gets overridden when connected to another module.
    """

    def __init__(self, freq=440.0, samp=44100.0):

        self.__slots__ = ['freq', 'samp']  # Slots to to optimise for storage

        self.freq = AudioValue(freq, 0, samp)  # AudioValue representing the frequency
        self.rate = samp   # Sampling rate of this synth


class AudioCollection:

    """
    A collection of audio-generating modules.
    When a value is requested, all the modules are sampled and
    additive synthesis is preformed on them.
    """

    def __init__(self):

        self._objs = []  # Audio objects in our collection

        self.change = True

    def add_module(self, node, start=False):

        """
        Adds a PySynth node to the collection.

        We can optionally start the module before adding it.
        Great for if we are adding something on the fly!

        :param node: PySynth node to add
        :type node: BaseModule
        :param start: Value determining if we are starting
        :type start: bool
        """

        if start:

            # Start the module:

            node = iter(node)

        self._objs.append(node)

        self.change = not self.change

    def start_modules(self):

        """
        Prepares all modules for iteration.

        We call the '__iter__()' method on each module,
        and let them do the rest.
        """

        # iterate over our modules:

        for mod in self._objs:

            # Prepare the module:

            iter(mod)

    def remove_module(self, node):

        """
        Removes a PySynth node from the collection.

        :param node: PySynth node to remove
        """

        self._objs.remove(node)

    def traverse_link(self):

        """
        Iterates over our bound nodes, and yield them.

        We utilise recursion to iterate over the links.
        Once we encounter None, the we are done.

        :return: Modules in the synth
        """

        # Iterate over our modules:

        for synth in self._objs:

            # Get and return the modules:

            for mod in synth.traverse_link():

                # Yield the mod from the module:

                yield mod

        # Now, raise the StopIteration exception to complete:

        raise StopIteration()

    def __iter__(self):

        """
        Prepares the object for iteration.
        :return: This object
        """

        return self

    def __next__(self):

        """
        Gets values from each node and returns it.

        :return: Synthesised values from each node
        """

        if not self._objs:

            # Return None

            return None

        final = 0

        for obj in self._objs:

            # Get the next value:

            temp = next(obj)

            # Compute the value

            final = final + temp * 1 / len(self._objs)

        # Done, return the result:

        return amp_clamp(final)


class AudioBuffer(deque):

    """
    Holds a collection of audio signals of a pre-determined length.
    We inherit the python deque object, and add/overload methods when necessary.

    Allows for returning of all samples in the queue at once s a list,
    or allows for getting the start or end values of the buffer.

    We keep track of our inputs, and make sure they don't get out of sync.
    We also allow for grabbing certain values, without removing them.

    We also support convolution with other audio buffers!
    We will implement DFT as well as the FFT, by default utilising the DFT.

    Once a value(s) are removed from the buffer, we automatically fill it,
    so the AudioBuffer always have the latest information.

    Audio information(or any information for that matter) is appended to the right,
    meaning that as the index increases, the 'newer' the objects get.
    Items on the far left have been in the queue the longest,
    while items on the far right have been in the queue the shortest.

    :param size: Size of the AudioBuffer
    :type size: int
    :param data_source: Source of our audio data. if not specified, will fill buffer with zeroes.
    :type data_source: Any iterable
    :param no_fill: Determines if we should automatically fill the buffer
    :type no_fill: bool
    """

    def __init__(self, size, data_source=None, no_fill=False):

        super(AudioBuffer, self).__init__([], size)  # Initialise parent deque with fixed size

        self.size = size  # Size of the AudioBuffer
        self.source = iter(data_source) if data_source is not None else [0] * size  # Source of our data
        self.nums = 0  # Number of valid numbers in the AudioBuffer
        self.no_fill = no_fill  # Determines if we should automatically fill the buffer

        # Fill the buffer:

        self.fill_buffer()

    def fill_buffer(self, ignore_global=False):

        """
        Fills the buffer to a specified size using data from the source.

        :param ignore_global: Determines if we should ignore the global fill value and fill
        :type ignore_global: bool
        """

        if ignore_global or self.no_fill:

            # Do not fill this buffer!

            return

        # Iterate over the remaining values that we need

        for index in range(len(self), self.size):

            # Pull a value from the data source and add it to the left:

            self.append(next(self.source))

    def pop(self):

        """
        Removes an item from the right side of the queue, and returns it.
        Great for removing the newest values added.

        We call the parent function here, 'deque.pop()', but we also include a 'fill_buffer()'
        call to ensure the buffer is always full.

        :return: Value removed from right side of buffer
        :rtype: float, int
        """

        # Remove value and save it for later:

        val = super(AudioBuffer, self).pop()

        # Re-fill our buffer:

        self.fill_buffer()

        # Return our popped value:

        return val

    def popleft(self):

        """
        Removes an item from the left side of the queue, and returns it.
        Great for removing the oldest values added.

        Like 'pop()', we call the parent function and re-fill our buffer.

        :return: Value removed from left side of the buffer
        :rtype: float, int
        """

        # Remove value and save it for later:

        val = super(AudioBuffer, self).popleft()

        # Re-fill our buffer:

        self.fill_buffer()

        # Return our popped value:

        return val

    def clear(self):

        """
        Clears the AudioBuffer of all data,
        and re-fills it with new data from the generator.

        We use the parent 'clear()' method, and then the 'fill_buffer()' method to populate.
        """

        super(AudioBuffer, self).clear()

        self.fill_buffer()

    '''
    def __getitem__(self, item):

        """
        Gets an item from the AudioBuffer.

        Before we return the value, we make sure that the buffer is full.

        :param item: Index of value to get
        :type item: int
        :return: Item at given index
        :rtype: float
        """

        # Pass it along to the parent class:

        return super(AudioBuffer, self).__getitem__(item)
    '''

    def __delitem__(self, key):

        """
        Deletes an item from the AudioBuffer.

        After the item is deleted, we fill the buffer again.

        :param key: Index of item to remove
        :type key: int
        """

        # Delete the item from the parent deque

        super(AudioBuffer, self).__delitem__(key)

        # Populate our buffer:

        self.fill_buffer()


class AudioValue:

    """
    # TODO: Fix this description

    Container for audio values, such as frequency, gain, ect.

    This object is time aware, and will be able to change our value
    over time.

    We also support getting information from oscillators of any kind(LFO's might be the most relevant).
    """

    def __init__(self, value, min_val, max_val):

        self._value = value  # Value the object is set at
        self.initial_value = value  # Value the object was instantiated with
        self.min = min_val  # Minimum value the object can be
        self.max = max_val  # Maximum value object can be
        self._events = []  # List of events in this object

    @property
    def value(self):

        """
        Handles any relevant events and return the internal value.

        We only handle one event at a time. If the target time for the handled event
        is less than or equal to the current time, then we set the internal value to the target value.

        If the end time is negative, then we do not remove it.

        :return: Value
        """

        # Check if we have something to handle:

        if self._events:

            # Not empty, let's check if it's instantiated:

            if type(self._events[0]) == tuple:

                # Instantiate it:

                self._events[0] = self.start_event(self._events[0])

            # Let's see if the time is valid

            if get_time() >= self._events[0].time_end > 0.0:

                # Value is done, let's remove it:

                self._value = self._events.pop(0).value_target

            else:

                # Compute the value at this time

                self._value = self._events[0].comp()

        # Return our value:

        return self._value

    @value.setter
    def value(self, value):

        """
        Sets the internal value to the given value.

        Under the hood, we simply add a SetValue event at the current time,
        so we don't interfere with the current event.

        :param value: Value to set
        """

        self.add_event(SetValue, value, get_time())

    def start_event(self, params):

        """
        Starts an event instance by instantiating it,
        and giving it the necessary values.

        :param params: Event and parameters to instantiate it with
        :type params: tuple
        :return: Instantiated and started event
        :rtype: BaseEvent
        :raise: ValueError - If the target value is outside of the range.
        """

        # Instantiate and add the event

        return params[0](get_time(), params[2], self._value, params[1])

    def add_event(self, event, target, time_e):

        """
        Adds an event to the queue. This event is not started or instantiated,
        it is instead added as a tuple with it's intended parameters.
        It is started once the AudioValue object reaches it.

        :param event: Event to instantiate and start
        :type event: BaseEvent
        :param target: Target value to reach
        :type target: float
        :param time_e: End time
        :type time_e: float
        """

        self._events.append((event, target, time_e))

    def linear_ramp(self, target, endtime):

        """
        Creates and adds a LinearRamp event to the event queue.

        :param target: Target value
        :type target: float
        :param endtime: End time
        :type endtime: float
        """

        self.add_event(LinearRamp, target, endtime)

    def exponential_ramp(self, target, endtime):

        """
        Creates and adds a ExponentialRamp event to the event queue.

        :param target: Target value
        :type target: float
        :param endtime: End time
        :type endtime: float
        """

        self.add_event(ExponentialRamp, target, endtime)

    def bind_oscillator(self, osc, endtime=-1.0):

        """
        Binds an oscillator to this object.
        The default time is negative,
        as the user probably wants to use this oscillator indefinitely.

        The values pulled from the oscillator will be added to the starting value
        when the OscillatorEvent was instantiated.
        If you just want to get oscillator information without adding the output to a value,
        then set the AudioValue to 0 before binding the oscillator.

        :param osc: Oscillator to bind
        :type osc: BaseOscillator
        :param endtime: End time of the event
        :type endtime: float
        """

        self.add_event(OscillatorEvent, osc, endtime)


class BaseEvent(object):

    """
    Default event that all child events will inherit.

    We use 'slots' to optimise the size and speed of this object.
    """

    __slots__ = ['time_start', 'time_end', 'value_start', 'value_target']

    def __init__(self, time_s, time_e, value_s, value_t):

        self.time_start = time_s  # Starting time
        self.time_end = time_e  # Target time, when the operation will end
        self.value_start = value_s  # Starting value
        self.value_target = value_t  # Target value, end value

    def comp(self):

        """
        Runs the necessary computations on the value and returns it.

        This should be overridden in the child class!

        :return: New value
        """

        return self.value_start


class ExponentialRamp(BaseEvent):

    """
    Event that exponentially ramps the value to the target over a time period.
    """

    def comp(self):

        """
        Exponentially ramps the value to a target over a time period.

        We use this formula for our calculations:

        v(t) = V0 * (V1 / V0) ^ ((t - T0) - (T1 - T0))

        t = current time
        V0 = Initial value
        V1 = Target value
        T0 = Initial time
        T1 = End time

        :return: New value
        :rtype: float
        """

        # Do the calculation and return the value

        return self.value_start * (self.value_target / self.value_start) ** \
            ((get_time() - self.time_start) / (self.time_end - self.time_start))


class SetValue(BaseEvent):

    """
    Event that sets the value to the target at the given time.
    """

    def comp(self):

        """
        Sets the value to a target at the given time.

        We simply return the starting value, the AudioValue will
        automatically change the value once the target time is reached.

        :return: Initial value
        :rtype: float
        """

        return self.value_start


class LinearRamp(BaseEvent):

    """
    Event that linearly ramps the value to the target value.
    """

    def comp(self):

        """
        Linearly ramps the value to the target.

        We use the current formula:

        v(t) = V0 + (V1 - V0) ^ ((t - T0) / (T1 - T0))

        t = current time
        V0 = Initial value
        V1 = Target value
        T0 = Start time
        T1 = End time

        :return: New value
        :rtype: float
        """

        return self.value_start + (self.value_target - self.value_start) ** ((get_time() - self.time_start) /
                                                                             (self.time_end - self.time_start))


class OscillatorEvent(BaseEvent):

    """
    Event that continuously pulls values from the oscillator
    bound to this object.

    value_target is now a reference to the oscillator.
    We will continue to pull values from this oscillator until we are removed.
    """

    def comp(self):

        """
        Computes the next value in the oscillator and returns it.

        :return: New value
        :rtype: float
        """

        return self.value_start + self.value_target.calc_next()
