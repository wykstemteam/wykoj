import logging
import random

from quart import current_app

logger = logging.getLogger(__name__)


class NekosBestAPI:
    @staticmethod
    async def get_url() -> str:
        try:
            headers = {
                "User-Agent": "wykojBot/1.0 (https://oj.wyk.edu.hk/)"
            }
            url = "https://nekos.best/api/v2/" + random.choice(["waifu", "neko", "kitsune"])
            response = await current_app.session.get(url, headers=headers)
        except Exception as e:
            logger.error(
                f"Error in fetching from nekos.best API:\n{e.__class__.__name__}: {str(e)}"
            )
            return "https://nekos.best/api/v2/neko/0378.png"

        data = await response.json()
        return data["results"][0]["url"]
