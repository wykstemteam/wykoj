import asyncio
from datetime import timedelta
from decimal import Decimal

from flask_wtf.file import FileAllowed, FileField
from pytz import utc
from wtforms import (
    BooleanField, DateTimeField, DecimalField, HiddenField, IntegerField,
    PasswordField, SelectField, StringField, SubmitField, TextAreaField
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Regexp, ValidationError
from wtforms.widgets import NumberInput

from wykoj.api import ChessComAPI
from wykoj.constants import ALLOWED_LANGUAGES, hkt
from wykoj.forms.utils import Form, editor_widget
from wykoj.models import Contest, Task, User


class SidebarForm(Form):
    content = StringField("Content (HTML5 with Bootstrap)", widget=editor_widget)
    submit = SubmitField("Save")


class TaskForm(Form):
    id = HiddenField("ID")
    task_id = StringField(
        "Task ID",
        validators=[DataRequired(), Regexp(r"^[A-Z][A-Z0-9]{3,4}$")],
        render_kw={"placeholder": "e.g. B001"}
    )
    title = StringField("Name", validators=[DataRequired(), Length(max=100)])
    is_public = BooleanField("Publicly Visible")
    authors = StringField(
        "Author(s)",
        validators=[DataRequired()],
        render_kw={"placeholder": 'Usernames separated by ","'}
    )
    content = StringField(
        "Task Statement (HTML5 with Bootstrap and KaTeX)",
        validators=[DataRequired()],
        widget=editor_widget
    )
    time_limit = DecimalField(
        "Time Limit (s)",
        validators=[DataRequired(), NumberRange(min=Decimal("0.01"), max=10)],
        places=2,
        widget=NumberInput(step=0.01, min=0.01, max=10)
    )
    memory_limit = IntegerField(
        "Memory Limit (MB)",
        validators=[DataRequired(), NumberRange(min=1, max=256)],
        widget=NumberInput(step=1, min=1, max=256)
    )
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        # Validate task id
        task = await Task.filter(task_id=self.task_id.data).first()
        if task and (int(self.id.data) != task.id if self.id.data else True):
            raise ValidationError("Task ID taken.")

        # Validate authors
        usernames = [a.strip() for a in self.authors.data.split(",") if a.strip()]
        usernames = tuple(set(usernames))  # Delete duplicates to avoid unnecessary db queries
        if not usernames:
            raise ValidationError("Author required.")
        users = await asyncio.gather(
            *[User.filter(username__iexact=username).first() for username in usernames]
        )
        for username, user in zip(usernames, users):
            if not user:
                raise ValidationError(f'No user with username "{username}".')


class NewStudentUserForm(Form):
    username = StringField(
        "Username",
        validators=[DataRequired(), Regexp(r"^s\d{2}[flrx]\d{2}$")],
        render_kw={"placeholder": "Identical to eClass LoginID, all lowercase"}
    )
    english_name = StringField("English Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    is_admin = BooleanField("Admin Status")
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        user = await User.filter(username=self.username.data).first()
        if user:
            raise ValidationError("Username taken.")


class NewNonStudentUserForm(NewStudentUserForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Regexp(r"^[a-z0-9]{3,20}$")],
        render_kw={"placeholder": "3-20 alphanumeric characters"}
    )


class UserForm(Form):
    id = HiddenField("ID")
    username = StringField(
        "Username",
        validators=[DataRequired(), Regexp(r"^[a-z0-9]{3,20}$")],
        render_kw={"placeholder": "3-20 alphanumeric characters"}
    )
    name = StringField(
        "Display Name", validators=[Length(max=20)], render_kw={"placeholder": "Optional"}
    )
    english_name = StringField("English Name", validators=[DataRequired()])
    chesscom_username = StringField(
        "Chess.com Username",
        validators=[Regexp(r"^([a-zA-Z0-9_]{3,25})?$")],
        render_kw={"placeholder": "Optional"}
    )
    language = SelectField(
        "Default Language",
        validators=[DataRequired()],
        choices=[(lang, lang) for lang in ALLOWED_LANGUAGES]
    )
    profile_pic = FileField(
        "Update Profile Picture", validators=[FileAllowed(["png", "jpg", "jpeg"])]
    )
    can_edit_profile = BooleanField("Can Edit Profile")
    is_student = BooleanField("Student Status")
    is_admin = BooleanField("Admin Status")
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        user = await User.filter(username__iexact=self.username.data).first()
        if user and int(self.id.data) != user.id:
            raise ValidationError("Username taken.")

        # Validate chess.com username
        if self.chesscom_username.data and not await ChessComAPI.username_exists(
            self.chesscom_username.data
        ):
            raise ValidationError("Nonexistent Chess.com username.")


class AdminResetPasswordForm(Form):
    new_password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("new_password")]
    )
    save = SubmitField("Save")  # Different name required as 2+ forms on the same page


class NewContestForm(Form):
    id = HiddenField("Object ID")
    title = StringField("Name", validators=[DataRequired(), Length(max=100)])
    is_public = BooleanField("Publicly Joinable")
    start_time = DateTimeField("Start Time", validators=[DataRequired()])
    duration = IntegerField(
        "Duration (minutes)",
        validators=[DataRequired(), NumberRange(min=1, max=20160)],
        widget=NumberInput(step=1, min=1, max=20160)
    )  # 1 minute - 14 days
    tasks = StringField("Tasks", render_kw={"placeholder": 'Task IDs separated by ","'})
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        # Validate contest time and duration
        # Check datetime format and ensure a 5 minute gap between contests.
        utc_start_time = hkt.localize(self.start_time.data).astimezone(utc)
        utc_end_time = utc_start_time + timedelta(minutes=self.duration.data)
        async for contest in Contest.all():
            if self.id.data and int(self.id.data) == contest.id:
                continue
            if utc_start_time < contest.start_time:
                if utc_end_time + timedelta(minutes=5) > contest.start_time:
                    raise ValidationError(
                        f"Contest overlaps with {contest.title}. "
                        f"A 5-minute gap between contests is required."
                    )
            elif contest.end_time + timedelta(minutes=5) > utc_start_time:
                raise ValidationError(
                    f"Contest overlaps with {contest.title}. "
                    f"A 5-minute gap between contests is required."
                )

        # Validate tasks
        task_ids = [a.strip() for a in self.tasks.data.split(",") if a.strip()]
        task_ids = list(set(task_ids))
        tasks = await asyncio.gather(
            *[Task.filter(task_id__iexact=task_id).first() for task_id in task_ids]
        )
        for task_id, task in zip(task_ids, tasks):
            if not task:
                raise ValidationError(f'No task with task ID "{task_id}".')


class ContestForm(NewContestForm):
    contestants = TextAreaField(
        "Contestants", render_kw={
            "placeholder": 'Usernames separated by ","',
            "rows": 5
        }
    )
    publish_editorial = BooleanField("Publish Editorial")
    editorial_content = StringField("Editorial", widget=editor_widget)

    async def async_validate(self) -> None:
        usernames = [c.strip() for c in self.contestants.data.split(",") if c.strip()]
        usernames = list(set(usernames))  # Delete duplicates to avoid unnecessary db queries
        users = await asyncio.gather(
            *[User.filter(username__iexact=username).first() for username in usernames]
        )
        for username, user in zip(usernames, users):
            if not user:
                raise ValidationError(f'No user with username "{username}".')
