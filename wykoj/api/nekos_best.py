import random

from aiohttp import ClientResponseError

import wykoj


class NekosBestAPI:
    @staticmethod
    async def get_url() -> str:
        try:
            url = random.choice([
                "https://nekos.best/api/v2/waifu",
                "https://nekos.best/api/v2/neko",
                "https://nekos.best/api/v2/kitsune"
            ])
            response = await wykoj.session.get(url)
        except ClientResponseError:
            return "https://nekos.best/api/v2/neko/0378.png"

        data = await response.json()
        return data["results"][0]["url"]
