import html
import os.path
from secrets import token_hex
from tempfile import gettempdir
from typing import Any

import aiofiles.os
from flask_wtf import FlaskForm
from quart import flash
from quart.datastructures import FileStorage
from wtforms import Field
from wtforms.validators import ValidationError


class Form(FlaskForm):
    async def async_validate(self) -> None:
        pass

    async def full_validate(self) -> bool:
        """Since WTForms does not accept async validators,
        this function helps validate both sync and custom async validators.
        A danger message is flashed if an async validator fails.
        """
        if not self.validate_on_submit():
            return False  # Handles the case where form is not submitted

        if hasattr(self, "async_validate"):
            try:
                await self.async_validate()
            except ValidationError as e:
                await flash(str(e), "danger")
                return False

        return True


async def get_filesize(fp: FileStorage) -> int:
    # Filesize is in bytes
    # Apparently you have to save a file to get its size
    filename = token_hex(8)
    _, ext = os.path.splitext(fp.filename)
    path = os.path.join(gettempdir(), filename + ext)
    await fp.save(path)
    fp.seek(0, 0)  # Set file position back to beginning
    size = (await aiofiles.os.stat(path)).st_size
    await aiofiles.os.remove(path)
    return size


def editor_widget(field: Field, **kwargs: Any) -> str:
    """A code editor for forms including code."""
    # The code editor creates its own textarea which is not treated as form data
    # So we create a hidden textarea and listen for changes in the editor
    # (This took way too long to implement)
    kwargs.setdefault("id", field.id)
    if "value" not in kwargs:
        kwargs["value"] = field._value()
    return (
        f'<textarea id="{field.id}" name="{field.id}" type="text"'
        'maxlength="1000000" style="display: none;"></textarea>\n'
        f'<div id="editor" class="{kwargs.get("class", "")}">{html.escape(field.data or "")}</div>'
    )
