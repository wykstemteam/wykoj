from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from quart_auth import current_user
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, EqualTo, ValidationError

from wykoj.constants import ALLOWED_LANGUAGES
from wykoj.models import User
from wykoj.utils.main import editor_widget


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class StudentSettingsForm(FlaskForm):
    name = StringField("Display Name", validators=[Length(max=20)], render_kw={"placeholder": "Optional"})
    language = SelectField("Default Language", choices=[(lang, lang) for lang in ALLOWED_LANGUAGES],
                           validators=[DataRequired()])
    profile_pic = FileField("Update Profile Picture", validators=[FileAllowed(["png", "jpg", "jpeg"])])
    submit = SubmitField("Save")


class NonStudentSettingsForm(StudentSettingsForm):
    username = StringField("Username", validators=[Regexp(r"^([a-z0-9]{3,20})?$")],  # Empty handled by DataRequired()
                           render_kw={"placeholder": "3-20 alphanumeric characters"})
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


class ResetPasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password")])
    save = SubmitField("Save")  # Different name required as multiple forms on the same page


class TaskSubmitForm(FlaskForm):
    language = SelectField("Language", choices=[(lang, lang) for lang in ALLOWED_LANGUAGES],
                           validators=[DataRequired()])
    source_code = StringField("Source Code", widget=editor_widget, validators=[DataRequired(), Length(max=1000000)])
    submit = SubmitField("Submit")
