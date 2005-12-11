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
KeySimulator provides a way of inserting keys into the currently
focussed X window.

This is fairly hacky, seeying as I have no X11 programming experience
whatsoever.
"""

import Xlib.display
import Xlib.X
import Xlib.XK
import time
import re

"""
import Xlib.display
import Xlib.X
import Xlib.XK
display = Xlib.display.Display()
screen = display.screen()
root = screen.root
"""

# Characters that need the Shift modifier
# Stolen from crikey 
# Copyright 2003 by Akkana Peck, http://www.shallowsky.com/software/
# * Modified by Efraim Feinstein, 2004 

_shift_chars = [
	'~', '!', '@', '#', '$', '%', '^', '&', '*', '(', 
	')', '_', '+', '|', '{', '}', ':', '"', '<', '>', '?', 
]

class KeySimulator:

	def __init__(self):
		self._updateReceiverWindow()
		self._buildStringToKeysymMap()

	def _updateReceiverWindow(self):
		self.display = Xlib.display.Display()
		self.screen = self.display.screen()
		self.root = self.screen.root
		self.window = self._getFocusedWindow()

		
	def sendString(self, string):
		self.window = self._getFocusedWindow()

		events = self._stringToKeyEvents(string)
		if events:
			self._sendEvents(self.window, events)
		
	def sendKey(self, key):
		# FIXME: Not implemented
		pass


	def getReceiverInfo(self):
		"""
		Return a list with the window class and name information for the window
		that will receive the simulated keypresses.
		"""

		self._updateReceiverWindow()

		wm_class = self.window.get_wm_class()
		wm_name = self.window.get_wm_name()

		if wm_class:
			wm_class = ".".join(wm_class)
		else:
			wm_class = ""

		if not wm_name:
			wm_name = ""

		return( (wm_class, wm_name) )

	def _sendEvents(self, window, events):

		for event in events:
			window.send_event(event, propagate = True)

		self.display.sync()

	def _buildStringToKeysymMap(self):

		"""
		Xlib's string_to_keysym() doesn't seem to convert some chars to correct
		keysyms, but when doing it the other way (via keysym_to_string()) most
		characters do show up. So we build a map of all keysyms which we can
		reference.
		"""

		self.keysym_map = {}
		
		for keysym in range(0, 65535):
			string = Xlib.XK.keysym_to_string(keysym)
			if string:
				self.keysym_map[string] = keysym

	def _getFocusedWindow(self):
	
		input_focus = self.display.get_input_focus()
		
		return(input_focus._data["focus"]);

	def _stringToKeyEvents(self, string):

		key_events = []

		parts = re.split("(\[.*?\])", string)

		# Get the keysym for the current character or special key in the string
		for part in parts:

			if part == '':
				# RegEx artifact. ;-)
				pass
			elif part[0] == '[':
				# Special command
				command = part[1:-1]

				mod_cmd = command.split('+')
				state = 0
				for p in mod_cmd:
					if p == "shift":
						state += Xlib.X.ShiftMask
					if p == "control":
						state += Xlib.X.ControlMask
					if p == "lock":
						state += Xlib.X.LockMask
					if p == "mod1":
						state += Xlib.X.Mod1Mask
					if p == "mod2":
						state += Xlib.X.Mod2Mask
					if p == "mod3":
						state += Xlib.X.Mod3Mask
					if p == "mod4":
						state += Xlib.X.Mod4Mask
					if p == "mod5":
						state += Xlib.X.Mod5Mask
					else:
						cmd = p

				keysym = Xlib.XK.string_to_keysym(cmd)
				if keysym > 0:
					keycode = self.display.keysym_to_keycode(keysym)
					key_events.append(self._createKeyEvent(keycode, state))
				else:
					sys.stderr.write("Unknown keysym '%s'\n" % keysym)
			else:
				# String of normal keys
				for c in part:
					if c in self.keysym_map:
						keysym = self.keysym_map[c]
						keycode = self.display.keysym_to_keycode(keysym)
						if c in _shift_chars:
							key_events.append(self._createKeyEvent(keycode, Xlib.X.ShiftMask))
						else:
							key_events.append(self._createKeyEvent(keycode))

		return(key_events)

	def _createKeyEvent(self, key_code, state = 0):
		
		ev = Xlib.protocol.event.KeyPress(
			time = int(time.time()), # Moet misschien een int zijn, is nu een float.
			root = self.root,
			window = self.window,
			same_screen = 0,
			child = Xlib.X.NONE, 
			root_x = 0,
			root_y = 0,
			event_x = 0,
			event_y = 0,
			state = state, # X.h 'state' -> shift, etc
			detail = key_code
		)

		return(ev)
		
