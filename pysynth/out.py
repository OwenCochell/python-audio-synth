"""
PySynth output models.

These modules handles sending the final audio data to a location,
weather that be an output device, file, terminal, or anything else!

To work with outputs, you must create an 'Output' module,
which will handle the different methods of output,
and allow you to output to multiple if you desire.

To add an output node, simply add a class inheriting 'BaseOutput',
and program in your functionality.

'Output' will handle to loading of these modules,
and will send relevant information to each one as necessary.

When you add a synth chain to the output module,
then you will receive an 'OutputInvoker',
which will automatically configure 'Output'
to pull audio information for a set amount of time.
This value can be invoked yourself,
or it can be passed to a sequencer for extra handling.
"""


import queue
import struct
import threading

from concurrent.futures import ThreadPoolExecutor

from pysynth.utils import BaseModule, AudioCollection, get_time


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

        self.char = 'f' + '>' if big else '<'  # Prefix char, working with floats and specified byte order

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

        return struct.pack(self.char, inp)


class BaseOutput(object):

    """
    BaseOutput - Class all child output modules must inherit!

    An 'Output Module' is a component that adds extra functionality to the 'Output' class.

    For example, if you wanted to write audio data to a wave file,
    then you would have to write and add an output module that can do so to the 'Output' class.

    We define some useful functionality here,
    such as defining the Output Module API,
    as well as getting a collection of values.

    The Output class will do the dirty work of invoking these modules,
    and passing audio information to us.
    We only have to worry about sending the audio to a location!

    Each audio module will be put in it's own thread,
    to prevent locking and allow them to operate efficiently.

    We accept signed floats as audio data,
    so be sure to configure your output accordingly!

    We also allow for the registration of a converter,
    which will automatically convert the audio information into something we can understand.
    """

    def __init__(self):

        self.queue = queue.Queue()  # Queue for getting audio information
        self.convert = None  # Converter instance
        self.running = False  # Value determining if we are running

    def add_converter(self, conv):

        """
        Adds the given converter to the output module.

        The converter MUST inherit BaseConverter,
        or an exception will be raised.

        :param conv: Converter to add
        :type conv: BaseConverter
        """

        # Check if the converter inherits BaseConverter

        assert issubclass(conv, BaseConverter), "Converter MUST inherit BaseConverter!"

        # Otherwise, add it to this module:

        self.convert = conv

    def get_input(self, block=True, timeout=None, raw=False):

        """
        Gets a value from the queue and sends it trough the converter, if it exists.
        We support common queue parameters, such as timeout and block.

        You can optionally disable conversion by using the 'raw' parameter.

        When we are stopped by the Output class,
        'None' is added to our queue.
        If you encounter 'None', then you should exit and finish up any work you may be doing.
        The 'stop()' method will be called shortly after,
        so you can put stop code in there.

        :param block: Determines is we should block - True for yes, False for no
        :type block: bool
        :param timeout: Timeout value in seconds. Ignored if None, or if we are not blocking
        :type timeout: int
        :param raw: Value determining if we should operate in raw mode,
            where we don't send info to the converter before returning it.
        :type raw: bool
        """

        # Get input from the queue:

        inp = self.queue.get(block=block, timeout=timeout)

        if inp is None:

            # We have None! Return

            return None

        # Check if we should convert:

        if not raw and self.convert is not None:

            # Convert the input:

            inp = self.convert.convert(inp)

        # Return the input:

        return inp

    def get_inputs(self, num, block=True, timeout=None, raw=False):

        """
        Gets a number of inputs from the input queue.

        Under the hood, we call 'get_input()' a specified amount of times,
        and return all the inputs as a tuple.

        Again, when we are stooped, 'None' is added to our audio queue.
        If we encounter 'None', then we will simply return None.

        :param num: Number of samples to retrieve
        :type num: int
        :param block: Determines if we should block
        :type block: bool
        :param timeout: Timeout value in seconds. Ignored if we are not blocking, or None
        :type timeout: int
        :param raw: Determines if we should send the input though the converter
        :type raw: bool
        :return: Tuple of inputs at the specified length
        :rtype: tuple
        """

        # Iterate a specified number of times:

        final = []

        for i in range(0, num):

            # Get input and add it to final:

            inp = self.get_input(block=block, timeout=timeout, raw=raw)

            if inp is None:

                # Return None:

                return None

            # Add input to list:

            final.append(inp)

        # Convert the tuple and return:

        return tuple(final)

    def add_input(self, inp):

        """
        Adds the given input to the audio queue.

        This probably should only be called by 'Output',
        but if developers has a use for adding values,
        and can properly handle any issues that may arise,
        then it should be okay to do so.

        :param inp: Input to add to the queue
        :type inp: float
        """

        # Add the value to the queue:

        self.queue.put(inp)

    def start(self):

        """
        This function is called when the output module is started.

        The output module is started when it is added to the thread executor pool.
        Feel free to put any setup code you want here.
        """

        pass

    def stop(self):

        """
        This function is called when the output module is stopped.

        The output module is stopped once the Output class is stopping,
        or if we are removed from the Output class during run time.

        You should make a point to stop all processes as quickly as possible,
        as you could be interrupting other operations.
        """

        pass

    def run(self):

        """
        This function will be invoked by the Output class.

        This function should be dedicated to outputting information to a certain location.
        'run' will be given it's own thread to work in, so if operations are blocking,
        then it will not interfere with other operations.

        The child class should overload this function,
        and define their won functionality here.
        """

        raise NotImplementedError("Child classes should implement this function!")


