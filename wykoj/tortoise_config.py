import os.path

import ujson as json

from wykoj.constants import DB_URL, TEST_DB_URL

NORMAL = {
    "connections": {
        "default": DB_URL
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
