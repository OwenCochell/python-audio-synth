"""
PySynth builtin output modules.

We contain the built in output modules for PySynth.

These modules are to be used with the OutputHandler,
as it will handle the process of getting, mixing, and sending
the audio information to each module.

We offer some useful output modules:
(An asterisk denotes that a dependency is required)

    - PyAudioModule - Outputs audio to speakers using PyAudio *
    - WaveModule - Outputs audio to a wave file
    - PrintModule - Prints audio data to a terminal
    - NullModule - Does nothing with the given audio information

Here are some audio modules I would like to see later:

    - NetModule - Server/client, used for sending audio data over a network
    - FFMPEGModule - Outputting audio to different audio types(mp3, flac, ogg) *
    - Other - Wrappers for other output types(simpleaudio, alsa) *
"""


import queue
import wave
import pathlib

from pysynth.output.convert import BaseConverter, FloatToByte, NullConvert, IntToByte


class BaseOutput(object):

    """
    BaseOutput - Class all child output modules must inherit!

    An 'Output Module' is a component that adds extra functionality to the 'OutputHandler' class.

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
        self.convert = NullConvert()  # Converter instance
        self.running = False  # Value determining if we are running
        self.out = None  # Reference to master OutputHandler class
        self.special = False

    def add_converter(self, conv):

        """
        Adds the given converter to the output module.

        The converter MUST inherit BaseConverter,
        or an exception will be raised.

        :param conv: Converter to add
        :type conv: BaseConverter
        """

        # Check if the converter inherits BaseConverter

        assert isinstance(conv, BaseConverter), "Converter MUST inherit BaseConverter!"

        # Otherwise, add it to this module:

        self.convert = conv

    def get_input(self, timeout=None, raw=False):

        """
        Gets a value from the queue and sends it through the converter.
        We support the timeout feature, which is the amount of time to stop our operation..

        Due to threading and our method of synchronization,
        we will ALWAYS block.

        You can optionally disable conversion by using the 'raw' parameter.

        When we are stopped by the Output class,
        'None' is added to our queue.
        If you encounter 'None', then you should exit and finish up any work you may be doing.
        The 'stop()' method will be called shortly after,
        so you can put stop code in there.

        :param timeout: Timeout value in seconds. Ignored if None, or if we are not blocking
        :type timeout: int
        :param raw: Value determining if we should operate in raw mode,
            where we don't send info to the converter before returning it.
        :type raw: bool
        """

        if self.special:

            # Generate a new frame

            inp = self.out.gen_value()

        else:

            # Get input from the queue:

            inp = self.queue.get(timeout=timeout)

        # We are done processing!

        if inp is None:

            # We have None! Return

            return None

        # Check if we should convert:

        if not raw:

            # Convert the input:

            inp = self.convert.convert(inp)

        # Return the input:

        return inp

    def get_inputs(self, num, timeout=None, raw=False):

        """
        Gets a number of inputs from the input queue,
        and returns them in a tuple.

        Under the hood we call 'get_input()' a number of times,
        and return all the inputs as a tuple.

        Again, when we are stopped, 'None' is added to our audio queue.
        If we encounter 'None', then we will simply return 'None'/

        :param num: Number of samples to retrieve
        :type num: int
        :param timeout: Timeout value in seconds. Ignored if we are blocking, or None
        :type timeout: int
        :param raw: Determines id we should send input through the converter
        :type raw: bool
        :return: Tuple containing the samples
        :rtype: tuple
        """

        final = []

        # get a number of inputs:

        for i in range(0, num):

            # Get input and add it to the final

            inp = self.get_input(timeout=timeout, raw=raw)

            if inp is None:

                # Just return None

                return None

            # Add input to list:

            final.append(inp)

        # Return the inputs

        return final

    def get_added_inputs(self, num, timeout=None, raw=False):

        """
        Gets a number of inputs from the input queue,
        and adds them together into one value.

        We use standard python arithmetic,
        so you could configure a class to do something special when added.

        Under the hood, we call 'get_input()' a specified amount of times,
        and add all the inputs together.

        If your converter returns bytes,
        then this is a great way to get a combined bytes object!

        Again, when we are stooped, 'None' is added to our audio queue.
        If we encounter 'None', then we will simply return None.

        :param num: Number of samples to retrieve
        :type num: int
        :param timeout: Timeout value in seconds. Ignored if we are not blocking, or None
        :type timeout: int
        :param raw: Determines if we should send the input though the converter
        :type raw: bool
        :return: Added values
        """

        # Iterate a specified number of times:

        final = self.get_input(timeout=timeout, raw=raw)

        for i in range(0, num-1):

            # Get input and add it to final:

            inp = self.get_input(timeout=timeout, raw=raw)

            if inp is None:

                # Return None:

                return None

            # Add input to list:

            final = final + inp

        # Convert the tuple and return:

        return final

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


class NullModule(BaseOutput):

    """
    NullModule - Sends audio information to nowhere!

    Great for situations where you want the control of the OutputHandler,
    but you don't want the audio to actually want the audio to go anywhere.
    """

    def run(self):

        """
        Just like the name,
        we simply do nothing with our audio!
        """

        while self.running:

            # Get an item, and do nothing!

            inp = self.get_input()


class PrintModule(BaseOutput):

    """
    PrintModule - prints audio information to the screen!

    By default, we print the floats to the terminal.
    However, if you want to see the information in a different format,
    then you can add a converter to this module.
    """

    def run(self):

        """
        We print the information from the input to the terminal.

        We do this using the 'print' command.
        """

        while self.running:

            # Get and print info:

            print(self.get_input())


class WaveModule(BaseOutput):

    """
    WaveModule - We save audio data to a wave file.

    We use the python 'wave' class,
    so this module requires no external dependencies!

    We require a path to a file,
    and can optionally be provided with the number of frames per buffer,
    which can alter performance considerably.

    We will configure the wave file for our uses,
    setting the sample width, frame rate, and the number of channels.
    This is configured when this module is started,
    and the file will be properly closed when this module is stopped.

    :param path: Path to the wave file to write to
    :type path: str
    :param frames_per_buffer: Frames to write per call
    :type frames_per_buffer: int
    """

    def __init__(self, path, frames_per_buffer=1024):

        super(WaveModule, self).__init__()

        self.path = path  # Path to wave file to write
        self.frames_per_buffer = frames_per_buffer  # Number of frames per write
        self.path = str(pathlib.Path(path).resolve())  # Path to the wave file
        self.file = None  # Instance of wave file

        # Add a float to byte converter:

        #self.add_converter(FloatToByte())
        self.add_converter(IntToByte())

    def start(self):

        """
        Starts the WaveModule.

        Specifically, we create a wave file stream,
        and configure it to our specifications,
        which is 1 channel, sample width of 4, and framerate to whatever we are set to.
        """

        # Create the stream:

        self.file = wave.open(self.path, mode='wb')

        # Set the number of channels:

        self.file.setnchannels(1)

        # Set the sample width:

        self.file.setsampwidth(2)

        # Set frame rate:

        self.file.setframerate(self.out.rate)

    def stop(self):

        """
        Stops the WaveModule.

        We stop the wave stream,
        to ensure all information has been written.
        """

        # Close the wave file

        self.file.close()

    def run(self):

        """
        Main run method for WaveModule.

        We get a certain number of frames, dependant on our frames per buffer,
        and then output them to the wave file.
        """

        while self.running:

            # Get a certain number of frames:

            frames = self.get_added_inputs(self.frames_per_buffer)

            # Output them to the wave file:

            self.file.writeframes(frames)


class PyAudioModule(BaseOutput):

    """
    PyAudio Module - We send info to speakers live via PyAudio.

    We will automatically configure PyAudio for our operation,
    such as extracting the sample rate from the input synths,
    configures the PyAudio stream for output,
    and select the correct audio format.

    The user can specify which device they want to use.
    We will offer methods for getting and selecting devices.
    We also allow for the customization of the number of frames per write,

    On the creation of this module,
    we attempt to import the PyAudio library.
    If this import fails, then we will raise an exception,
    and will refuse to instantiate.

    :param device: Device ID to use for output
    :type device: int
    :param frames_per_buffer: Number of frames to write per buffer
    :type frames_per_buffer: int
    """

    def __init__(self, device=None, frames_per_buffer=1024):

        super(PyAudioModule, self).__init__()

        # Attempt to load PyAudio:

        try:

            import pyaudio

        except:

            # Could not import PyAudio! Raise an exception of our own

            raise ModuleNotFoundError("We require PyAudio to be installed!")

        self.device = device  # Device to output to
        self.frames_per_buffer = frames_per_buffer  # Number of frames per write
        #self.format = pyaudio.paInt16  # Format to output audio
        self.format = pyaudio.paFloat32

        self.pyaudio = pyaudio.PyAudio()  # PyAudio instance
        self.stream = None  # Instance of our stream. Created upon start

        # Lets add a FloatToByte converter:

        self.add_converter(FloatToByte())
        #self.add_converter(IntToByte())

    def start(self):

        """
        We configure and set up the audio stream here.
        """

        # Set up the stream:

        self.stream = self.pyaudio.open(format=self.format,
                                        channels=1,
                                        output=True,
                                        rate=self.out.rate,
                                        #frames_per_buffer=self.frames_per_buffer,
                                        output_device_index=self.device)

    def stop(self):

        """
        We stop the PyAudio stream.
        """

        self.stream.stop_stream()

    def run(self):

        """
        Main run method,
        we grab a number of frames and write them.
        """

        print("We are running!")

        while self.running:

            # Get a certain number of frames:

            frames = self.get_added_inputs(self.frames_per_buffer)

            # Send them to PyAudio

            self.stream.write(frames)

            #print("Time py: {}".format(get_time()-start))
