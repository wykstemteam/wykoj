# WYK Online Judge
An online judge with tasks and contests.

UI based on [HKOI Online Judge](https://judge.hkoi.org).

## Installation
I will update this later, there are a zillion steps lol

Steps (Roughly):
- Clone repo with `git clone https://github.com/Tr-Jono/wykoj`.
- Compile (and minify) `wykoj/scss/style.scss` to `wykoj/static/style.min.css`
  (You may use [Live SASS Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass) in VS Code).
- Install dependencies: `pip install -r requirements.txt`.
- Create `config.json` in the inner `wykoj` directory with `SECRET_KEY` and `DB_URL`. (add details later)
- Initialize database: `python init_db.py`.
- Run: `hypercorn -b localhost:3000 "wykoj:create_app()"`.

Access the online judge at http://localhost:3000.

## Issues to Fix (or treat them as features)
- `ConnectionAbortError: [WinError 10053] An established connection was aborted by the software in your host machine` appearing randomly.

## Roadmap
- Add language specs to Info page
- Implement database migration for `test.py` (to create a copy of `wykoj.db` for testing)
- Stats in user page and contests page
- Task stats page (hide link during contest, contest redirect)
- Replace refreshing of submission page in `main.js` with
  https://pgjones.gitlab.io/quart/tutorials/broadcast_tutorial.html
- Advanced filtering form footer for submissions page
- Categorization for tasks