from wykoj.constants import DB_URL

TORTOISE_CONFIG = {
    "connections": {
        "default": DB_URL
    },
    "apps": {
        "models": {
            "models": ["wykoj.models", "aerich.models"],
            "default_connection": "default"
        }
    }
}
