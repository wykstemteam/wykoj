import asyncio
import json
import logging
import random

logger = logging.getLogger(__name__)


class NekosBestAPI:
    @staticmethod
    async def get_url() -> str:
        url = "https://nekos.best/api/v2/" + random.choice(["waifu", "neko", "kitsune"])
        try:
            # aiohttp gets 403'd by nekos.best's Cloudflare bot protection (TLS/HTTP
            # fingerprinting), even with matching headers and from the same IP that
            # curl succeeds from. Shell out to curl instead, which isn't blocked.
            proc = await asyncio.create_subprocess_exec(
                "curl", "-sS", "-A", "wykojBot/1.0 (https://oj.wyk.edu.hk/)", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode())
            data = json.loads(stdout)
        except Exception as e:
            logger.error(
                f"Error in fetching from nekos.best API:\n{e.__class__.__name__}: {str(e)}"
            )
            return "https://nekos.best/api/v2/neko/0378.png"

        return data["results"][0]["url"]
