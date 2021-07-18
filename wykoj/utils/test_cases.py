import asyncio
import os
import re
from dataclasses import dataclass
from itertools import count
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import aiofiles
import ujson as json
from aiocache import cached

import wykoj


async def read_file(path: str) -> str:
    async with aiofiles.open(path, encoding="utf-8") as f:
        return await f.read()


def get_files(task_id: str) -> List[str]:
    dir = os.path.join(wykoj.root_path, "test_cases", task_id)
    if not os.path.isdir(dir):
        return False
    return [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]


@cached(ttl=10)
async def get_config(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        config = json.loads(
            await read_file(os.path.join(wykoj.root_path, "test_cases", task_id, "config.json"))
        )
        assert "grader" in config and "batched" in config
        if config["batched"]:
            assert "points" in config and sum(config["points"]) == 100
        if config["grader"]:
            config["grader_code"] = await read_file(
                os.path.join(wykoj.root_path, "test_cases", task_id, "grader.py")
            )
        return config
    except (FileNotFoundError, ValueError, AssertionError):
        # ValueError for ujson, JSONDecodeError for json
        return None


@cached(ttl=10)
async def get_sample_test_cases(task_id: str) -> List[Tuple[str, str]]:
    cases = []
    files = get_files(task_id)

    for i in count(1):
        if f"0.{i}.in" in files and f"0.{i}.out" in files:
            case_in = await read_file(
                os.path.join(wykoj.root_path, "test_cases", task_id, f"0.{i}.in")
            )
            case_out = await read_file(
                os.path.join(wykoj.root_path, "test_cases", task_id, f"0.{i}.out")
            )
            if case_in.endswith("\n"):
                case_in = case_in[:-1]
            if case_in.endswith("\n"):
                case_out = case_out[:-1]
            # Replace \n with <br> to be displayed correctly in HTML
            case_in = case_in.replace("\n", "<br>")
            case_out = case_out.replace("\n", "<br>")
            cases.append((case_in, case_out))
        else:
            break

    return cases


@cached(ttl=10)
async def check_test_cases_ready(task_id: str) -> bool:
    config = await get_config(task_id)
    if not config:
        return False

    files = get_files(task_id)
    if config["grader"]:
        return "1.1.in" in files
    else:
        return "1.1.in" in files and "1.1.out" in files


@dataclass(frozen=True)
class TestCase:
    subtask: int
    test_case: int
    input: str
    output: str = None

    def json(self):
        data = {"subtask": self.subtask, "test_case": self.test_case, "input": self.input}
        if self.output:
            data["output"] = self.output
        return json.dumps(data)


async def iter_test_cases(task_id: str) -> AsyncIterator[TestCase]:
    """Returns an async generator instead of a list because there can be many large test cases."""
    config = await get_config(task_id)

    files = get_files(task_id)
    if config["grader"]:
        for i in count(1):
            for j in count(1):
                if f"{i}.{j}.in" in files:
                    case_in = await read_file(
                        os.path.join(wykoj.root_path, "test_cases", task_id, f"{i}.{j}.in")
                    )
                    yield TestCase(i, j, case_in)
                elif j == 1:
                    return
                else:
                    break
    else:
        for i in count(1):
            for j in count(1):
                if f"{i}.{j}.in" in files and f"{i}.{j}.out" in files:
                    case_in = await read_file(
                        os.path.join(wykoj.root_path, "test_cases", task_id, f"{i}.{j}.in")
                    )
                    case_out = await read_file(
                        os.path.join(wykoj.root_path, "test_cases", task_id, f"{i}.{j}.out")
                    )
                    yield TestCase(i, j, case_in, case_out)
                elif j == 1:
                    return
                else:
                    break
