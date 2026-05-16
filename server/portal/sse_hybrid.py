"""
AJAX/SSE webclient

This web client protocol uses two separate components: a Session, for Evennia's session handling, and
a Resource, which manages the pool of client connections linked to the Sessions.

It's intended to replace the websocket and AJAX-fallback systems entirely, so it may not be
suitable if you wish to support very very old browsers. Adding it as a separate endpoint rather 
than coopting the /webclientdata endpoint is, however, possible.
"""

import html
import json
import re
import time

from django.conf import settings
from django.utils.functional import Promise
from twisted.internet.task import LoopingCall
from twisted.web import resource, server

from evennia.server import session
from evennia.utils import utils, logger
from evennia.utils.ansi import parse_ansi
from evennia.utils.utils import ip_from_request, to_bytes

from server.portal.text2html import parse_html

_CLIENT_SESSIONS = utils.mod_import(settings.SESSION_ENGINE).SessionStore
_RE_SCREENREADER_REGEX = re.compile(
	r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)
_KEEPALIVE = 30  # how often to check keepalive


# defining a simple json encoder for returning django data to the client, borrowed from Evennia.
class LazyEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Promise):
			return str(obj)
		return super().default(obj)


def jsonify(obj):
	return to_bytes(json.dumps(obj, ensure_ascii=False, cls=LazyEncoder))


#
# A session type handling communication over the web client interface.
#

class HybridSSESession(session.Session):
	"""
	This represents a session running in the hybrid Ajax/SSE webclient.
	"""
	pgid = None

	def __init__(self, *args, **kwargs):
		self.protocol_key = "ajax/SSE"
		super().__init__(*args, **kwargs)

	def init_session(self, protocol_key, address, sessionhandler):
		self.last_alive = time.time()
		return super().init_session(protocol_key, address, sessionhandler)

	def get_client_session(self):
		"""
		Get the client's browser session (used for auto-login based on browser session)

		Returns:
			csession (ClientSession): This is a django-specific internal representation
				of the browser session.

		"""
		if self.csessid:
			return _CLIENT_SESSIONS(session_key=self.csessid)

	def disconnect(self, reason="Server disconnected."):
		"""
		Disconnect from server.

		Args:
			reason (str): Motivation for the disconnect.
		"""
		logger.log_msg(f"disconnecting session {self}, reason {reason}")
		csession = self.get_client_session()

		if csession:
			csession["webclient_authenticated_uid"] = None
			csession.save()
			self.logged_in = False
		self.client.lineSend(self.csessid, self.pgid, ["connection_close", [reason], {}])
		self.client.client_disconnect(self.csessid)
		self.sessionhandler.disconnect(self)

	def at_login(self):
		csession = self.get_client_session()
		if csession:
			csession["webclient_authenticated_uid"] = self.uid
			csession.save()

	def data_in(self, **kwargs):
		"""
		Data User -> Evennia

		Keyword Args:
			kwargs (any): Incoming data.

		"""
		self.last_alive = time.time()
		self.sessionhandler.data_in(self, **kwargs)

	def data_out(self, **kwargs):
		"""
		Data Evennia -> User

		Keyword Args:
			kwargs (any): Options to the protocol
		"""
		self.sessionhandler.data_out(self, **kwargs)

	def _format_output(self, message, options=None, **kwargs):
		"""
		Takes a message and makes sure to parse all of the format codes to the target HTML styling

		Args:
			message (str): Text to send.

		Keyword Args:
			options (dict): Options-dict with the following keys understood:
				- raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
				- nocolor (bool): Remove all color.
				- screenreader (bool): Use Screenreader mode.
		"""

		flags = self.protocol_flags
		options = options or {}
		raw = options.get("raw", flags.get("RAW", False))
		xterm256 = options.get("xterm256", flags.get("XTERM256", True))
		useansi = options.get("ansi", flags.get("ANSI", True))
		nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
		screenreader = options.get("screenreader", flags.get("SCREENREADER", False))

		if screenreader:
			# screenreader mode cleans up output
			message = parse_ansi(message, strip_ansi=True, xterm256=False, mxp=False)
			message = _RE_SCREENREADER_REGEX.sub("", message)

		if raw:
			return message
		else:
			return parse_html(message, strip_ansi=nocolor)


	def send_text(self, *args, **kwargs):
		"""
		Send text data.
		"""

		if not args:
			return
		args = list(utils.make_iter(args))
		if not (text := args[0]):
			return

		text = utils.to_str(text)
		args[0] = self._format_output(text, **kwargs)

		# send to client on required form [cmdname, args, kwargs]
		self.client.lineSend(self.csessid, self.pgid, ["text", args, kwargs])

	def send_prompt(self, *args, **kwargs):
		"""
		Send prompt data.
		"""
		if not args:
			return
		args = list(utils.make_iter(args))
		if not (text := args[0]):
			return

		text = utils.to_str(text)
		args[0] = self._format_output(text, **kwargs)

		# send to client on required form [cmdname, args, kwargs]
		self.client.lineSend(self.csessid, self.pgid, ["prompt", args, kwargs])

	def send_map(self, *args, **kwargs):
		"""
		Send map data.
		"""
		if not args:
			return
		args = list(utils.make_iter(args))
		if not (text := args[0]):
			return

		text = utils.to_str(text)
		args[0] = self._format_output(text, **kwargs)

		# send to client on required form [cmdname, args, kwargs]
		self.client.lineSend(self.csessid, self.pgid, ["map", args, kwargs])

	def send_default(self, cmdname, *args, **kwargs):
		"""
		Data Evennia -> User.

		Args:
			cmdname (str): The first argument will always be the oob cmd name.
			*args (any): Remaining args will be arguments for `cmd`.

		Keyword Args:
			*kwargs (any): Will be sent as keyword arguments for `cmd`
		"""

		if not cmdname == "options":
			self.client.lineSend(self.csessid, self.pgid, [cmdname, args, kwargs])


