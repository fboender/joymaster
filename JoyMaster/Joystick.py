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

import select
import os
import struct

# Possible joystick events. Taken from linux/joystick.h 
JS_EVENT_BUTTON = 0x01	# button pressed/released
JS_EVENT_AXIS   = 0x02	# joystick moved 
JS_EVENT_INIT   = 0x80	# initial state of device

# Possible Axis events. Taken from linux/input.h 
ABS_X  = 0x00
ABS_Y  = 0x01
ABS_Z  = 0x02   # Not implemented 
ABS_RX = 0x03   # Not implemented
ABS_RY = 0x04   # Not implemented
ABS_RZ = 0x05   # Not implemented

# Defined ourselves
JS_EVENT_RELEASED  = 0x00
JS_EVENT_PRESSED   = 0x01

JS_AXIS_CENTER = 0x00
JS_AXIS_UP     = 0x01
JS_AXIS_RIGHT  = 0x02
JS_AXIS_DOWN   = 0x03
JS_AXIS_LEFT   = 0x04

class _TriggerSequence:
	"""
	This class represents a single joystick trigger. A joystick trigger
	consists out of a name which uniquely identifies the trigger, and a
	sequence. The sequence is an array of possible joystick events in string
	format ('up', 'down', '1', etc). 

	This class is controlled by the Trigger class. 
	"""
	
	name = ""          # Unique identifier for this trigger
	_sequence = []     # Array of events that, if all matched, trigger this trigger
	_running = False   # True if the trigger is currently (partly) matched
	_runningPos = -1   # Current (next) position in the sequence where we need to match events

	def __init__(self, name, sequence):
		
		self.name = name
		self._sequence = sequence

	def setRunning(self, running):
		"""
		Mark this sequence as running/not running. A sequence is running if the
		previous X joystick events matched with sequence[0:X].
		"""

		self._running = running
		if self._running:
			self._runningPos = 1
		else:
			self._runningPos = -1

	def matchFirst(self, str):
		
		if self.matchPos(0, str):
			return (True)
		else:
			return (False)

	def matchNext(self, str):
		match = self.matchPos(self._runningPos, str)
		if match:
			self._runningPos += 1
			return(True)
		else:
			return(False)

	def matchPos(self, pos, str):
		if self._sequence[pos] == str:
			return True
		else:
			return False

	def matchComplete(self):
		if self._runningPos == len(self._sequence):
			return(True)
		else:
			return(False)

	def isRunning(self):
		return(self._running)

class Trigger:

	triggers = []
	triggered = []

	def __init__(self, joystick):

		self.joystick = joystick

	def addTrigger(self, name, sequence):
		
		ts = _TriggerSequence(name, sequence)
		self.triggers.append(ts)
	
	def dumpTriggers(self):
		for ts in self.triggers:
			print ts

	def getTriggered(self):
		self._readJSEvents()
		triggered = self.triggered
		self.triggered = []
		return(triggered)
	
	def _readJSEvents(self):
		js_events = self.joystick.getEvents()

		for js_event in js_events:
			self._handleJSEvent(js_event)

	def _handleJSEvent(self, js_event):
		
		event_type, event_str = self.joystick.eventToString(js_event)
		event_str = str(event_str)

		for trigger in self.triggers:
			
			if trigger.isRunning():
				if not trigger.matchNext(event_str):
					trigger.setRunning(False)
			
			if not trigger.isRunning():
				if trigger.matchFirst(event_str):
					trigger.setRunning(True)

			if trigger.isRunning():
				if trigger.matchComplete():
					trigger.setRunning(False)
					self.triggered.append(trigger.name)

class _JSEvent:
	"""
	Base abstract joystick event class
	"""
	time = 0          # Time (sec) of this event
	elapsed_time = 0  # Time (ms) between this and the last event
	state = 0         # JS_EVENT_* (released, pressed)
	
class _JSEventButton(_JSEvent):
	"""
	Abstract joystick event for button events
	"""

	type = JS_EVENT_BUTTON
	button = 0
	
