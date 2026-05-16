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

# Websockets are fragile in certain situations, such as remote mobile access, as the connection
# will fully break every time your connection changes routes (such as switching cell towers).
# Server-Sent Events are more robust for these scenarios, as the game connection stays "active"
# even when the network connection blips.
# As such, I've implemented a mod layer that hijacks the AJAX fallback endpoint to provide SSE
# If you want to use the Server-Sent Events implementation instead of websockets,
# uncomment these lines
#WEBSOCKET_CLIENT_ENABLED = False
#SSE_ENABLED = True
#AJAX_CLIENT_CLASS = "server.portal.sse_hybrid.HybridSSEHub"

# CACHE BUSTERRRR
TEMPLATES[0]["OPTIONS"]["context_processors"].append("web.custom_context.extra_context")

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