#
# SSE/Ajax Webclient Resource - called by the webclient at the /webclientdata endpoint
#


class HybridSSEHub(resource.Resource):
	"""
	A hybrid ajax/SSE transport

	"""

	client_protocol = HybridSSESession

	isLeaf = True
	allowedMethods = ("POST","GET")

	def __init__(self):
		self.sessions = {}
		self.streams = {}
		self.databuffer = {}
		self.keep_alive = None

	def _keepalive(self):
		"""
		Callback for checking if the connection is still alive.
		"""
		now = time.time()
		sessions = list(self.sessions.values())
		timed_out = (
			sess
			for sess in sessions
			# if session is both logged in and has an active stream, we keep it regardless
			if not (sess.logged_in and sess.stream)
			# otherwise, we check if it's been idle for longer than the keepalive window
			and (now - sess.last_alive) > _KEEPALIVE
		)
		# remove timed-out sessions
		for sess in timed_out:
			self.sessions.pop(sess.csessid + sess.pgid, None)
			sess.disconnect()
		# stop task if there's nothing left to be keeping alive for now
		if not len(self.sessions.keys()):
			self.keep_alive.stop()
			self.keep_alive = None

	def _session_id_from_POST(self, request):
		"""
		Helper to get the client session id out of POST requests.

		Args:
			request (Request): Incoming request object.
		Returns:
			str: The client-session id.
		"""

		return str(html.escape(request.args.get(b"sessid")[0].decode("utf-8")))

	def _page_id_from_POST(self, request):
		"""
		Helper to get the client page id out of POST requests.

		Args:
			request (Request): Incoming request object.
		Returns:
			str: The client-page id.
		"""

		return str(html.escape(request.args.get(b"pgid")[0].decode("utf-8")))


	def _metadata_from_stream(self, request):
		"""
		Helper to get the client's metadata from a stream connection
		"""
		session_id, page_id = '',''
		# client will connect with wsurl?csessid&page_id&browserid
		webarg = request.uri.decode('utf-8').split("?", 1)[1]
		session_id, *cargs = webarg.split("&")
		if cargs:
			page_id = str(cargs[0])
		return session_id, page_id

	# def at_login(self):
	# 	"""
	# 	Called when this session gets authenticated by the server.
	# 	"""
	# 	pass

	def lineSend(self, session_id, page_id, data):
		"""
		This sends data to the client over the SSE stream, or adds to buffer if the stream is down.

		Args:
			session_id (int): User session id.
			page_id (int): Client page id.
			data (list): A send structure [cmdname, [args], {kwargs}].
		"""

		uid = session_id+page_id
		if not (sess := self.sessions.get(uid)):
			return
		if stream := sess.stream:
			# we have an event stream open
			stream.write("data: {}".format(json.dumps(data)).encode('utf-8'))
			stream.write("\n\n".encode('utf-8'))
		else:
			# no available stream. Store data in buffer to send later
			dataentries = self.databuffer.get(uid, [])
			dataentries.append(jsonify(data))
			self.databuffer[uid] = dataentries

	def client_disconnect(self, uid):
		"""
		Disconnect session with given id.

		Args:
			uid (int): Unique session id, from concatenated user session ID and page UID
		"""

		if uid in self.sessions:
			del self.sessions[uid]
		if uid in self.databuffer:
			del self.databuffer[uid]

	def _create_session(self, session_id, page_id, remote_addr):
		"""
		create and initialize a new session
		"""
		# basic session initialization
		sess = self.client_protocol()
		sess.client = self
		sess.init_session("sse/ajax", remote_addr, self.sessionhandler)
		# protocol-specific initialization
		sess.csessid = session_id
		sess.pgid = page_id
		csession = _CLIENT_SESSIONS(session_key=session_id)
		uid = csession and csession.get("webclient_authenticated_uid", False)
		if uid:
			# the client session is already logged in
			sess.uid = uid
			sess.logged_in = True
		sess.protocol_flags["CLIENTNAME"] = f"Evennia Webclient (sse/ajax)"
		sess.protocol_flags["UTF-8"] = True
		sess.protocol_flags["OOB"] = True
		# actually do the connection
		sess.sessionhandler.connect(sess)
		# add the new session to our data
		self.sessions[session_id+page_id] = sess

		# make sure the keepalive/timeout task is running
		if not self.keep_alive:
			self.keep_alive = LoopingCall(self._keepalive)
			self.keep_alive.start(_KEEPALIVE, now=False)

		return sess

	def stream_connect(self, request):
		"""
		Called when a new stream is initialized and adds to the streams.
		"""
		session_id, page_id = self._metadata_from_stream(request)
		remote_addr = ip_from_request(request)

		csessid = session_id+page_id
		sess = self.sessions.get(csessid)
		if not sess:
			# we have to make a new one
			sess = self._create_session(session_id, page_id, remote_addr)

		# store the stream
		sess.stream = request

		# grab any buffered messages and send them down the stream
		if dataentries := self.databuffer.pop(csessid,None):
			for entry in dataentries:
				request.write(entry)
				request.write("\n\n".encode('utf-8'))

	def stream_disconnect(self, request, csessid):
		"""
		Called when a stream is closed or lost and removes it from the streams.
		"""
		if sess := self.sessions.get(csessid):
			# remove the stream from the session
			sess.stream = None
			# set last-alive timestamp to now, to prevent premature timeouts
			sess.last_alive = time.time()
		else:
			logger.log_warn(f"Disconnect event for stream with id {csessid} but no such session found.")

	def mode_input(self, request):
		"""
		This is called by render_POST when the client
		is sending data to the server.

		Args:
			request (Request): Incoming request.
		"""

		session_id = self._session_id_from_POST(request)
		page_id = self._page_id_from_POST(request)
		csessid =  session_id+page_id
		cmdarray = json.loads(request.args.get(b"data")[0])
		if sess := self.sessions.get(csessid):
			sess.data_in(**{cmdarray[0]: [cmdarray[1], cmdarray[2]]})
		else:
			logger.log_warn(f'received input for {csessid} but no session found')
		return b'""'

	def mode_close(self, request):
		"""
		This is called by render_POST when the client is signalling
		that it is about to be closed.

		Args:
			request (Request): Incoming request.
		"""

		csessid = self._session_id_from_POST(request) + self._page_id_from_POST(request)
		if sess := self.sessions.get(csessid):
			sess.disconnect(reasons="Connection closed.")
		else:
			self.client_disconnect(csessid)
		return b'""'

	def render_POST(self, request):
		"""
		This function is what Twisted calls with POST requests coming
		in from the ajax client. The requests should be tagged with
		different modes depending on what needs to be done, such as
		initializing or sending/receving data through the request. It
		uses a long-polling mechanism to avoid sending data unless
		there is actual data available.

		Args:
			request (Request): Incoming request.

		"""
		dmode = request.args.get(b"mode", [b"None"])[0].decode("utf-8")

		return self.mode_input(request)

	def render_GET(self, request):
		"""
		This method is what Twisted calls when it receives a GET request. We use this
		to connect the underlying SSE stream.
		"""
		request.setHeader('Content-Type', 'text/event-stream; charset=utf-8')
		request.setHeader('Cache-Control', 'no-cache')
		request.setHeader('X-Accel-Buffering', 'no')
		request.setResponseCode(200)
		# this request will be kept open as the event stream
		self.stream_connect(request)
		session_id, page_id = self._metadata_from_stream(request)
		# when the request is "finished" it means the stream closed...
		d = request.notifyFinish()
		# ... so we clean up the connection
		d.addBoth(self.stream_disconnect, session_id+page_id)
		request.write("")
		# keep the request active
		return server.NOT_DONE_YET
