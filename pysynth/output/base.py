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
from pysynth.osc import ZeroOscillator


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
    We also offer an internal scheduling system that allows users and sequencers to specify 
    when we should add and remove ourselves from the OutputHandler.
    This allows us to control ourselves, and makes audio scheduling easy!

    Point is, if you iterate over us,
    or call our start method,
    then we will add ourselves to the OutputHandler until we are stopped.

    You shouldn't create this module directly.
    Instead, you should receive your very own OutputControl module
    when you bind a synth to the OutputHandler.
    """

    OUT = []  # Reference to OutputHandler

    def __init__(self):

        super(OutputControl, self).__init__()

        self.item_written = 0  # Number of items to write. If 0, then we don't keep track

        self.time_events = []  # List of time events

        self.started = False  # Value determining if we are added to the OutputHandler
        self.finishing = False  # Value determining if we are finishing
        self.wait = False  # Value determining if we are started, but are wating on a time event


    def start(self):

        """
        We simply prepare the object for iteration.

        '__iter__()' does all the dirty work!
        """

        # Check if we are not started

        if not self.started:

            print("Starting...")

            return iter(self)

        # Check if we are finishing:

        if self.finishing:

            # We are just finishing, restart the modules:

            print("Resetting modules...")

            self.input.start_modules()

            self.finishing = False

            self.info.done = 0

    def stop(self):

        """
        Stop method - A polite way of stopping this control instance!

        This function prepares this instance to stop,
        but does not actually do so until all modules are ready to stop.

        This allows features like fade outs, echos, and amplitude envelopes
        to continue to operate even after this instance is asked to stop.

        Once all modules have reported that they are ready to stop,
        and there are no other time events to process,
        then we will automatically call 'abs_stop()' which
        will complete the process of removing us from the OutputHandler. 
        """

        # Tell the chain that we are done:

        self.done()

        # Have the modules finish up:

        self.input.finish_modules()

        # Update our status:

        self.finishing = True

    def abs_stop(self):

        """
        Absolute stop - Completely stops this control instance!

        When called, we remove ourselves from the OutputHandler,
        reset our state, and stop the synth chain.

        This function ignores time events and finish status!
        Thats great for immediately stopping this synth chain,
        but not that great if you are expecting modules to finish up,
        and it might interfear with the sequencer, 
        and it's ability to properly manage the notes attached to this object.

        This function is called by us automatically,
        when the synth chain is finished,
        and we don't have any more time events.
        So worry not! You do not have to call this function manually,
        as we will automatically do so.

        This removes us from the OutputHandler,
        meaning that this chain will NOT be in an event loop.
        This means that time events and the modules will NOT be sampled
        or worked with until our 'start()' method is called by an external entity.

        Point is - It is probably in your best intrest to NOT call this function!
        We should be able to automatically handle the process of stopping ourselves.
        It is better to politely stop this module chain by calling 'stop()',
        so we can ensure that the modules are completely ready to stop. 
        """

        if self.info.running:

            # Remove ourselves from the OutputHandler:

            print("Removing ourselves from output hand")

            self.OUT[0]._remove_synth(self)

            # Reset our values:

            self.item_written = 0
            self.time_events.clear()

            # Stop the chain:

            self.input.stop_modules()

            # Update our status:

            self.started = False
            self.finishing = False

    def join(self):

        """
        Blocks until the OutputControl is removed from OutputHandler.
        """

        while self.started:

            continue

        return

    def get_next(self):

        """
        We simply return values from the synth chain attached to us.

        We also do some checks to determine if we should stop.
        If we do stop, we will call our 'stop()' method,
        which will remove us from the OutputHandler.
        """

        time_now = get_time()

        # Lets see if we are ready to start:

        if self.time_events and self.time_events[0][0] > time_now:

            # We are not ready to start, lets wait:

            return None

        if self.time_events and self.time_events[0][0] < time_now:

            # We are ready, lets start the synth chain:

            self.wait = False

            self.start()

        # Lets see if we are ready to stop:

        if self.time_events and self.time_events[0][1] < time_now and self.time_events[0][0] >= 0:

            print("Ready to stop")

            # We are done! Lets remove the time event:

            self.time_events.pop(0)

            # Prepare the synth chain for stopping:

            self.stop()

        # Lets see if we have written enough:

        if self.item_written != 0 and self.item_written > self.index:

            # We have written everything we can, lets prepare for stopping:

            self.stop()

        # State of the object has been changed, let's see if we are ready to stop:

        if not self.info.running or self.info.done == self.info.connected:

            # Chain has stopped, or all modules ready to stop:

            print("Removing synth chain...")

            self._event_done()

            self.info.done = 0

            return None

        # Otherwise, lets just return!

        return self.get_input()

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

    def time_event(self, start, stop):

        """
        Schedules a time event for this OutputControl instance.

        Time events allows us to add and remove ourselves during certain intervals.

        'start' determines the time to start this object.
        We will not return audio values until the value from 'get_time()'
        is less than or equal to this value.
        If you want this object to start immediately, then supply 0 for this value.

        'stop' determines the time to stop this object.
        We will remove ourselves from the OutputHandler when the value from 'get_time()'
        is less than or equal to this value.
        If you want this object to continue indefinitely, then supply -1 for this value.

        You can schedule multiple time events, and we will handle them as necessary.
        Once a time event has been completed,
        (Added and removed ourselves during the given interval),
        then we will remove the time event.
        If there are no other time events, then we will remove ourselves from the OutputHandler. 
        """

        # Add the time event to this object:

        self.time_events.append([start, stop])

    def _event_done(self):

        """
        Method called when we have processed a time event
        (Passed start and stop times).

        We will determine if we should remove ourselves completely from OutputHandler.
        If these are more events in the 'time_events' list,
        then we will remain added, as we will eventually start ourselves.
        """

        if self.time_events:

            # We are good to continue

            return

        # No events scheduled, lets exit:

        self.abs_stop()

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

        self.OUT[0]._add_synth(self)

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
        self.thread = []

        self.run = False  # Value determining if we are running
        self._pause = threading.Event()  # Event object determining if we are paused

        self._pause.set()

        self._input.add_module(ZeroOscillator())

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

        out = OutputControl()
        out.OUT.append(self)

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
        and creating a barrier to ensure all modules are synchronized in getting their values.

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

                if mod.special:

                    # Ignore and continue:

                    continue

                mod.add_input(inp)

            return inp

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

        #self._work.submit(mod.run)

        thread = threading.Thread(target=mod.run)
        thread.daemon = True
        thread.start()
        self.thread.append(thread)

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
