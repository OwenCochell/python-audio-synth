"""
Envelopes for chaning the shape of the amplitude,
or loudness, of the sound.

We implement some common envelopes, such as an ADSR envelope,
which is one of the most common amplitude envelopes in use.
"""


from pysynth.envelope.base import BaseEnvelope
from pysynth.utils import AudioValue, get_time


class BaseAmpEnvelope(BaseEnvelope):

    """
    Base amplitude envelope - handles the changes in pitch.

    The change in pitch is done by dividing the incoming audio data by the 'amp_value'
    parameter, which is changed by the child envelope instance.
    This value defaults at '1', meaning that we will pass along the audio info at it's normal amplitude.

    We also allow for changing the max value of the sound, which is again, at 1.
    If this max value is changed, then a 1 and the 'amp_value' will result in the audio being scaled down to the max value.

    We utilise AudioValue and it's time event system to alter 'amp_value' over time.
    This allows ut to accurately change the amplitude over time,
    and get proper functionality for things like decay and and attack.

    To implement support for features like release,
    we will continue to keep ourselves added to the sequencer until we are done releasing.
    This allows for notes to have a fade out, even after they are told to shut down.
    The synth chain, if used with an OutputControl object,
    will continue to be sampled until we reach 0.
    We do this by blocking the 
    """

    def __init__(self):

        super().__init__()

        self.amp = AudioValue(0.00001, 0, 1)


class ADSREnvelope(BaseAmpEnvelope):

    """
    ADSR Envelope implementation.

    An ADSR envelope is a very common audio tool that shapes the waveform based upon some configurable parameters.

    These parameters are as follows:

        > Attack - The time it takes to reach the maximum value when the note is started
        > Decay - The time it takes to 'decay' down to the sustain level
        > Sustain - Level the amplitude will remain as until the note is released
        > Release - The time it will take for the amplitude to decay to silence after the note is stopped

    Using these parameters, one could shape a waveform to be many diffrent things.

    The start of this envelope is when this modules 'start()' function is called.
    We will continue to sustain until this module is asked to finish,
    which we will then start to decay down to 0.
    Once we reach zero, then this module will report that we are ready to complete,
    regardless of weather we have been asked to finish.
    When we are asked to finish up, then we will start the decay time time down to 0.

    We use AudioValue to keep track of the volume,
    and we will alter this audio value when we reach or events.
    This audio value changes its value using the default exponential ramping,
    although the user has the ability to change this method.
    """

    def __init__(self, attack, decay, sustain, release, max=1):

        super().__init__()

        self.attack = attack  # Attack time
        self.decay = decay  # Decay time
        self.sustain = sustain  # Sustain value
        self.release = release  # Release time
        self.max = max  # The maximum value this ADSR will attack to, MUST be less than 1!

    def start(self):

        """
        Starts the ADSR envelope.

        We just schedule the relevant time events for attack and decay.
        """

        # Clear any lingering events:

        self.amp.cancel_all_events()

        # Set the attack time:

        self.amp.linear_ramp(self.max, self.attack + get_time())

        # Set the decay time:

        self.amp.linear_ramp(self.sustain, self.decay + self.attack + get_time())

    def finish(self):

        """
        Cancles all events currently occuring and ramps down to the final value.
        """

        print("Finishing the envelope")

        # Cancel all events:

        self.amp.cancel_all_events()

        # Schedule an event to ramp down to zero:

        self.amp.linear_ramp(0, self.release + get_time())

    def get_next(self):
        
        """
        Multiplies the incoming value by the amp value
        and sends it along.

        If the amp is ever zero, then we will report as ready to finish.
        """

        # Get a value from the AudioValue:

        val = self.amp.value

        #print(val)

        # Determine if we should finish:

        if val == 0:

            # We are done, let's finish:

            print("Reporting as finished")

            self.done()

        # Return the input multiplied by the envelope:

        return self.get_input() * val
