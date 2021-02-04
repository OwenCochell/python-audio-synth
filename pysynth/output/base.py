"""
PySynth Output Classes

We contain the PySynth OutputHandler,
and OutputControl.

Both classes handle and manage output from synth chains,
and send them to output modules attached to the Control class.

The Output class is the engine of this process,
pulling audio info and passing it along.
The OutputControl class manages the synth chains,
adding and removing them as necessary.

The design of the output class is heavily structured for sequencer use,
but you could script synth output using certain features located in OutputControl.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pysynth.utils import BaseModule, AudioCollection, get_time
from pysynth.output.modules import BaseOutput


class OutputControl(BaseModule):

    """
    Output Control - Controls adding and removing synths from the OutputHandler.

    We offer an easy to use interface for adding synths to the OutputHandler.

    We act as any other synth module,
    but when we are started, we add ourselves to the OutputHandler.
    This starts the other modules attached to us, and audio information is consumed by the OutputHandler.

    Because of this, we should be the LAST module in a synth chain.
    If not, then some information could be lost,
    and errors could occur when outputting information.

    We offer the ability to add ourselves to the OutputHandler until we are stopped
    (Great for sequencer use).
    We also offer ways to add ourselves for a certain period of time,
    like for a certain period of time, or a certain number of samples.

    Point is, if you iterate over us,
    or call our start method,
    then we will add ourselves to the OutputHandler until we are stopped.

    You shouldn't create this module directly.
    Instead, you should receive your very own OutputControl module
    when you bind a synth to the OutputHandler.
    """

    def __init__(self, out):

        super(OutputControl, self).__init__()

        self.out = out  # instance of the OutputHandler
        self.time_remove = 0  # Time to remove ourselves. If 0, then we don't keep track
        self.item_written = 0  # Number of items to write. If 0, then we don't keep track

    def start(self):

        """
        We simply prepare the object for iteration.

        '__iter__()' does all the dirty work!
        """

        return iter(self)

    def stop(self):

        """
        Remove ourselves from the OutputHandler.
        """

        # Remove ourselves from the OutputHandler:

        self.out._remove_synth(self)

        self.time_remove = 0
        self.item_written = 0

    def get_next(self):

        """
        We simply return values from the synth chain attached to us.

        We also do some checks to determine if we should stop.
        If we do stop, we will call our 'stop()' method,
        which will remove us from the OutputHandler.
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
        Registers ourselves with the OutputHandler until we reach time.

        :param time: Time to stop sending info to Output
        :type time: int
        """

        # Set the time limit:

        self.time_remove = time

        # Start ourselves:

        self.start()

    def write_num(self, num):

        """
        Registers ourselves to the OutputHandler for a number of iterations.

        :param num: Number of values to write
        :type num: int
        """

        # Set the max write limit:

        self.item_written = num

        # Start ourselves:

        self.start()

    def __iter__(self):

        """
        We do the same as BaseModule,
        except we add ourselves to the OutputHandler,
        and we don't call 'start()'!
        """

        # Reset the index value:

        self.index = 0

        # Prepare the sub-modules:

        self.input.start_modules()

        # Set our started value:

        self.started = True

        # Add ourselves to the OutputHandler:

        self.out._add_synth(self)

        # Return ourselves:

        return self


class OutputHandler:

    """
    OutputHandler - Handles and coordinates sending audio data to certain locations

    We handle to addition and subtraction of synths,
    allowing them to be added and removed on the fly.
    This is useful for systems such as the sequencer.

    We also allow for outputting info to multiple sources,
    so one could configure the output to send data to speakers
    and a wave file at the same time.

    When a synth is added, an 'OutputControl' is returned.
    This class allows for the control of the synth added,
    and allows for the developer to add the synth for a certain amount of time.
    It also integrates will with the sequencer.

    We are a 'reactive' output system,
    meaning we only sample the synths when the modules request us too.
    This allows for a balance of speed and accuracy,
    so we don't sample more frames then we should.
    This also means that we will only sample as quickly as our slowest module.
    Most of the time this is ideal,
    but if not then you should take care to only load modules you need!
    """

    def __init__(self, rate=44100):

        self._output = []  # Output modules to send information
        self._work = ThreadPoolExecutor()  # Thread pool executor to put our output modules in
        self._input = AudioCollection()  # Audio Collection to mix sound
        self.rate = rate  # Rate to output audio
        self.futures = []
        self.barrier = None  # Instance of the barrier class

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

        assert isinstance(out, BaseOutput), "Class must inherit BaseOutput!"

        # Add ourselves to the module:

        out.out = self

        # Check if we are running:

        if self.run:

            # Start and add the module:

            self._submit_module(out)

        # Otherwise, add it to the collection and start it later:

        self._output.append(out)

    def bind_synth(self, synth):

        """
        Binds a synth chain to the Output class.

        We return an OutputControl class to manage adding the synth to this class.
        This allows synths to be managed by a sequencer,
        or for them to be added for a specified amount of time.

        We will bind the synth chain to the OutputControl class,
        and return it.

        We also set the sampling rate of the synth chain to our own,
        so all synths can maintain a similar sampling rate.

        :param synth: Synth chain to add to output
        :type synth: BaseModule
        :return: OutputControl with the synth chain bound to it
        :rtype: OutputControl
        """

        # Create an output control:

        out = OutputControl(self)

        # Bind the synth to the output control:

        out.bind(synth)

        # Bind our sampling rate to the synth chain:

        synth._info.samp = self.rate

        # Return the output control:

        return out

    def start(self):

        """
        Starts the OutputHandler.

        This entails starting the output modules we have added,
        and creating a barrier to ensure all modules are synchronised in getting their values.

        We will start to consume audio information until we are stopped or paused.
        """

        # Set the run value:

        self.run = True

        # Create the barrier:

        self.barrier = threading.Barrier(len(self._output))

        # Start all the modules in our collection:

        for mod in self._output:

            # Start the module:

            self._submit_module(mod)

    def stop(self):

        """
        Stops the OutputHandler.

        This entails stopping all the output modules in our collection,
        and stopping the control thread that sends audio to the modules.

        Once stopped, the OutputHandler can be started again.
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
        Pauses the OutputHandler.

        We clear our pause event,
        which will cause the control thread to pause until it is unset.

        Audio information will not be consumed when paused!
        """

        # Clear the event:

        self._pause.clear()

    def resume(self):

        """
        Resumes the OutputHandler.

        We set out pause event,
        which will cause the control thread to continue.

        Audio information will be consumed when resumed!
        """

        # Set the event:

        self._pause.set()

    def gen_value(self):

        """
        Gets and sends the input from the synths to each output module.

        This allows audio information to be sampled only when it is necessary!
        Because modules block before getting information,
        all modules will be ready to receive information when this method is called.
        """

        # Iterate until we ge something valid:

        while True:

            # Pause if necessary:

            self._pause.wait()

            # Get some audio information:

            inp = next(self._input)

            if inp is None:

                continue

            # Iterate over our modules:

            for mod in self._output:

                # Add the input to the module:

                mod.add_input(inp)

            break

    def _add_synth(self, synth):

        """
        Adds a synth to the AudioCollection.

        This should really only be called by OutputControl,
        as they have the ability to fine-tune the operation.

        :param synth: Synth to be added to the Output class
        :type synth: BaseModule
        """

        # Add the synth to our collection:

        print("Added synth: {}".format(synth))

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

        # Add it to the collection:

        self._work.submit(mod.run)

    def _stop_module(self, mod):

        """
        Stops the given module.

        We call the 'stop' method, and set the running value to False.
        We also add None to the input queue.

        :param mod: Module to stop
        :type mod: BaseOutput
        """

        # Set the run value:

        mod.running = False

        # Call the stop method:

        mod.stop()

        # Add 'None' to the input queue:

        mod.add_input(None)
