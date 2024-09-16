from pytz import timezone

hkt = timezone("Asia/Hong_Kong")

# The value acts as a key and is used for communication with the judging backend
ALLOWED_LANGUAGES = {
    "C": "c",
    "C++": "cpp",
    "Python": "py",
    "OCaml": "ocaml",
}

LANGUAGE_LOGO = {
    "C": "c-original.svg",
    "C++": "cplusplus-original.svg",
    "Python": "python-original.svg",
    "OCaml": "ocaml-original.svg"
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
    SKIPPED = "sk"
    SYSTEM_ERROR = "se"


VERDICT_TRANS = {
    Verdict.PENDING: "Pending",
    Verdict.COMPILATION_ERROR: "Compilation Error",
    Verdict.ACCEPTED: "Accepted",
    Verdict.PARTIAL_SCORE: "Partial Score",
    Verdict.WRONG_ANSWER: "Wrong Answer",
    Verdict.RUNTIME_ERROR: "Runtime Error",
    Verdict.TIME_LIMIT_EXCEEDED: "Time Limit Exceeded",
    Verdict.MEMORY_LIMIT_EXCEEDED: "Memory Limit Exceeded",
    Verdict.SKIPPED: "Skipped",
    Verdict.SYSTEM_ERROR: "System Error"
}


class ContestStatus:
    PRE_PREP = "pre_prep"
    PREP = "prep"
    ONGOING = "ongoing"
    ENDED = "ended"
