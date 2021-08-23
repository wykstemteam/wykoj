import os.path

from flask_wtf.file import FileAllowed, FileField
from quart_auth import current_user
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from wykoj.api.chesscom import ChessComAPI
from wykoj.constants import ALLOWED_LANGUAGES, LANGUAGE_EXTENSIONS
from wykoj.forms.utils import Form, editor_widget, get_filesize
from wykoj.models import User


class LoginForm(Form):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class StudentSettingsForm(Form):
    name = StringField(
        "Display Name", validators=[Length(max=20)], render_kw={"placeholder": "Optional"}
    )
    chesscom_username = StringField(
        "Chess.com Username",
        validators=[Regexp(r"^([a-zA-Z0-9_]{3,25})?$")],
        render_kw={"placeholder": "Optional"}
    )
    language = SelectField(
        "Default Language",
        choices=[(lang, lang) for lang in ALLOWED_LANGUAGES],
        validators=[DataRequired()]
    )
    profile_pic = FileField(
        "Update Profile Picture", validators=[FileAllowed(["png", "jpg", "jpeg"])]
    )
    submit = SubmitField("Save")

    async def async_validate(self) -> None:
        if self.profile_pic.data and await get_filesize(self.profile_pic.data) > 8 * 1000 * 1000:
            raise ValidationError("Profile picture exceeds 8 MB.")

        # Validate chess.com username
        if self.chesscom_username.data and not await ChessComAPI.username_exists(
            self.chesscom_username.data
        ):
            raise ValidationError("Nonexistent Chess.com username.")


class NonStudentSettingsForm(StudentSettingsForm):
    username = StringField(
        "Username",
        validators=[Regexp(r"^([a-z0-9]{3,20})?$")],
        render_kw={"placeholder": "3-20 alphanumeric characters"}
    )
    english_name = StringField("English Name", validators=[Length(max=100)])

    def validate_username(self, username: StringField) -> None:
        if current_user.can_edit_profile:
            DataRequired()(self, username)

    def validate_english_name(self, english_name: StringField) -> None:
        if current_user.can_edit_profile:
            DataRequired()(self, english_name)

    async def async_validate(self) -> None:
        if self.username.data == current_user.username:
            return
        user = await User.filter(username__iexact=self.username.data).first()
        if user:
            raise ValidationError("Username taken.")

        await super().async_validate()


class ResetPasswordForm(Form):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("new_password")]
    )
    save = SubmitField("Save")  # Different name required as multiple forms on the same page


class TaskSubmitForm(Form):
    language = SelectField(
        "Language",
        choices=[(lang, lang) for lang in ALLOWED_LANGUAGES],
        validators=[DataRequired()]
    )
    source_code_file = FileField(
        "Upload", validators=[FileAllowed(list(LANGUAGE_EXTENSIONS.values()))]
    )
    source_code = StringField(
        "Source Code", widget=editor_widget, validators=[Length(max=100 * 1000)]
    )
    submit = SubmitField("Submit")

    async def async_validate(self) -> None:
        if not self.source_code_file.data:
            return

        if await get_filesize(self.source_code_file.data) > 100 * 1000:
            raise ValidationError("Source code file exceeds 100 kB.")

        _, ext = os.path.splitext(self.source_code_file.data.filename)
        if ext != "." + LANGUAGE_EXTENSIONS[self.language.data]:
            raise ValidationError("File extension does not match language.")
