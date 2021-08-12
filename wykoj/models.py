import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional, Union

from aiocache import cached
from bs4 import BeautifulSoup
from pytz import utc
from quart_auth import AuthUser
from tortoise import Model, fields
from tortoise.functions import Count


class Sidebar(Model):
    content = fields.TextField()


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(30, unique=True)
    password = fields.CharField(200)
    name = fields.CharField(30)
    english_name = fields.CharField(120)
    chesscom_username = fields.CharField(30, null=True)  # chess.com usernames <= 25 chars
    lichess_username = fields.CharField(30, null=True)  # lichess usernames <= 20 chars
    language = fields.CharField(30, default="C++")
    # To improve image quality, we store a larger size than displayed
    # i.e. 40 x 40 -> 20 x 20; 160 x 160 -> 120 x 120
    img_40 = fields.CharField(40, default="default_40.png")
    img_160 = fields.CharField(40, default="default_160.png")
    can_edit_profile = fields.BooleanField(default=True)
    is_student = fields.BooleanField()
    is_admin = fields.BooleanField()
    solves = fields.IntField(default=0)
    authored_tasks: fields.ManyToManyRelation["Task"]
    submissions: fields.ReverseRelation["Submission"]
    contest_participations: fields.ReverseRelation["ContestParticipation"]

    class Meta:
        ordering = ("id", )


class UserWrapper(AuthUser):
    # Quart-Auth suggests creating asynchronous properties for every attribute
    # That's just unacceptable so we make a wrapper

    def __init__(self, auth_id: int) -> None:
        super().__init__(auth_id)
        self.id: int = auth_id  # This is used in Contest.is_contestant
        self.user: Optional[User] = None
        self._resolved: bool = False

    # These methods allow access to and modification of User properties through UserWrapper

    def __getattr__(self, item: Any) -> Any:
        try:
            return self.__getattribute__(item)
        except AttributeError:
            if item == "user":
                raise
            return getattr(self.user, item)

    def __setattr__(self, key: str, value: Any) -> None:
        if getattr(self, "user", None) and key in self.user.__dict__:
            self.user.__setattr__(key, value)
        else:
            self.__dict__[key] = value

    async def resolve(self) -> None:
        """Fetch user object from database."""
        if self._resolved or self._auth_id is None:
            return
        self.user = await User.filter(id=self._auth_id).first()
        self._resolved = True

    @property
    def is_admin(self) -> bool:
        return bool(self.user and self.user.is_admin)


class Task(Model):
    id = fields.IntField(pk=True)
    task_id = fields.CharField(10, unique=True)
    title = fields.CharField(120)
    is_public = fields.BooleanField()
    authors: fields.ManyToManyRelation[User] = fields.ManyToManyField(
        "models.User", related_name="authored_tasks"
    )
    content = fields.TextField()
    time_limit = fields.DecimalField(max_digits=5, decimal_places=3)  # s
    memory_limit = fields.IntField()
    solves = fields.IntField(default=0)
    # Sample test cases and test cases are stored locally inside test_cases/
    submissions: fields.ReverseRelation["Submission"]
    contests: fields.ManyToManyRelation["Contest"]

    class Meta:
        ordering = ("task_id", )

    @property
    @cached(ttl=1)
    async def attempts(self) -> int:
        return (
            await Submission.annotate(count=Count("author_id", distinct=True)
                                      ).filter(task_id=self.id).values("count")
        )[0]["count"]

    @property
    def ogp_preview(self) -> str:
        """Task preview for OGP. Returns the first paragraph of the task statement in plain text."""
        soup = BeautifulSoup(self.content, "html.parser")
        # Get the first paragraph
        text = soup.p.get_text()
        # Replace MathJax $ and $$ tags with surrounding spaces, while not replacing \$
        text = re.sub(r"\s*(?<!\\)\${1,2}\s*", " ", text)
        # Replace line breaks and indents with just one space
        text = re.sub(r"\s+", " ", text.strip())
        return text


