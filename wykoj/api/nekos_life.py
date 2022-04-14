from aiohttp import ClientResponseError
import wykoj

class NekosLifeAPI:

    @staticmethod
    async def get_neko_url() -> str:
        # Return neko image link
        try:
            response = await wykoj.session.get("https://nekos.life/api/v2/img/neko")
        except ClientResponseError:
            # Take this image if there is response error
            return "https://cdn.nekos.life/neko/neko115.jpeg"
        return response.json()['url']
