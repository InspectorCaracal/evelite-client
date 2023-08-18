r"""
Evennia settings file.
"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "EveLite"

# lightly customized websocket protocol to play better with the custom client
WEBSOCKET_PROTOCOL_CLASS = "server.portal.websocket.WebSocketClient"

# CACHE BUSTERRRR
TEMPLATES[0]["OPTIONS"]["context_processors"].append("web.custom_context.extra_context")

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
