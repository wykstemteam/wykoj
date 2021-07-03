import os

import ujson as json
from pytz import timezone

hkt = timezone("Asia/Hong_Kong")

with open(os.path.join(os.getcwd(), "wykoj", "config.json")) as f:
    config = json.load(f)

JUDGE_HOST = config["JUDGE_HOST"]
DB_URL = config["DB_URL"]
TEST_DB_URL = config["TEST_DB_URL"]

ALLOWED_LANGUAGES = {
    "C": "c",
    "C++": "cpp",
    "Python": "py",
    "Pascal": "pas",
    "OCaml": "ocaml"
}

ALLOWED_LANGUAGES_TRANS = {v: k for k, v in ALLOWED_LANGUAGES.items()}

VERDICT_TRANS = {
    "pe": "Pending",
    "ce": "Compilation Error",
    "ac": "Accepted",
    "ps": "Partial Score",
    "wa": "Wrong Answer",
    "re": "Runtime Error",
    "tle": "Time Limit Exceeded",
    "mle": "Memoery Limit Exceeded",
    "se": "System Error"
}

class Verdict:
    PENDING = "pe"
    COMPILATION_ERROR = "ce"
    ACCEPTED = "ac"
    PARTIAL_SCORE = "ps"
    WRONG_ANSWER = "wa"
    RUNTIME_ERROR = "re"
    TIME_LIMIT_EXCEEDED = "tle"
    MEMORY_LIMIT_EXCEEDED = "mle"
    SYSTEM_ERROR = "se"
