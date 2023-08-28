// convenience access for the most commonly used page elements
const input_box = document.getElementById("input_box");
const game_out = document.getElementById("_log");
// the full suite i think will require a different solution for getting the element, since i don't know if these characters are valid in element IDs
// const keybind_labels = [ '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '+', 'Enter', '.', '-', '*', '/' ];
 const keybind_labels = [ '1', '2', '3', '4', '5', '6', '7', '8', '9' ];

// websocket info
const wsstring = wsurl +"?"+ csessid;
var socket = new WebSocket(wsstring);
var pingInterval;

// not currently used
function toggleTheme(e) {
	if (e.checked) {
		document.documentElement.setAttribute('data-theme', 'dark');
		localStorage.theme = "dark";
	}
	else {
		document.documentElement.setAttribute('data-theme', 'light');
		localStorage.theme = "light";
	}
}

// parses the element to attach click events to mxplink-classed elements
function MakeClickables(el) {
	for (var i = 0; i < el.childNodes.length; i++) {
		curr = el.childNodes[i];
		if (curr.nodeType != 1) continue;
		if (curr.classList.contains("mxplink")) {
			curr.addEventListener("click", mxp_send);
    }        
		MakeClickables(curr);
	}
}

// base function for adding new log lines to the end of an element
function LogTo(el, msg, cls) {
	if (msg) {
		msg_div = '<div class="'+cls+'">'+msg+'</div>';
		el.insertAdjacentHTML("beforeend",msg_div);
		// parses the newly added element to make clickable mxp
		MakeClickables(el.lastChild);
		// scroll the element down to the bottom so the new line is visible
		el.scrollTop = el.scrollHeight;
		// you can do any extra processing to the msg here that you want for the log, such as adding a timestamp
		// here, we just add a break tag
		if (localStorage[document.title + el.id])	localStorage[document.title + el.id] += "<br/>" + msg;
		else localStorage[document.title + el.id] = msg;
	}
}

// clear all content from a log div
function LogClear(el) {
	el.innerHTML = "";
}

function LogDownload(el) {
	var log_el = el.parentNode;
	var data = localStorage[document.title + log_el.id];
	// we set it by default to be text/html because the logged items have all the html tags
	var textAsBlob = new Blob([data], {type: "text/html"});
	var blobAsURL = window.URL.createObjectURL(textAsBlob);

	var downloadLink = document.createElement("a");
	downloadLink.download = document.title + log_el.id + ".html";
	downloadLink.innerHTML = "Download Log";
	downloadLink.href = blobAsURL;
	downloadLink.onclick = function (event) { document.body.removeChild(event.target); }
	downloadLink.style.display = "none";
	document.body.appendChild(downloadLink);
 
	downloadLink.click();
}

// wrapper function for setting the innerHTML of an element
function SetHTML(id, content) {
	el = document.getElementById(id);
	el.innerHTML = content;
	MakeClickables(el);
}

// wrapper function for updating the map view
function UpdateMap(message) {
	SetHTML("map", message);
}
// function for updating the status bar
function UpdateStatus(input) {
	message = input[1][0];
	// you can grab extra data here from msg[2] if you want a more complex status bar
	// e.g. sending {'hp': .7} and then setting the fill of the HP bar to .7*width
	SetHTML("prompt", message);
}

// wrapper function for adding a new game message to the game log
function GameMsg(message) {
	LogTo(game_out,message,"message");
}
// wrapper function for logging your inputs to the game log
function EchoMsg(message) {
	LogTo(game_out,message,"echo");
}
// wrapper function for adding a new server/system message to the game log
function ServerMsg(message) {
	LogTo(game_out, message, "system")
}

// function for adding a new channel message to the correct channel log
function ChannelMsg(message, channid) {
	var chan_elem = document.getElementById(channid + "_log");
	if (!chan_elem) {
		// sometimes we might receive a channel message before we've received the chaninfo for it
		// so we add the channel with a placeholder channel name
		AddChannel(channid, '(loading)');
		chan_elem = document.getElementById(channid + "_log");
	}
	LogTo(chan_elem,message,"message");
}

// requests a list of all the account's subscribed channels from the portal
function LoadChannels() {
	SendFunc('get_channels', '', {});
}
// create or update a new channel tab and log
function AddChannel(channid, channame) {
	if (!document.getElementById(channid+"_log")) {
		new_log = document.createElement('div');
		new_log.id = channid + "_log";
		new_log.classList.add("invisible");
		new_log.classList.add("log");
		// TODO: make this less hardcoded
		new_log.innerHTML = '<div class="dl-button" onclick="LogDownload(this)" alt="Download this log" title="Download this log">📥</div>';
		// how do i add the "log" role from here
		document.getElementById('main').append(new_log);
	}
	// handle name updates for async
	var old_tab = document.getElementById(channid+"_tab");
	if (old_tab) {
		old_tab.innerText = channame;
		old_tab.dataset.channame = channame;
	}
	else {
		new_tab = document.createElement('span');
		new_tab.id = channid + "_tab";
		new_tab.dataset.channel = channid;
		new_tab.dataset.channame = channame;
		new_tab.classList.add("chan-tab");
		new_tab.innerText = channame;
		new_tab.addEventListener("click", swapChannel, false);
		document.getElementById('tab_area').append(new_tab);
	}
}

