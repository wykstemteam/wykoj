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

# Keyed by the leading letter of a task ID, see admin guide for details
TASK_CATEGORIES = {
    "A": "Algorithm Training",
    "B": "Basic Programming Exercises",
    "C": "Contests",
    "L": "Lecture Notes",
    "P": "Practice Problems",
    "T": "Team Formation Test",
    "W": "WYOI Problems",
    "Z": "WYHK Problems",
}

# URL slug for /tasks/<task_type>, the first word of the category name in lowercase
TASK_CATEGORY_SLUGS = {letter: name.split()[0].lower() for letter, name in TASK_CATEGORIES.items()}
TASK_CATEGORY_LETTERS = {slug: letter for letter, slug in TASK_CATEGORY_SLUGS.items()}


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
    SKIPPED = "sk"


VERDICT_TRANS = {
    Verdict.PENDING: "Pending",
    Verdict.COMPILATION_ERROR: "Compilation Error",
    Verdict.ACCEPTED: "Accepted",
    Verdict.PARTIAL_SCORE: "Partial Score",
    Verdict.WRONG_ANSWER: "Wrong Answer",
    Verdict.RUNTIME_ERROR: "Runtime Error",
    Verdict.TIME_LIMIT_EXCEEDED: "Time Limit Exceeded",
    Verdict.MEMORY_LIMIT_EXCEEDED: "Memory Limit Exceeded",
    Verdict.SYSTEM_ERROR: "System Error",
    Verdict.SKIPPED: "Skipped"
}


class ContestStatus:
    PRE_PREP = "pre_prep"
    PREP = "prep"
    ONGOING = "ongoing"
    ENDED = "ended"