class OutputControl(BaseModule):

    """
    Output Control - Controls adding and removing synths from the Output class

    We offer an easy to use interface for adding synths to the output class.

    We act as any other synth module,
    but when we are started, we add ourselves to the Output class.
    This starts the other modules attached to us, and audio information is consumed by the Output class.

    Because of this, we should be the LAST module in a synth chain.
    If not, then some information could be lost.

    We offer the ability to add ourselves to the Output class until we are stopped
    (Great for sequencer use).
    and we also offer ways to add ourselves for a certain period of time,
    like for a certain period of time, or a certain number of samples.

    Point is, if you iterate over us,
    or call our start method,
    then we will add ourselves to the Output class until we are stopped.

    You shouldn't create this module directly.
    Instead, you should receive your very own OutputControl module
    when you add a synth to the Output class.
    """

    def __init__(self, out):

        super(OutputControl, self).__init__()

        self.out = out  # instance of the Output class
        self.time_remove = 0  # Time to remove ourselves. If 0, then we don't keep track
        self.item_written = 0  # Number of items to write. If 0, then we don't keep track

    def start(self):

        """
        Adds ourselves to the Output class.

        If no use cases are set, then we will be added until we are stopped!
        """

        # Add ourselves to the Output class:

        self.out._add_synth(self)

    def stop(self):

        """
        Remove ourselves from the Output class.
        """

        # Remove ourselves from the Output class:

        self.out._remove_synth(self)

        self.time_remove = 0
        self.item_written = 0

    def get_next(self):

        """
        We simply return values from the synth chain attached to us.

        We also do some checks to determine if we should stop.
        If we do stop, we will call our 'stop()' method,
        which will remove us from the Output collection.
        """

        # Lets see if we should remove ourselves:

        if self.time_remove != 0 and self.time_remove > get_time():

            # >Time< to remove ourselves! Our >Time< is up!

            self.stop()

            return

        if self.item_written != 0 and self.item_written > self.index:

            # We have written everything we can, lets remove:

            self.stop()

            return

        # Otherwise, lets just return!

        return self.get_input()

    def write_time(self, time):

        """
        Registers ourselves with the Output class until we reach time.

        :param time: Time to stop sending info to Output
        :type time: int
        """

        # Set the time limit:

        self.time_remove = time

        # Start ourselves:

        self.start()

    def write_num(self, num):

        """
        Write a number of values to the Output and the removes ourselves.

        :param num: Number of values to write
        :type num: int
        """

        # Set the max write limit:

        self.item_written = num

        # Start ourselves:

        self.start()