// remove a channel tab
function RemoveChannel(channid) {
	// the only "channel" without an ID is the Game tab, which cannot be removed
	if (channid) {
		log_area = document.getElementById(channid+"_log");
		log_tab = document.getElementById(channid+"_tab");
		if (log_tab) log_tab.remove();
		if (log_area) log_area.remove();
	}
}

// change the currently active log view to one of the channels, or to the game log
function swapChannel(e) {
	channid = this.dataset.channel;
	if (!channid)	channid = '';
	new_log = document.getElementById(channid + "_log");
	if (!new_log) {
		new_log = document.createElement('div');
		new_log.id = channid + "_log";
		document.getElementById('main').append(new_log);
	}
	else {
		new_log.classList.remove("invisible");
	}
	curr_chan = input_box.dataset.channel;
	if (!curr_chan) curr_chan = '';
	curr_log = document.getElementById(curr_chan + "_log");
	if (curr_log) {
		curr_log.classList.add('invisible');
	}
	curr_tab = document.getElementById(curr_chan + "_tab");
	if (curr_tab) {
		curr_tab.classList.remove('active-tab');
	}
	this.classList.add('active-tab');
	input_box.dataset.channel = channid;
	new_log.scrollTop = new_log.scrollHeight;
}

// function to navigate back and forward through the tab's session input history
function NavCmdHistory(el, store_key, direction) {
	var store_item = sessionStorage.getItem(store_key);
	if (!store_item) return;
	store_item = JSON.parse(store_item);
	var index = el.dataset.cmd_index;
	if (!index) {
		// assume we're at the end
		index = store_item.length;
		if (el.value) {
			store_item.push(el.value);
			LogSessionCmd(store_key, el.value);
		}
	}
	else index = Number(index);
	index += direction;
	if ((index < store_item.length) && (index >= 0)) {
		el.value = store_item[index];
		el.dataset.cmd_index = index;
	}
}
// function to add an input to the session input history
function LogSessionCmd(store_key, message) {
	var store_item = sessionStorage.getItem(store_key);
	if (store_item) {
		store_item = JSON.parse(store_item);
		store_item.push(message);
	}
	else {
		store_item = [ message ];
	}
	sessionStorage.setItem(store_key, JSON.stringify(store_item));
}

// function to load commands to numpad bindings
function UpdateCmdKeys(bindings) {
	// walk through all of the keys and update
	for (key in keybind_labels) {
		key_el = document.getElementById("keybind_"+key);
		if (!key_el) continue;
		if (bindings[key]) {
			// set the command for the key
			key_el.dataset.command = bindings[key];
			// set the display text
			keystr = `( ${key} )`;
			key_el.innerHTML = bindings[key] + "<br/>" + keystr;
			key_el.classList.remove("invisible");
			// add the click event
			key_el.addEventListener('click', KeybindClickEvent);
		}
		else {
			// hide the button and remove the event
			key_el.classList.add("invisible");
			key_el.removeEventListener('click', KeybindClickEvent);
		}
	}
}

// wrappers for the events because i'm too lazy to coordinate the keypress and click properly rn
function KeybindClickEvent(e) {
	KeybindCmd(this);
}
function KeybindPressEvent(e) {
	key_el = document.getElementById("keybind_"+String(e.key));
	if (key_el)	{
		if (KeybindCmd(key_el)) e.preventDefault();
	}
}
// actually execute a keybind command
function KeybindCmd(el) {
	command = el.dataset.command;
	if (!command) return false;
	SendFunc('text', command, {});
	return true;
}

// wrapper function for sending a command back over the websocket to the server
function SendFunc(func, args, kwargs) {
	data = [func, args, kwargs];
	socket.send(JSON.stringify(data));
}

// function to execute the connected command when clicking on an mxp link
// this function uses a customized mxp-link parsing, which is why a customized text2html is provided
function mxp_send(e) {
	if (typeof(this.dataset.command) == 'undefined') return;
	command = this.dataset.command;
	if (e.ctrlKey || e.shiftKey) {
		pieces = command.split(" ");
		command = "look "+ pieces.slice(1).join(" ");
	}
	SendFunc('text', command, '');
}

