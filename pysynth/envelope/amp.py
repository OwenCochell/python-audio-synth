"""
Envelopes for chaning the shape of the amplitude,
or loudness, of the sound.

We implement some common envelopes, such as an ADSR envelope,
which is one of the most common amplitude envelopes in use.
"""


from pysynth.envelope.base import BaseEnvelope


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