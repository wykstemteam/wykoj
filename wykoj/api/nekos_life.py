import random

from aiohttp import ClientResponseError

import wykoj


class NekosLifeAPI:
    @staticmethod
    async def get_neko_url() -> str:
        try:
            url = random.choice([
                "https://nekos.life/api/v2/img/neko",
                "https://nekos.life/api/v2/img/fox_girl"
            ])
            response = await wykoj.session.get(url)
        except ClientResponseError:
            return "https://cdn.nekos.life/neko/neko115.jpeg"
        return (await response.json())["url"]
