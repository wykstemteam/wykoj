import logging
import random

import wykoj

logger = logging.getLogger(__name__)


class NekosBestAPI:
    @staticmethod
    async def get_url() -> str:
        try:
            url = "https://nekos.best/api/v2/" + random.choice(["waifu", "neko", "kitsune"])
            response = await wykoj.session.get(url)
        except Exception as e:
            logger.error(
                f"Error in fetching from nekos.best API:\n{e.__class__.__name__}: {str(e)}"
            )
            return "https://nekos.best/api/v2/neko/0378.png"

        data = await response.json()
        return data["results"][0]["url"]
