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
- The up and down arrow key can be used in the input box to scroll through your command history. Even between page reloads!
- Built-in channel tabs in your main game view. Automatically loads any channels you're subscribed to on logging in, with an easy-to-integrate `msg` command to let your game's channel sub/unsub automatically add or remove client tabs.
- Comes pre-set with a map panel and a custom inputfunc to let your client fetch its own map updates. No more worries about keeping the webclient updated without spamming your telnet players!
- Supports custom keybindings with on-screen buttons, so you can map any commands you want to the numpad. By default, it's set up just for the 1-9 buttons, but it can easily be extended to the full keypad.
- Clean, straightforward, and easily customizable styling!
- Thoroughly commented so you can easily figure out exactly what to mess with to get it to work *juuust* the way you want.
- Did I mention it's only 14KB?

### Not yet implemented....
- Mobile view
- Downloadable log files
- Providing the full-keypad alternate bindings code
- A slightly nicer-looking default UI would be nice

## Installation

The project files are laid out in exactly the folder structure and locations that they need to be in a default Evennia gamedir structure. Just download the files, paste them into your game directory, and restart Evennia. You're all set!

#### Wait! But I already customized some of those files myself!

Not to worry! You probably want to replace anything this project includes in the `web` directory, but the rest can be integrated into your own game files just fine.
