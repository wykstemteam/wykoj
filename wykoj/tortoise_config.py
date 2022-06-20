import ujson as json

with open("config.json") as f:
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
