class TriggerSequence:
	"""
	This class represents a single joystick trigger. A joystick trigger
	consists out of a name which uniquely identifies the trigger, and a
	sequence. The sequence is an array of possible joystick events in string
	format ('up', 'down', '1', etc).

	This class is controlled by the Trigger class.
	"""
	name = ""          # Unique identifier for this trigger
	__sequence = []     # Array of events that, if all matched, trigger this trigger
	__running = False   # True if the trigger is currently (partly) matched
	__runningPos = -1   # Current (next) position in the sequence where we need to match events

	def __init__(self, name, sequence):
		self.name = name
		self.__sequence = sequence

	def setRunning(self, running):
		"""
		Mark this sequence as running/not running. A sequence is running if the
		previous X joystick events matched with sequence[0:X].
		"""

		self.__running = running
		if self.__running:
			self.__runningPos = 1
		else:
			self.__runningPos = -1

	def matchFirst(self, str):
		if self.matchPos(0, str):
			return (True)
		else:
			return (False)

	def matchNext(self, str):
		match = self.matchPos(self.__runningPos, str)
		if match:
			self.__runningPos += 1
			return(True)
		else:
			return(False)

	def matchPos(self, pos, str):
		if self.__sequence[pos] == str:
			return True
		else:
			return False

	def matchComplete(self):
		if self.__runningPos == len(self.__sequence):
			return(True)
		else:
			return(False)

	def isRunning(self):
		return(self.__running)

class Trigger:
	__triggers = []
	__triggered = []

	def __init__(self, joystick):
		self.joystick = joystick

	def addTrigger(self, name, sequence):
		ts = TriggerSequence(name, sequence)
		self.__triggers.append(ts)

	def clearTriggers(self):
		"""
		Remove all triggers.
		"""
		self.__triggers = []

	def dumpTriggers(self):
		for ts in self.__triggers:
			print ts

	def getTriggered(self):
		self.__readJSEvents()
		triggered = self.__triggered
		self.__triggered = []
		return(triggered)

	def __readJSEvents(self):
		js_events = self.joystick.getEvents()

		for js_event in js_events:
			self.__handleJSEvent(js_event)

	def __handleJSEvent(self, js_event):
		event_type, event_str = self.joystick.eventToString(js_event)
		event_str = str(event_str)

		for trigger in self.__triggers:
			if trigger.isRunning():
				if not trigger.matchNext(event_str):
					trigger.setRunning(False)

			if not trigger.isRunning():
				if trigger.matchFirst(event_str):
					trigger.setRunning(True)

			if trigger.isRunning():
				if trigger.matchComplete():
					trigger.setRunning(False)
					self.__triggered.append(trigger.name)

