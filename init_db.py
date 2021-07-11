import asyncio

from quart import Quart
from tortoise import Tortoise

from wykoj import bcrypt, create_app
from wykoj.models import Sidebar, User


async def init_db(app: Quart) -> None:
    """Performs database initialization. You should only run this once.

    Generates database schemas, and creates default sidebar content
    and an admin user with username "admin" and password "adminadmin".
    (Please change username and password upon first login.)
    SQLite file must not be already present at DB_URI specified in config.json.
    """

    await Tortoise.init(db_url=app.config["DB_URI"], modules={'models': ['wykoj.models']})
    await Tortoise.generate_schemas()

    await asyncio.gather(
        Sidebar.create(
            content=(
                '<div class="card border-danger mb-3">\n'
                '    <div class="card-header">Announcement</div>\n'
                '    <div class="card-body">\n'
                '        <h5 class="card-title mb-0">Welcome to WYKOJ!</h5>\n'
                '    </div>\n'
                '</div>'
            )
        ),
        User.create(
            username="admin",
            password=bcrypt.generate_password_hash("adminadmin").decode("utf-8"),
            name="Admin",
            english_name="Admin",
            is_student=False,
            is_admin=True
        )
    )

    await Tortoise.close_connections()


if __name__ == "__main__":
    app = create_app()
    asyncio.run(init_db(app))