class Output:

    """
    Output module - Handles and coordinates sending audio data to certain locations

    We handle to addition and subtraction of synths,
    allowing them to be added and removed on the fly.
    This is useful for systems such as the sequencer.

    We also allow for outputting info to multiple sources,
    so once could configure the output to send data to speakers
    and a wave file at the same time.

    When a synth is added, an 'OutputControl' is returned.
    This class allows for the control of the synth added,
    and allows for the developer to add the synth for a certain amount of time.
    """

    def __init__(self):

        self._output = []  # Output modules to send information
        self._work = ThreadPoolExecutor()  # Thread pool executor to put our output modules in
        self._input = AudioCollection()  # Audio Collection to mix sound
        self._thread = None  # Instance of control thread - sends input to modules

        self.run = False  # Value determining if we are running
        self._pause = threading.Event()  # Event object determining if we are paused

        self._pause.set()

    def add_output(self, out):

        """
        Adds an output module to this class.

        We ensure it inherits BaseModule, and then we add it.

        If we are currently running,
        then we start it and add it to the thread pool executor.

        If we are not started, then we will wait to add the modules until we have been.

        :param out: Output modules to add
        :type out: BaseOutput
        """

        # Ensure object is output module:

        assert issubclass(out, BaseOutput), "Class must inherit BaseOutput!"

        # Check if we are running:

        if self._run:

            # Start and add the module:

            self._submit_module(out)

        # Otherwise, add it to the collection and start it later:

        self._output.append(out)

    def bind_synth(self, synth):

        """
        Binds a synth chain to the Output class.

        We return a OutputControl class to manage adding the synth to this class.
        This allows synths to be managed by a sequencer,
        or for them to be added for a specified amount of time.

        We will bind the synth chain to the OutputControl class,
        and return it.

        :param synth: Synth chain to add to output
        :type synth: BaseModule
        :return: OutputControl with the synth chain bound to it
        :rtype: OutputControl
        """

        # Create an output control:

        out = OutputControl(self)

        # Bind the synth to the output control:

        out.bind(synth)

        # Return the output control:

        return out

    def start(self):

        """
        Starts the Output class.

        This entails starting the output modules we have added,
        and spinning up a control thread that will send audio values to the output modules.

        We will start to consume audio information until we are stopped or paused.
        """

        # Set the run value:

        self.run = True

        # Start all the modules in our collection:

        for mod in self._output:

            # Start the module:

            self._submit_module(mod)

        # Start the control thread:

        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self):

        """
        Stops the output class.

        This entails stopping all the output modules in our collection,
        and stopping the control thread that sends audio to the modules.

        Once stopped, the Output can be started again.
        However, some modules can't be restarted.
        So be prepared for errors, or certain output modules not working.
        """

        # Set the run value:

        self.run = False

        # Stop all output modules:

        for mod in self._output:

            # Stop the module:

            self._stop_module(mod)

    def pause(self):

        """
        Pauses the Output class.

        We clear our pause event,
        which will cause the control thread to pause until it is unset.

        Audio information will not be consumed when paused!
        """

        # Clear the event:

        self._pause.clear()

    def resume(self):

        """
        Resumes the Output class.

        We set out pause event,
        which will cause the control thread to continue.

        Audio information will be consumed when resumed!
        """

        # Set the event:

        self._pause.set()

    def _run(self):

        """
        Control method - We send information to output modules.

        This method will reside in a thread, so it should not be called directly!

        We will continuously send audio information to output modules,
        unless we are paused or stopped.
        """

        while self.run:

            # Pause if necessary:

            self._pause.wait()

            # Get some audio information:

            inp = next(self._input)

            # Iterate over our modules:

            for mod in self._output:

                # Add the input to the module:

                mod.add_input(inp)

    def _add_synth(self, synth):

        """
        Adds a synth to the AudioCollection.

        This should really only be called by OutputControl,
        as they have the ability to fine-tune the operation.

        :param synth: Synth to be added to the Output class
        :type synth: BaseModule
        """

        # Add the synth to our collection:

        self._input.add_module(synth)

    def _remove_synth(self, synth):

        """
        Removes a synth from the AudioCollection.

        This should really only be called by OutputControl,
        as they have the ability to fine-tune the operation.

        :param synth: Synth to be removed from the Output class
        :type synth: BaseModule
        """

        # Remove the synth from our collection:

        self._input.remove_module(synth)

    def _submit_module(self, mod):

        """
        We do the dirty work of starting and submitting a module to the ThreadPoolExecutor.

        We assume the module inherits BaseOutput,
        and that it has been added to the module collection.

        If you wish to add a module, you should really use 'add_output'.

        :param mod: Output module to start
        :type mod: BaseOutput
        """

        # Set the run value:

        mod.running = True

        # Start the module:

        mod.start()

        # Add the module to the thread pool:

        self._work.submit(mod.run)

    def _stop_module(self, mod):

        """
        Stops a certain module.

        We set the run value to False,
        and call the stop method of the module.

        We also add 'None' to the queue of each object,
        to signify that we wish for the module to stop.

        :param mod: Output module to stop
        :type mod: BaseOutput
        """

        # Set the run value:

        mod.running = False

        # Add 'None' to the module input:

        mod.add_input(None)

        # Run the stop method:

        mod.stop()
