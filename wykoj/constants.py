JUDGE_HOST = "http://localhost:5000"
TEST_DB_URL = "sqlite://wykoj/test.db"

ALLOWED_LANGUAGES = {
    "Assembly": 45,
    "C": 50,
    "C++": 54,
    "C#": 51,
    "Elixir": 57,
    "F#": 87,
    "Go": 60,
    "Haskell": 61,
    "Java": 62,
    "JavaScript (Node.js)": 63,
    "Kotlin": 78,
    "Lua": 64,
    "Objective-C": 79,
    "Pascal": 67,
    "Perl": 85,
    "Python": 71,
    "R": 80,
    "Ruby": 72,
    "Rust": 73,
    "Scala": 81,
    "Swift": 83
}

SUBMISSION_STATUSES = [
    "Pending",
    "Compilation Error",
    "Accepted",
    "Partial Score",
    "Wrong Answer",
    "Runtime Error",
    "Time Limit Exceeded",
    "Memory Limit Exceeded",
    "System Error"
]