class _JSEventAxis(_JSEvent):
	"""
	Abstract joystick event for axis events
	"""
	type = JS_EVENT_AXIS
	axis = 0
	direction = 0

class Joystick:
	"""
	Joystick provides an easy interface to events that occured on the joystick.
	"""
	
	events = []

	def __init__(self, joystick_device, skip_btn_release = True, skip_axis_center = True):

		self.skip_btn_release = skip_btn_release
		self.skip_axis_center = skip_axis_center

		self._openDevice(joystick_device)
	
	def _openDevice(self, joystick_device):
		"""
		Try to open the joystick device and handle any device initialization
		events.
		"""
		
		try:
			self.joydev = os.open(joystick_device, os.O_NONBLOCK)
		except OSError, e:
			raise e

		self._readEvents() # Handle (ignore) device initialization

	def getEvents(self):
		"""
		Return an array of joystick events that occured since the last time
		getEvents() was called.
		"""

		self._readEvents()
		events = self.events
		self._flushEvents()

		return(events)
		
	def _readEvents(self):
		"""
		Read and interpret joystick events by querying the kernel and then passing any
		events (that are not initialization events) to _handleEvent().
		"""

		pendingEvents = True
		
		while pendingEvents:
			r, w, e = select.select([self.joydev], [], [], 0)

			if r:
				x = os.read(self.joydev, 8) # FIXME: What's this 8 all about?
				# See http://www.python.org/doc/2.0.1/lib/module-struct.html
				event = struct.unpack('IhBB',x)
				
				time, value, type, number = event

				# Only handle _real_ events; ignore device initialization events
				if type == JS_EVENT_BUTTON or type == JS_EVENT_AXIS:
					self._handleEvent(time, value, type, number)
			else:
				pendingEvents = False
		
	def _handleEvent(self, time, value, type, number):

		if type == JS_EVENT_BUTTON:
			event = _JSEventButton()
			event.button = number + 1
			event.state = value # Pressed OR released

		elif type == JS_EVENT_AXIS:
			event = _JSEventAxis()
			event.direction = self._axisGetDirection(number, value)
			event.state = value 

		event.time = time

		if len(self.events) > 0:
			event.elapsed_time = self.events[-1].time - event.time
		else:
			event.elapsed_time = 0

		self._storeEvent(event)

	def _storeEvent(self, event):
		
		if event.type == JS_EVENT_BUTTON:
			if event.state == JS_EVENT_PRESSED or self.skip_btn_release == False:
				self.events.append(event)
		if event.type == JS_EVENT_AXIS:
			if event.state != 0 or self.skip_axis_center == False:
				self.events.append(event)

	def eventToString(self, event):

		if event.type == JS_EVENT_BUTTON:
			return( ("button", event.button) )
		else:
			if event.direction == JS_AXIS_UP:
				direction_string = "up"
			elif event.direction == JS_AXIS_RIGHT:
				direction_string = "right"
			elif event.direction == JS_AXIS_DOWN:
				direction_string = "down"
			elif event.direction == JS_AXIS_LEFT:
				direction_string = "left"
			elif event.direction == JS_AXIS_CENTER:
				direction_string = "center"
			else:
				direction_string = "unknown"
				
			return( ("axis", direction_string) )

	def _axisGetDirection(self, number, value):

		direction = None

		if number == ABS_X:
			# Horizontal movement 
			if value < 0:
				direction = JS_AXIS_LEFT
			if value > 0: 
				direction = JS_AXIS_RIGHT
			if value == 0:
				direction = JS_AXIS_CENTER
		if number == ABS_Y:
			# vertical movement
			if value < 0:
				direction = JS_AXIS_UP
			if value > 0:
				direction = JS_AXIS_DOWN
			if value == 0:
				direction = JS_AXIS_CENTER

		return (direction)
		
	def _flushEvents(self):

		self.events = []
		
