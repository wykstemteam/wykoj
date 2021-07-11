from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List

from aiocache import cached
from aiohttp import ClientResponseError
from chess import pgn
from pytz import utc

import wykoj


@dataclass(order=True, unsafe_hash=True)
class ChessComChessGame:
    game_id: int = field(hash=True)
    rated: bool = field(compare=False)
    time_class: str = field(compare=False)
    time_control: str = field(compare=False)
    pgn: str = field(compare=False)
    white_username: str = field(compare=False)
    white_rating: int = field(compare=False)
    # white_result: str = field(compare=False)
    black_username: str = field(compare=False)
    black_rating: int = field(compare=False)
    # black_result: str = field(compare=False)

    termination: str = field(init=False, compare=False)
    time: datetime = field(init=False, compare=False)
    url: str = field(init=False, compare=False)

    def read_data_from_pgn(self) -> None:
        game = pgn.read_game(StringIO(self.pgn))
        self.termination = game.headers["Termination"]
        self.time = utc.localize(
            datetime.strptime(
                game.headers["UTCDate"] + " " + game.headers["UTCTime"], "%Y.%m.%d %H:%M:%S"
            )
        )
        self.url = game.headers["Link"]

    @property
    def game_format(self) -> str:
        s = "Rated" if self.rated else "Unrated"
        s += f" {self.time_class.capitalize()}"
        if "+" in self.time_control:
            base, inc = [int(i) for i in self.time_control.split("+")]
        else:
            base = int(self.time_control)
            inc = 0

        base /= 60
        if base.is_integer():
            base_s = format(base, ".0f")
        else:
            base_s = format(base, ".1f")

        return s + f" ({base_s}+{inc})"


class ChessComAPI:
    """Wrapper for chess.com API."""
    @staticmethod
    @cached(ttl=3 * 60)
    async def username_exists(username: str) -> bool:
        try:
            await wykoj.session.get(f"https://api.chess.com/pub/player/{username}")
        except ClientResponseError as e:
            if e.status == 404:  # Not Found
                return False
            else:
                raise
        else:
            return True

    @staticmethod
    @cached(ttl=3 * 60)
    async def get_recent_games(username: str) -> List[ChessComChessGame]:
        """Retrieve games played by a user in the recent 2 months."""
        now = datetime.now(utc)
        cur_month = (now.year, now.month)
        last_month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        urls = [
            f"https://api.chess.com/pub/player/{username}/games/{last_month[0]}/{last_month[1]:02}",
            f"https://api.chess.com/pub/player/{username}/games/{cur_month[0]}/{cur_month[1]:02}"
        ]
        games = []

        try:
            for url in urls:
                async with wykoj.session.get(url) as resp:
                    data = await resp.json()
                    for raw_game in data["games"]:
                        game = ChessComChessGame(
                            game_id=int(raw_game["url"].rsplit(sep="/", maxsplit=1)[1]),
                            rated=raw_game["rated"],
                            time_class=raw_game["time_class"],
                            time_control=raw_game["time_control"],
                            pgn=raw_game["pgn"],
                            white_username=raw_game["white"]["username"],
                            white_rating=raw_game["white"]["rating"],
                            # white_result=raw_game["white"]["result"],
                            black_username=raw_game["black"]["username"],
                            black_rating=raw_game["black"]["rating"],
                            # black_result=raw_game["black"]["result"]
                        )
                        games.append(game)
        except ClientResponseError as e:
            if e.status != 404:  # Ignore Not Found, [] is returned
                raise

        return games
