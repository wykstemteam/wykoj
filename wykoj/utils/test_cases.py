import asyncio
import os
import re
from itertools import count
from typing import Dict, Any, Optional, List, Tuple, Union

import aiofiles
import ujson as json
from aiocache import cached
from quart import current_app


async def read_file(path: str) -> str:
    async with aiofiles.open(path, encoding="utf-8") as f:
        return await f.read()


@cached(ttl=60)
async def get_config(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        config = json.loads(await read_file(
            os.path.join(current_app.root_path, "test_cases", task_id, "config.json")
        ))
        assert "grader" in config and "batched" in config
        if config["batched"]:
            assert "points" in config and sum(config["points"]) == 100
        if config["grader"]:
            config["grader_code"] = await read_file(
                os.path.join(current_app.root_path, "test_cases", task_id, "grader.py")
            )
        return config
    except (FileNotFoundError, ValueError, AssertionError):  # ValueError for ujson, JSONDecodeError for json
        return None


@cached(ttl=60)
async def get_sample_test_cases(task_id: str) -> List[Tuple[str, str]]:
    cases = []
    try:
        files = set(f for f in os.listdir(os.path.join(current_app.root_path, "test_cases", task_id))
                    if re.match(r"^0\.\d+\.((in)|(out))$", f))
    except FileNotFoundError:  # When no directory name matches task id
        return cases
    for i in count(1):
        if f"0.{i}.in" in files and f"0.{i}.out" in files:
            # Replace \n with <br> to be displayed correctly in HTML
            case_in = await read_file(os.path.join(current_app.root_path, "test_cases", task_id, f"0.{i}.in"))
            case_out = await read_file(os.path.join(current_app.root_path, "test_cases", task_id, f"0.{i}.out"))
            case_in = case_in.replace("\n", "<br>")
            case_out = case_out.replace("\n", "<br>")
            cases.append((case_in, case_out))
        else:
            break
    return cases


@cached(ttl=60)  # TODO: Maybe change return format
async def get_test_cases(task_id: str) -> Union[List[List[str]], List[List[Tuple[str, str]]]]:
    cases = []
    config = await get_config(task_id)
    if not config:
        return cases
    # No need to try-except for FileNotFoundError in later code since handled in get_config()
    if config["grader"]:
        files = set(f for f in os.listdir(os.path.join(current_app.root_path, "test_cases", task_id))
                    if re.match(r"^[1-9]\d*\.\d+\.in$", f))
    else:
        files = set(f for f in os.listdir(os.path.join(current_app.root_path, "test_cases", task_id))
                    if re.match(r"^[1-9]\d*\.\d+\.((in)|(out))$", f))
    if config["grader"]:
        for i in count(1):
            cases.append([])
            for j in count(1):
                if f"{i}.{j}.in" in files:
                    case_in = await read_file(
                        os.path.join(current_app.root_path, "test_cases", task_id, f"{i}.{j}.in")
                    )
                    cases[-1].append(case_in)
                elif j == 1:
                    del cases[-1]
                    return cases
                else:
                    break
    else:
        for i in count(1):
            cases.append([])
            for j in count(1):
                if f"{i}.{j}.in" in files and f"{i}.{j}.out" in files:
                    case_in = await read_file(
                        os.path.join(current_app.root_path, "test_cases", task_id, f"{i}.{j}.in")
                    )
                    case_out = await read_file(
                        os.path.join(current_app.root_path, "test_cases", task_id, f"{i}.{j}.out")
                    )
                    cases[-1].append((case_in, case_out))
                elif j == 1:
                    del cases[-1]
                    return cases
                else:
                    break
