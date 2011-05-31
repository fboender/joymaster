#!/usr/bin/python
#
# Copyright 2005-2010, Ferry Boender <ferry DOT boender AT electricmonk DOT nl>
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
Joystick provides easy access to joystick events.
"""

import select
import os
import struct
import logging

# Possible joystick events. Taken from linux/joystick.h 
JS_TYPE_BUTTON    = 0x01  # button pressed/released
JS_TYPE_AXIS      = 0x02  # joystick moved 
JS_TYPE_INIT      = 0x80  # initial state of device
JS_TYPE_INIT_BTN  = 0x81  # Device capability discovery (buttons)
JS_TYPE_INIT_AXIS = 0x82  # Device capability discovery (axis)

# Possible Axis events. Taken from linux/input.h 
JS_ABS_X  = 0x00
JS_ABS_Y  = 0x01
JS_ABS_Z  = 0x02   # Not implemented 
JS_ABS_RX = 0x03   # Not implemented
JS_ABS_RY = 0x04   # Not implemented
JS_ABS_RZ = 0x05   # Not implemented

# Defined ourselves
JS_STATE_RELEASED  = 0x00
JS_STATE_PRESSED   = 0x01

JS_AXIS_CENTER = 0x00
JS_AXIS_UP     = 0x01
JS_AXIS_RIGHT  = 0x02
JS_AXIS_DOWN   = 0x03
JS_AXIS_LEFT   = 0x04

class JSEvent:
	"""
	Base abstract joystick event class.
	"""
	def __init__(self, time, value, type, number):
		self._time = time
		self._value = value
		self._type = type
		self._number = number

class JSEventInit(JSEvent):
	"""
	Abstract joystick event for initialization
	"""
	def __init__(self, time, value, type, number):
		self.type = JS_TYPE_INIT
		JSEvent.__init__(self, time, value, type, number)

	def __repr__(self):
		return('<JSEventInit instance>')

class JSEventButton(JSEvent):
	"""
	Abstract joystick event for button events
	"""
	def __init__(self, time, value, type, number):
		self.type = JS_TYPE_BUTTON
		self.button = number
		self.state = value
		JSEvent.__init__(self, time, value, type, number)

	def __repr__(self):
		return('<JSEventButton instance (btn=%s, state=%s)>' % (self.button, self.state))

class JSEventAxis(JSEvent):
	"""
	Abstract joystick event for axis events
	"""
	def __init__(self, time, value, type, number):
		self.type = JS_TYPE_AXIS
		if number == JS_ABS_X:
			# Horizontal movement 
			if value < 0:
				self.direction = JS_AXIS_LEFT
			if value > 0:
				self.direction = JS_AXIS_RIGHT
			if value == 0:
				self.direction = JS_AXIS_CENTER
		if number == JS_ABS_Y:
			# vertical movement
			if value < 0:
				self.direction = JS_AXIS_UP
			if value > 0:
				self.direction = JS_AXIS_DOWN
			if value == 0:
				self.direction = JS_AXIS_CENTER
		JSEvent.__init__(self, time, value, type, number)

	def __repr__(self):
		return('<JSEventAxis instance (dir=%s)>' % (self.direction))

def JSEventFactory(time, value, type, number):
	"""
	Return proper JSEvent* class giving input params.
	"""
	type_map = {
		JS_TYPE_BUTTON: JSEventButton,
		JS_TYPE_AXIS: JSEventAxis,
		JS_TYPE_INIT: JSEventInit,
		JS_TYPE_INIT_BTN: JSEventInit,
		JS_TYPE_INIT_AXIS: JSEventInit,
	}
	return(type_map[type](time, value, type, number))

class Joystick:
	"""
	Joystick provides an easy interface to events that occured on the joystick.
	"""
	def __init__(self, device='/dev/input/js0', skip_btn_release = True, skip_axis_center = True):
		self.log = logging.getLogger("joymaster.Joystick")
		self.device = device
		self.skip_btn_release = skip_btn_release
		self.skip_axis_center = skip_axis_center
		self.events = []

		# Try to open the device
		self.log.debug('Opening device %s' % (device))
		try:
			self.joydev = os.open(self.device, os.O_NONBLOCK)
		except OSError, e:
			raise e

		# Handle (ignore) device initialization
		self.read_events(wait_time = 0)

	def has_events(self, wait_time = 0):
		"""
		Returns True or False depending on whether events are waiting from the joystick. wait_time determines how long to wait for an event (in seconds); None will wait eternally
		"""
		r, w, e = select.select([self.joydev], [], [], wait_time)
		return(bool(r))

	def read_events(self, wait_time = None):
		"""
		Return a list of events of type JSEvent*. wait_time determines how long
		to wait for incoming events (in seconds). None = wait forever, 0 =
		don't wait. Default is None.
		"""
		events = []
		while True:
			if self.has_events(wait_time):
				x = os.read(self.joydev, 8)
				# See http://www.python.org/doc/2.0.1/lib/module-struct.html
				event = struct.unpack('IhBB',x)
				time, value, type, number = event

				self.log.debug(
					'Raw event received: time: %s, value: %s, type: %s, number: %s' % (
					time, value, type, number)
				)
				jsevent = JSEventFactory(time, value, type, number)
				self.log.debug('Event received: %s' % (jsevent))

				# Don't report button releases and axis centering
				if not (
					jsevent.type == JS_TYPE_BUTTON and
					self.skip_btn_release and
					jsevent.state == JS_STATE_RELEASED
				) and not (
					jsevent.type == JS_TYPE_AXIS and
					self.skip_axis_center and
					jsevent.direction == JS_AXIS_CENTER
				):
					events.append(jsevent)
			else:
				break
			wait_time = 0
		return(events)

if __name__ == "__main__":
	logging.basicConfig()
	log = logging.getLogger("joymaster")
	log.setLevel(logging.DEBUG)

	j = Joystick('/dev/input/js1')
	while True:
		print j.read_events()
