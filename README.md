# EveLite

#### a lightweight webclient for Evennia

*NOTE: This is fully usable, but still a bit unpolished. Check out the Not Yet Implemented section to see what's still missing.*

### Try out EveLite if...

- You want a functional and lightweight webclient.
- You want to customize your webclient to match your game's specific needs and style.
- You looked at the feature list below and you really want one of them but you don't want to write it yourself.
- You're not actually making a game in Evennia, you just want a nice websocket-based MU\* client for what you *are* making.

### Stick with Evennia's webclient if...

- You want to let your players customize the client themselves.
- You don't really want to mess with setting up a webclient at all.

## Features
- It's super lightweight! The entire client is driven by a single *14KB* Javascript file.
- Clean, straightforward, and easily customizable styling!
- Thoroughly commented JavaScript to make customizing your webclient's functionality as easy as possible.
- The up and down arrow key can be used in the input box to scroll through your command history. Even across page reloads!
- Built-in channel tabs in your main game view. Automatically loads any channels you're subscribed to on logging in, with an easy-to-integrate `msg` command to let your game's channel sub/unsub automatically add or remove client tabs.
- Export your game and channel logs to a file with the click of a button.
- Comes pre-set with a map panel and a custom inputfunc to let your client fetch its own map updates. No more worries about keeping the webclient updated without spamming your telnet players!
- Supports custom keybindings with on-screen buttons, so you can map any commands you want to the numpad. By default, it's set up just for the 1-9 buttons, but it can easily be extended to the full keypad.
- Did I mention it's only 14KB?

### Not yet implemented....
- Mobile view
- Ability to clear the browser's log storage
- Providing the full-keypad alternate bindings code
- A slightly nicer-looking default UI would be nice

## Installation

The project files are laid out in exactly the folder structure and locations that they need to be in a default Evennia gamedir structure. Just download the files, paste them into your game directory, and restart Evennia. You're all set!

#### Wait! But I already customized some of those files myself!

Not to worry! You probably want to replace anything this project includes in the `web` directory, but the rest can be integrated into your own game files just fine.

## Using With Your Game

Aside from the client's own automatic features, it's set up to make integrating the rest of its features as painless as possible.

### Maps

EveLite supports three different ways of getting an updated map from your game server - the server can send either an "in-band" or an "out-of-band" message, or the webclient can request a map update directly. 

#### `session.msg( ( map_str, { 'type': 'map' }) )`
Sending the map string as an ordinary `text` message with a custom option of `'type': 'map'` is the "in-band" method. This kind of `msg` call on your server will be displayed by other clients, such as telnet, as a normal incoming text message. EveLite, however, will see the 'map' value in the options and update the map pane.

If you have a `map` command that displays the area map, this is how you'd want to send it.

#### `session.msg( map=map_str )`
Using the custom msg command of `map` directly will send the map string entirely "out-of-band". EveLite will immediately recognize it and update the map pane. Other clients, such as telnet, will only receive and process it if they have some kind of OOB processor that recognizes a `map` command. This is the message type which the "map on request" third method receives.

#### webclient request
The provided webclient JavaScript will automatically request a map update when it receives a text msg `type` option of `traversal`. This message type isn't used anywhere in core Evennia, so you can implement it yourself or change/remove it entirely.

With this method, when the webclient gets a message of the right type - even though the message itself didn't have a map included - it sends a request to the server asking for an OOB map update.

### Channel Tabs

While the client does automatically load in any connected channels as soon as your account connects, it can't know that your account has subbed or unsubbed to any channels on the server - unless you tell it. Fortunately, that's easy!

EveLite recognizes a custom out-of-band `msg` command of `chaninfo`, which it can then parse to tell if it needs to add, update, or remove a channel tab. The syntax for sending this message is:
```python
session.msg( chaninfo=(channel_id, channel_name, subbed_status) )
```

For example, you could add a line at the end of `Channel.post_join_channel`, saying `joiner.msg( chaninfo=(self.id, self.key, True) )` and as soon as the webclient receives that notification, it will set up the tab for that channel. If the third value is `False`, it'll remove the tab instead.

### Keybindings

If you want to make use of having contextual commands with on-screen or numpad buttons, you'll need to send them to the client from the server. The client uses a custom `msg` command, `key_cmds`. Where and how to send this information to the client depends on what kind of commands you want to have, of course, but here's some examples!

```py
# the basic cardinal directions and 'look' in a + configuration
chara.msg( key_cmds=('', { '8': 'north', '2': 'south', '4': 'west', '6': 'east', '5': 'look' }) )

# a simple confirmation dialog
session.msg( key_cmds=('', { '1': 'Yes', '2': 'No' }) )

# RPSLK
chara.msg( key_cmds=('', { '1': 'ROCK', '3': 'PAPER', '5': 'SCISSORS', '7': 'LIZARD', '9': 'SPOCK`' }) )
```

When the client receives a `key_cmds` update, any keys that aren't listed in the mapping is turned off. e.g. With the simple confirmation dialog example, the numpad keys for 3 through 9 will behave as normal numeric keys, and there will be no visible or clickable buttons for them.
