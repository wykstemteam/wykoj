import wykoj

class NekosLifeAPI:

    @staticmethod
    async def get_neko_url() -> str:
        # Return neko image link
        response = await wykoj.session.get("https://nekos.life/api/v2/img/neko")
        return response.json()['url']
