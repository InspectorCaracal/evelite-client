import time
import evennia
from django.conf import settings
from twisted.internet import reactor
from evennia.server.portal.portalsessionhandler import PortalSessionHandler as CorePortalSessionHandler
from evennia.server.sessionhandler import ServerSessionHandler as CoreServerSessionHandler
from evennia.utils import logger

# per-session throttles
_MAX_COMMAND_RATE = float(settings.MAX_COMMAND_RATE)
_MAX_CHAR_LIMIT = int(settings.MAX_CHAR_LIMIT)

_MIN_TIME_BETWEEN_COMMANDS = 1.0 / float(_MAX_COMMAND_RATE)

_ERROR_COMMAND_OVERFLOW = settings.COMMAND_RATE_WARNING
_ERROR_MAX_CHAR = settings.MAX_CHAR_LIMIT_WARNING

# mildly hacky solution for the server not coming back up
_LAST_ATTEMPTED_RESTART = None
_RESTART_ATTEMPT_RATE = 10

class PortalSessionHandler(CorePortalSessionHandler):
	def data_in(self, session, **kwargs):
		"""
		Called by portal sessions for relaying data coming
		in from the protocol to the server.

		Args:
			session (PortalSession): Session receiving data.

		Keyword Args:
			kwargs (any): Other data from protocol.

		Notes:
			Data is serialized before passed on.

		"""
		if not session:
			return

		if not evennia.EVENNIA_PORTAL_SERVICE.amp_protocol:
			# this can happen if someone connects before AMP connection
			# was established (usually on first start)
			reactor.callLater(1.0, self.data_in, session, **kwargs)
			return
		_amp = evennia.EVENNIA_PORTAL_SERVICE.amp_protocol
		status = _amp.get_status()
		if not status[1]:
			reactor.callLater(1.0, self.data_in, session, **kwargs)
			if not _LAST_ATTEMPTED_RESTART or (time.time() - _LAST_ATTEMPTED_RESTART) > _RESTART_ATTEMPT_RATE:
				logger.log_warn("Server is DOWN. Attempting to relaunch.")
				_amp.start_server(_amp.factory.portal.server_twistd_cmd)
			return


		if text := kwargs.get("text"):
			if (_MAX_CHAR_LIMIT > 0) and len(text) > _MAX_CHAR_LIMIT:
				self.data_out(session, text=[[_ERROR_MAX_CHAR], {}])
				return
		now = time.time()

		try:
			command_counter_reset = session.command_counter_reset
		except AttributeError:
			command_counter_reset = session.command_counter_reset = now
			session.command_counter = 0

		# global command-rate limit
		if max(0, now - command_counter_reset) > 1.0:
			# more than a second since resetting the counter. Refresh.
			session.command_counter_reset = now
			session.command_counter = 0

		session.command_counter += 1

		if session.command_counter * _MIN_TIME_BETWEEN_COMMANDS > 1.0:
			self.data_out(session, text=[[_ERROR_COMMAND_OVERFLOW], {}])
			return

		# scrub data
		kwargs = self.clean_senddata(session, kwargs)

		# relay data to Server
		session.cmd_last = now
		evennia.EVENNIA_PORTAL_SERVICE.amp_protocol.send_MsgPortal2Server(session, **kwargs)

		# eventual local echo (text input only)
		if text and session.protocol_flags.get("LOCALECHO", False):
			self.data_out(session, text=text)