class Contest(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(120)
    is_public = fields.BooleanField()
    # Public = Contest is open to all users and users can join the contest themselves on the contest page
    start_time = fields.DatetimeField()
    duration = fields.IntField()  # minutes
    tasks: fields.ManyToManyRelation[Task] = fields.ManyToManyField("models.Task")
    participations: fields.ReverseRelation["ContestParticipation"]
    submissions: fields.ReverseRelation["Submission"]

    class Meta:
        ordering = ("-id", )

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration)

    async def get_contestants(self) -> List[User]:
        return [
            cp.contestant for cp in await self.participations.all().prefetch_related("contestant")
        ]

    async def get_contestants_no(self) -> int:
        return await self.participations.all().count()

    @cached(ttl=1)
    async def is_contestant(self, user: Union[User, UserWrapper]) -> bool:
        return user.id is not None and user.id in [
            contestant.id for contestant in await self.get_contestants()
        ]

    @property
    def status(self) -> str:
        now = datetime.now(utc)
        if now < self.start_time - timedelta(minutes=1):
            return "pre_prep"
        if self.start_time - timedelta(minutes=1) <= now < self.start_time:
            return "prep"
        if self.start_time <= now < self.end_time:
            return "ongoing"
        return "ended"


class ContestTaskPoints(Model):
    task: fields.ForeignKeyRelation["Task"] = fields.ForeignKeyField("models.Task")
    _points = fields.TextField()
    participation: fields.ForeignKeyRelation["ContestParticipation"] = fields.ForeignKeyField(
        "models.ContestParticipation", related_name="task_points"
    )

    class Meta:
        unique_together = (("task", "participation"), )

    @property
    def points(self) -> List[Union[int, float]]:
        p = []
        for i in self._points.split(","):
            f = float(i)
            p.append(int(f) if f.is_integer() else f)
        return p

    @points.setter
    def points(self, value: List[Decimal]) -> None:
        self._points = ",".join([str(i) for i in value])

    @property
    def total_points(self) -> float:
        return float(sum(self.points))


class ContestParticipation(Model):
    contest: fields.ForeignKeyRelation[Contest] = fields.ForeignKeyField(
        "models.Contest", related_name="participations"
    )
    contestant: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="contest_participations"
    )
    task_points: fields.ReverseRelation[ContestTaskPoints]

    class Meta:
        unique_together = (("contest", "contestant"), )
        ordering = ("id", )

    @property
    @cached(ttl=3)
    async def total_points(self) -> int:
        return sum(ctp.total_points for ctp in await self.task_points)


class TestCaseResult(Model):
    class Meta:
        ordering = ("submission_id", "subtask", "test_case")

    subtask = fields.IntField()
    test_case = fields.IntField()
    verdict = fields.CharField(5)
    score = fields.DecimalField(max_digits=6, decimal_places=3, default=0)
    time_used = fields.DecimalField(max_digits=5, decimal_places=3)  # s
    memory_used = fields.DecimalField(max_digits=7, decimal_places=3)  # MB
    submission: fields.ForeignKeyRelation["Submission"] = fields.ForeignKeyField(
        "models.Submission", related_name="test_case_results"
    )


class Submission(Model):
    id = fields.IntField(pk=True)
    time = fields.DatetimeField()
    task: fields.ForeignKeyRelation[Task] = fields.ForeignKeyField(
        "models.Task", related_name="submissions"
    )
    author: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="submissions"
    )
    language = fields.CharField(30)
    source_code = fields.TextField()
    verdict = fields.CharField(5, default="pe")
    score = fields.DecimalField(max_digits=6, decimal_places=3, default=0)
    _subtask_scores = fields.TextField(null=True)
    time_used = fields.DecimalField(max_digits=5, decimal_places=3, null=True)  # s
    memory_used = fields.DecimalField(max_digits=7, decimal_places=3, null=True)  # MB
    test_case_results: fields.ReverseRelation[TestCaseResult]
    first_solve = fields.BooleanField(default=False)
    contest: fields.ForeignKeyNullableRelation[Contest] = fields.ForeignKeyField(
        "models.Contest", related_name="submissions", on_delete=fields.SET_NULL, null=True
    )

    class Meta:
        ordering = ("-id", )

    @property
    def subtask_scores(self) -> List[Union[int, float]]:
        if not self._subtask_scores:
            return None

        p = []
        for i in self._subtask_scores.split(","):
            f = float(i)
            p.append(int(f) if f.is_integer() else f)
        return p

    @subtask_scores.setter
    def subtask_scores(self, value: List[Decimal]) -> None:
        self._subtask_scores = ",".join([str(i) for i in value])
