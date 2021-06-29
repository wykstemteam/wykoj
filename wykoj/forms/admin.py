import asyncio
from datetime import timedelta

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, HiddenField, SubmitField
from wtforms.fields.html5 import IntegerField, DecimalField, DateTimeField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, EqualTo, ValidationError
from wtforms.widgets.html5 import NumberInput

from wykoj.constants import ALLOWED_LANGUAGES
from wykoj.models import User, Task, Contest
from wykoj.utils.main import editor_widget


class SidebarForm(FlaskForm):
    content = StringField("Content (HTML5 with Bootstrap)", validators=[DataRequired()], widget=editor_widget)
    submit = SubmitField("Save")


class TaskForm(FlaskForm):
    id = HiddenField("ID")
    task_id = StringField("Task ID", validators=[DataRequired(), Regexp(r"^[A-Z]{1,2}\d{3,4}$")],
                          render_kw={"placeholder": "e.g. B001"})
    title = StringField("Name", validators=[DataRequired(), Length(max=100)])
    is_public = BooleanField("Publicly Visible")
    authors = StringField("Author(s)", validators=[DataRequired()],
                          render_kw={"placeholder": 'Usernames separated by ","'})
    content = StringField("Task Statement (HTML5 with Bootstrap and MathJax)",
                          validators=[DataRequired()], widget=editor_widget)
    time_limit = DecimalField("Time Limit (s)", validators=[DataRequired(), NumberRange(min=0.01, max=10)],
                              places=2, widget=NumberInput(step=0.01, min=0.01, max=10))
    memory_limit = IntegerField("Memory Limit (MB)", validators=[DataRequired(), NumberRange(min=1, max=256)],
                                widget=NumberInput(step=1, min=1, max=256))
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        # Validate task id
        task = await Task.filter(task_id=self.task_id.data).first()
        if task and self.id.data and int(self.id.data) != task.id:
            raise ValidationError("Task ID taken.")

        # Validate authors
        usernames = [a.strip() for a in self.authors.data.split(",") if a.strip()]
        usernames = tuple(set(usernames))  # Delete duplicates to avoid unnecessary db queries
        if not usernames:
            raise ValidationError("Author required.")
        users = await asyncio.gather(*[User.filter(username__iexact=username).first() for username in usernames])
        for username, user in zip(usernames, users):
            if not user:
                raise ValidationError(f'No user with username "{username}".')


class NewStudentUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Regexp(r"^s\d{2}[flrx]\d{2}$")],
                           render_kw={"placeholder": "Identical to eClass LoginID, all lowercase"})
    english_name = StringField("English Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    is_admin = BooleanField("Admin Status")
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        user = await User.filter(username=self.username.data).first()
        if user:
            raise ValidationError("Username taken.")


class NewNonStudentUserForm(NewStudentUserForm):
    username = StringField("Username", validators=[DataRequired(), Regexp(r"^[a-z0-9]{3,20}$")],
                           render_kw={"placeholder": "3-20 alphanumeric characters"})


class UserForm(FlaskForm):
    id = HiddenField("ID")
    username = StringField("Username", validators=[DataRequired(), Regexp(r"^[a-z0-9]{3,20}$")],
                           render_kw={"placeholder": "3-20 alphanumeric characters"})
    name = StringField("Display Name", validators=[Length(max=20)], render_kw={"placeholder": "Optional"})
    english_name = StringField("English Name", validators=[DataRequired()])
    language = SelectField("Default Language", validators=[DataRequired()],
                           choices=[(lang, lang) for lang in ALLOWED_LANGUAGES])
    profile_pic = FileField("Update Profile Picture", validators=[FileAllowed(["png", "jpg", "jpeg"])])
    can_edit_profile = BooleanField("Can Edit Profile")
    is_student = BooleanField("Student Status")
    is_admin = BooleanField("Admin Status")
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        user = await User.filter(username__iexact=self.username.data).first()
        if user and self.id.data and int(self.id.data) != user.id:
            raise ValidationError("Username taken.")


class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password")])
    save = SubmitField("Save")  # Different name required as 2+ forms on the same page


class NewContestForm(FlaskForm):
    id = HiddenField("Object ID")
    title = StringField("Name", validators=[DataRequired(), Length(max=100)])
    is_public = BooleanField("Publicly Joinable")
    start_time = DateTimeField("Start Time", validators=[DataRequired()])
    duration = IntegerField("Duration (minutes)", validators=[DataRequired(), NumberRange(min=1, max=20160)],
                            widget=NumberInput(step=1, min=1, max=20160))  # 1 minute - 14 days
    tasks = StringField("Tasks", render_kw={"placeholder": 'Task IDs separated by ","'})
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        # Validate contest time and duration
        # Check datetime format and ensure 15 minute interval between contests.
        self_end_time = self.start_time.data + timedelta(minutes=self.duration.data)
        async for contest in Contest.all():
            if self.id.data and int(self.id.data) == contest.id:
                continue
            if self.start_time.data < contest.start_time:
                if self_end_time + timedelta(minutes=15) > contest.start_time:
                    raise ValidationError(f"Contest overlapped with {contest.title}. "
                                          f"A 15-minute interval between contests is required.")
            elif contest.end_time + timedelta(minutes=15) > self.start_time.data:
                raise ValidationError(f"Contest overlapped with {contest.title}. "
                                      f"A 15-minute interval between contests is required.")

        # Validate tasks
        task_ids = [a.strip() for a in self.tasks.data.split(",") if a.strip()]
        task_ids = list(set(task_ids))
        tasks = await asyncio.gather(*[Task.filter(task_id__iexact=task_id).first() for task_id in task_ids])
        for task_id, task in zip(task_ids, tasks):
            if not task:
                raise ValidationError(f'No task with task ID "{task_id}".')


class ContestForm(NewContestForm):
    contestants = TextAreaField("Contestants", render_kw={"placeholder": 'Usernames separated by ","', "rows": 5})

    async def async_validate(self) -> None:
        usernames = [c.strip() for c in self.contestants.data.split(",") if c.strip()]
        usernames = list(set(usernames))  # Delete duplicates to avoid unnecessary db queries
        users = await asyncio.gather(*[User.filter(username__iexact=username).first() for username in usernames])
        for username, user in zip(usernames, users):
            if not user:
                raise ValidationError(f'No user with username "{username}".')