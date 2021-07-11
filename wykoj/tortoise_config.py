import os

import ujson as json

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    config = json.load(f)

DB_URI = config["DB_URI"]

TORTOISE_CONFIG = {
    "connections": {
        "default": DB_URI
    },
    "apps": {
        "models": {
            "models": ["wykoj.models", "aerich.models"],
            "default_connection": "default"
        }
    }
}
