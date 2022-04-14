from aiohttp import ClientResponseError

import wykoj


class NekosLifeAPI:
    @staticmethod
    async def get_neko_url() -> str:
        try:
            response = await wykoj.session.get("https://nekos.life/api/v2/img/neko")
        except ClientResponseError:
            return "https://cdn.nekos.life/neko/neko115.jpeg"
        return (await response.json())["url"]
