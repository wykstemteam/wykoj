import os.path

import ujson as json

from wykoj.constants import TEST_DB_URL

with open(os.path.join(__file__, os.path.pardir, "config.json")) as f:
    config = json.load(f)

NORMAL = {
    "connections": {
        "default": config["DB_URL"]
    },
    "apps": {
        "models": {
            "models": ["wykoj.models"],
            "default_connection": "default"
        }
    }
}

TEST = {
    "connections": {
        "default": TEST_DB_URL
    },
    "apps": {
        "models": {
            "models": ["wykoj.models"],
            "default_connection": "default"
        }
    }
}

TEST_MIGRATION = {
    "connections": {
        "default": TEST_DB_URL
    },
    "apps": {
        "models": {
            "models": ["wykoj.models", "aerich.models"],
            "default_connection": "default"
        }
    }
}
