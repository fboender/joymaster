#!/usr/bin/python
#
# Copyright 2005, Ferry Boender <f DOT boender AT electricmonk DOT nl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

"""
XEventSimulator provides a way of inserting simulated events into a X Window.
"""

import Xlib.display
import Xlib.X
import Xlib.XK
import time

class XEventSimulator:
	"""
	XEventSimulator provides a way of inserting (key) event sequences into an X
	Window.  A single event sequence can consist out of multiple X events (i.e.
	multiple keypresses). Also provided are various convenience helper methods
	for converting strings to event(s) sequences. 

	Example:

	display = Xlib.display.Display()

	xevsim = XEventSimulator(display)
	xevsim.setWindow(xevsim.getCurrentFocussedWindow())

	xev = xevsim.stringToXEvent("control+shift+Up")
	xevsim.addEventSequence("xev_1", [xev_1])

	xevsim.sendEventSequence("xev_1")
	"""

	def __init__(self, display, window = None):

		self.__window = None
		self.__event_seqs = {}
		self.__setDisplay(display)

		if window:
			self.setWindow(window)

	def __setDisplay(self, display):
		"""
		Set the display to work with. Calling this function invalidates any
		currently set self.__window and, in effect, any events.
		"""

		if not isinstance(display, Xlib.display.Display):
			raise TypeError("Expected an Xlib.display.Display instance")
		
		self.__display = display
		
	def setWindow(self, window):
		"""
		Set the window (of XAtom Window type) which will receive the events.
		Window must be gotten from the same display as given on object
		instantiation.
		"""
		
		if not isinstance(window, Xlib.xobject.drawable.Window):
			raise TypeError("Expected an Xlib.xobject.drawable.Window instance")

		self.__window = window

	def getDisplay(self):
		"""
		Return the used display.
		"""

		return(self.__display)

	def getWindow(self):
		"""
		Return the window (of type XAtom Window) which will receive the events.
		"""

		return(self.__window)

	def addEventSequence(self, name, event_seq):
		"""
		Add an name->event sequence which can be sent to the window.

		name is a string which uniquely identifies the sequence. 
		event_seq is an list of Xlib.protocol.event.* instances.
		"""

		if not isinstance(event_seq, list):
			raise TypeError("Expected a list of Xlib.protocol.event.* instances")

		# Check events validity
		for event in event_seq:
			if not isinstance(event, Xlib.protocol.event.KeyPress):
				raise TypeError("Expected a list of Xlib.protocol.event.* instances")
				
		self.__event_seqs[name] = event_seq

		return(True)

	def delEventSequence(self, name):
		"""
		Remove an name->event sequence.
		"""
		
		self.__event_seqs.pop(name)
		
	def delEventSequences(self):
		"""
		Remove all name->event sequences.
		"""

		self.__event_seqs = {}

	def sendEventSequence(self, name):
		"""
		Send the event identified by 'name' to the window.
		"""

		if not self.__window:
			raise AttributeError("No window has been set.")

		event_seq = self.__event_seqs[name]

		for event in event_seq:
			self.__window.send_event(event, propagate = True)

		self.__display.sync()

	def getCurrentFocussedWindow(self):
		"""
		Convenience method which returns the currently focussed window on the
		display. 

		Returns None if no currently focussed window could be found. Otherwise,
		returns an Xlib.display.Window instance.
		"""

		input_focus = self.__display.get_input_focus()
		if input_focus == None:
			return(None)

		window = input_focus.focus
		if window == None:
			return(None)
		
		return(window);

	def stringToXEvent(self, string):
		"""
		Convert a string representation of an X event to a real X event. 

		String format is :  "[modifier+[modifier+]...]key"
		
		Possible modifiers are:
			shift
			control
			lock
			mod1
			mod2    (usually Alt, but it varies from system to system)
			mod3
			mod4
			mod5

		Key is any definition from /usr/include/X11/keysymdefs.h without the
		XK_ prefix. (Case sensitive)

		Example: "control+d" 
		Example: "shift+mod2+Up"

		Raises ValueError if the string representation contained anything not
		recognised as an X modifier or key. Otherwise, returns an
		Xlib.protocol.event.KeyPress instance

		NOTE: Currently, only key events are implemented.
		"""

		if not isinstance(string, str):
			raise TypeError("Expected a string.")

		state = 0
		keycode = 0

		for part in string.split("+"):
			
			if   part.lower() == "shift": state += Xlib.X.ShiftMask
			elif part.lower() == "control": state += Xlib.X.ControlMask
			elif part.lower() == "lock": state += Xlib.X.LockMask
			elif part.lower() == "mod1": state += Xlib.X.Mod1Mask
			elif part.lower() == "mod2": state += Xlib.X.Mod2Mask
			elif part.lower() == "mod3": state += Xlib.X.Mod3Mask
			elif part.lower() == "mod4": state += Xlib.X.Mod4Mask
			elif part.lower() == "mod5": state += Xlib.X.Mod5Mask
			else:
				keysym = Xlib.XK.string_to_keysym(part)
				if keysym == 0:
					raise ValueError("Not a valid X key: '%s'" % part)

				keycode = self.__display.keysym_to_keycode(keysym)
				if keycode == 0:
					raise ValueError("Not a valid X key: '%s'" % part)
		
		if keycode == 0:
			raise ValueError("Missing a valid X key")

		ev = Xlib.protocol.event.KeyPress(
			time = int(time.time()), 
			root = Xlib.X.NONE,    # FIXME: Will this not reference the wrong root?
			window = Xlib.X.NONE,  # FIXME: Will this not reference the wrong window?
			same_screen = 0, 
			child = Xlib.X.NONE, 
			root_x = 0,
			root_y = 0,
			event_x = 0,
			event_y = 0,
			state = state, # X.h 'state' -> shift, etc
			detail = keycode
		)

		return(ev)

	def stringsToXEvents(self, strings):
		"""
		Convert an list of string representations of X events to an list of
		real X events.

		Returns None if the string representations contained anything not
		recognised as an X modifier or key. Otherwise, returns an list of
		Xlib.protocol.event.KeyPress instances
		"""

		if not isinstance(strings, list) and not isinstance(strings, tuple):
			raise TypeError("Expected a list or tuple.")

		events = []

		for string in strings:
			ev = self.stringToXEvent(string)
			if not ev:
				return(None)
			else:
				events.append(ev)

		return(events)
		
if __name__ == "__main__":

	# Test cases
	display = Xlib.display.Display()

	xevsim = XEventSimulator(display)
	xevsim.setWindow(xevsim.getCurrentFocussedWindow())

	xev_1 = xevsim.stringToXEvent("control+shift+Up")
	xev_2 = xevsim.stringToXEvent("mod2+d")
	xev_3 = xevsim.stringsToXEvents(["shift+p", "Up", "mod2+F4"])
	xev_4 = xevsim.stringsToXEvents(["h", "e", "l", "l", "o", "space", "w", "o", "r", "l", "d"])

	xevsim.addEventSequence("xev_1", [xev_1])
	xevsim.addEventSequence("xev_2", [xev_2])
	xevsim.addEventSequence("xev_3", xev_3)
	xevsim.addEventSequence("xev_4", xev_4)

	xevsim.sendEventSequence("xev_4")
	xevsim.sendEventSequence("xev_1")