// initialize the websocket once the connection is established
socket.onopen = function (e) {
	// implements a ping/pong between the browser and the server's websocket to prevent timeouts
	pingInterval = setInterval(function(){ SendFunc('ping', 'ping', ''); }, 45000);
}
// handle cleanup and error messaging when the websocket connection closes
socket.onclose = function (e) {
	console.log(e.code);
	if (e.code != 1001) {
		if (e.reason) ServerMsg("Connection closed: "+e.reason+"\n");
		else ServerMsg("Connection closed.");
	}
	// stops the pings
	clearInterval(pingInterval)
};
// inform of and debug-log errors
socket.onerror = function (e) {
	ServerMsg("Connection error.");
	console.log(e);
};

// handle all messages coming from the server
socket.onmessage = function (e) {
	msg = JSON.parse(e.data);
	console.log(msg);
	// the default structure of the `msg` object is:
	// [ protocol_cmd, [arg1, arg2], kwargs_obj ]
	// thus, msg[0] is the cmdname, msg[1] is the args, and msg[2] is the kwargs
	// the default protocol_cmd of 'text' has the message as the first arg
	if (msg[0] == 'text') {
		message = msg[1][0];
		opts = msg[2];
		// pass channel messages to the correct channel
		if (msg[2].from_channel) {
			ChannelMsg(msg[1], String(msg[2].from_channel));
		}
		// this switch case assumes you add 'type' kwargs to your msg function
		// it would look like this: obj.msg(text=("a message", {'type': 'map'});
		else {
			switch(msg[2].type) {
				// these first cases REPLACE the normal message display
				case 'map':
					UpdateMap(message);
					break;
				case 'system':
					ServerMsg(message);
					break;
				case 'input':
					EchoMsg(message);
					break;
				// the following cases happen AS WELL AS the normal message display
				// so there is no `break` and multiple can theoretically be triggered by one message
				case 'traversal':
					SendFunc('get_map', '', {});
				// this one is just here to demonstrate having multiple, i didn't create a `get_status` inputfunc
				case 'dmg':
					SendFunc('get_status', '', {});
				default:
					GameMsg(message);
			}
		}
	}
	else if (msg[0] == 'prompt') {
		UpdateStatus(msg);
	}
	else if (msg[0] == 'chaninfo') {
		var joined = msg[1][2];
		if (joined)	AddChannel(msg[1][0], msg[1][1]);
		else RemoveChannel(msg[1][0]);
	}
	else if (msg[0] == 'map') {
		UpdateMap(msg[1][0]);
	}
	// load in the extra context numpad buttons
	else if (msg[0] == 'key_cmds') {
		// the command mapping is in the msg kwargs
		UpdateCmdKeys(msg[2]);
	}
	// any client functionality we want to trigger when an account logs in
	// this is received both when logging in via the webclient AND when opening the webclient while already logged in via the website
	else if (msg[0] == 'logged_in') {
		// ask the server for the list of channels we're on
		LoadChannels();
	}
};

// add clickability to Game tab
document.getElementById("_tab").addEventListener("click", swapChannel, false);

// handle primary text-box inputs to the client
input_box.addEventListener("keydown", function(e) {
	var channid = this.dataset.channel
	if (!channid) channid = '';
	var log_store_key = "cmd_log"+channid;

	// uses the enter key to send the message, but shift+enter to add newlines
	if (e.key == 'Enter' && !e.shiftKey) {
		e.preventDefault();
		var message = this.value;
		// get the channel name info, if there is any
		var chankey = '';
		if (channid) {
			channel = document.getElementById(channid +"_tab");
			if (channel && channel.dataset.channame) chankey = channel.dataset.channame;
		}

		if (String(message).length) {
			// add the entered text to the command cache
			LogSessionCmd(log_store_key, message);
			if (chankey.length)	message = chankey + " " + message;
			SendFunc('text', message, { 'type': 'input' });
			input_box.value = "";
			if (input_box.dataset.cmd_index) delete input_box.dataset.cmd_index;
		}
	}
	else if (e.key == 'ArrowUp') {
		// only go back through the history if the cursor is at the beginning
		if (this.selectionStart === 0) {
			NavCmdHistory(this, log_store_key, -1);
		}
	}
	else if (e.key == 'ArrowDown') {
		// only go forward through the history if the cursor is at the end
		if (this.selectionEnd === this.value.length) {
			NavCmdHistory(this, log_store_key, 1);
		}
	}
}, false);

// handles keypresses at the page level
document.addEventListener("keydown", (e) => {
	if (e.key === 'Escape' && input_box === document.activeElement) input_box.blur();
	else if (e.location == e.DOM_KEY_LOCATION_NUMPAD) {
		// handle context button keybindings
		KeybindPressEvent(e);
	}
	else if (input_box !== document.activeElement) {
		// automatically focus on the input area when you start typing
		if ( e.key && e.key.length === 1 && !(e.ctrlKey || e.altKey) ) {
			input_box.focus();
		}
	}
});
