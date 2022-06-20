import os
from dataclasses import dataclass
from itertools import count
from typing import Any, Dict, List, Optional

import aiofiles
import ujson as json
from aiocache import cached

from wykoj.constants import ALLOWED_LANGUAGES


@dataclass(frozen=True)
class SampleTestCase:
    input: str
    output: str
    description: Optional[str] = None


async def read_file(path: str) -> str:
    async with aiofiles.open(path, encoding="utf-8") as f:
        return await f.read()


def get_files(task_id: str) -> List[str]:
    dir_path = os.path.join("test_cases", task_id)
    if not os.path.isdir(dir_path):
        return []
    return [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]


class TestCaseAPI:
    @staticmethod
    @cached(ttl=5)
    async def get_config(task_id: str) -> Optional[Dict[str, Any]]:
        dir_path = os.path.join("test_cases", task_id)
        try:
            config = json.loads(await read_file(os.path.join(dir_path, "config.json")))
            assert "grader" in config and "batched" in config
            if config["batched"]:
                assert "points" in config and sum(config["points"]) == 100
            if config["grader"]:
                assert "grader_file" in config and "grader_language" in config
                assert config["grader_language"] in ALLOWED_LANGUAGES
                config["grader_source_code"] = await read_file(
                    os.path.join(dir_path, config["grader_file"])
                )
            return config
        except (FileNotFoundError, ValueError, AssertionError):
            # ValueError for ujson, JSONDecodeError for json
            return None

    @staticmethod
    @cached(ttl=5)
    async def check_test_cases_ready(task_id: str) -> bool:
        config = await TestCaseAPI.get_config(task_id)
        if not config:
            return False

        files = get_files(task_id)
        if config["grader"]:
            return "1.1.in" in files
        else:
            return "1.1.in" in files and "1.1.out" in files

    @staticmethod
    @cached(ttl=5)
    async def get_sample_test_cases(task_id: str) -> List[SampleTestCase]:
        dir_path = os.path.join("test_cases", task_id)
        cases = []
        files = get_files(task_id)

        for i in count(1):
            if f"0.{i}.in" not in files or f"0.{i}.out" not in files:
                break

            case_in = await read_file(os.path.join(dir_path, f"0.{i}.in"))
            case_out = await read_file(os.path.join(dir_path, f"0.{i}.out"))
            if case_in.endswith("\n"):
                case_in = case_in[:-1]
            if case_out.endswith("\n"):
                case_out = case_out[:-1]
            # Replace \n with <br> to be displayed correctly in HTML
            case_in = case_in.replace("\n", "<br>")
            case_out = case_out.replace("\n", "<br>")

            if f"0.{i}.txt" in files:
                desc = await read_file(os.path.join(dir_path, f"0.{i}.txt"))
            else:
                desc = None

            cases.append(SampleTestCase(input=case_in, output=case_out, description=desc))

        return cases
