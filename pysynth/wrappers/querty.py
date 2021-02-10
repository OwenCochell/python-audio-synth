"""
Sequencer wrapper for QWERTY keyboard input.

We allow the synth to be played via string infomration,
with sources being live keyboard input, text files, and more!

We utilise the current default control scheme:

q,a,w,s,e,d,r,f,t,g,y,h,u,j,i,k,o,l,p - All play musical notes, q being the lowest and p being the highest
z - Instrument 1
x - Instrument 2
c - Instrument 3
v - Instrument 4
, - Decrement the notes played by 1 step
. - Increment the notes played by 1 step

This allows for control of a quad-instrument sequencer,
allowing one to play using their keyboard.
"""

import platform
import os

from tkinter import Tk, Frame

from pysynth.seq import BaseInput, BaseDecoder, Sequencer, Note


class QWERTYKeyboard(BaseInput):

    """
    Gets and sends continuous keyboard input to the decoder.

    We utilise TKInter to get input from the keyboard.
    """

    def __init__(self):

        super(QWERTYKeyboard, self).__init__()

        self.root = None  # Root instance of TKinter
        self.frame = None  # Instance of TKinter frame

    def start(self):

        """
        We setup and configure the tkinter front end for getting keys.

        We also disable 'xset' on linux machines,
        which causes problems with how key inputs are configured.
        """

        # Check if we are on linux:

        if platform.system() == 'Linux':

            # Disable 'xset'

            os.system("xset r off")

        # Configure TKinter input window

        self.root = Tk()
        self.frame = Frame(self.root, width=100, height=100)
        self.frame.bind("<KeyPress>", self.decoder.key_pressed)
        self.frame.bind("<KeyRelease>", self.decoder.key_released)
        self.frame.pack()

    def stop(self):

        """
        We stop the TKinter instance,
        and enable 'xset' if we are on linux.
        """

        # Check if we are on linux:

        if platform.system() == 'Linux':

            # Disable 'xset'

            os.system("xset r on")

        # Disable the root instance:

        self.root.destroy()

    def run(self):

        """
        Actual run method for QWERTYKeyboard.

        We start the TKinter thread, and ensure that it is configured correctly.
        """

        self.frame.focus_set()
        self.root.mainloop()


class QWERTYDecoder(BaseDecoder):

    """
    Receives and interprets QWERTY strings.

    We require ALL inputs to be in string format!

    We are designed for the QWERTYKeyboard input module,
    but we can easily be used for others!
    """

    def __init__(self):

        super(QWERTYDecoder, self).__init__()

        # Selected instrument:

        self.instrument = 0  # Start with the 0th instrument

    def key_pressed(self, key):

        """
        Interprets the given key as being pressed down.

        We simply forward it to the decoder method for interpretation.

        This method is for QWERTYKeyboard callback support.

        :param key: Key that was pressed
        """

        # Send the key to the decoder method:

        self.decode(key.char, True)

    def key_released(self, key):

        """
        Interprets the given key as being released.

        We simply forward it to the decoder method for interpretation.

        This method is for QWERTYKeyboard callback support.

        :param key: Key that was released
        """

        # Send the key to the decoder method:

        self.decode(key.keysym, False)

    def decode(self, key, pressed):

        """
        We decode the given keys and convert them into instructions for the sequencer.

        We require a parameter to tell us if the key is being pressed or un-pressed.

        :param key: Key to be handled
        :type key str
        :param pressed: Determines if the key is being pressed or released
        :type pressed: bool
        """

        # Check if key is in notes:

        if key in self.seq.notes:

            # Calculate the note value given the note index, and offset:

            note = Note.from_num(self.seq.off - self.seq.notes.index(key))

            # Send the note to the sequencer, determining on press value:

            if pressed:

                # Toggle the note to be on:

                self.seq.start_note(note, name=self.instrument)

                return

            # Otherwise, lets stop the note:

            self.seq.stop_note(note, name=self.instrument)

            return

        if not pressed:

            # We only care about pressed keys, lets quit:

            return

        # Check if key in instruments:

        if key in self.seq.instrument_selection:

            # Get and set the index of the instrument:

            self.instrument = self.seq.instrument_selection.index(key)

            # Stop all playing notes:

            self.seq.stop_all()

            return

        # Check if we should increment the instrument:

        if key == self.seq.increment:

            # Increment the step by 1:

            self.seq.off += 1

            return

        # Check if we should decrement the instrument:

        if key == self.seq.decrement:

            # Decrement the step by 1:

            self.seq.off -= 1

            return

        # Otherwise, exit as the key is invalid

        return


class QWERTYWrapper(Sequencer):

    """
    QWERTY Wrapper for the PySynth sequencer!

    We configure 4 instruments, each with the names of 1, 2, 3, 4.

    We also auto-load the QWERTYDecoder module,
    and offer convince methods for auto-loading certain QWERTYInput modules.

    We keep track of the keymaps, and allow for the auto-generation of synths.
    """

    def __init__(self, middle_freq=440.0):

        super(QWERTYWrapper, self).__init__(middle_freq=middle_freq)

        self.notes = ['p', 'l', 'o', 'k', 'i', 'j', 'u', 'h',
                      'y', 'g', 't', 'f', 'r', 'd', 'e', 's', 'w', 'a', 'q']  # Key to map notes to, high to low
        self.instrument_selection = ['z', 'x', 'c', 'v']   # Keys that select the number of the instrument
        self.increment = '.'  # Value that increments our offset
        self.decrement = ','  # Value that decrements our offset

        self.off = 0  # Number of steps away from the middle note
        self.default_name = 0  # Default name if none is specified

        # Add the QWERTYDecoder to our sequencer:

        self.bind_decoder(QWERTYDecoder())

    def load_keyboard(self):

        """
        Loads the QWERTYKeyboard input module,
        used for getting live input from QWERTY keyboards.
        """

        # Load QWERTYKeyboard:

        self.bind_input(QWERTYKeyboard())
