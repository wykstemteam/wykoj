# WYK Online Judge
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)
[
    ![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)
](https://pycqa.github.io/isort/)

An online judge with tasks and contests.

Live Version: https://wykoj.owo.idv.hk

UI based on [HKOI Online Judge](https://judge.hkoi.org).

Hmmm yes chess pages in an online judge

## Installation (To Be Completed)
Steps:
- Clone repo with `git clone https://github.com/jonowo/wykoj`.
- Install [Bootstrap Sass (v4.5.0)](https://github.com/twbs/bootstrap/archive/v4.5.0.zip).
- Copy all files in `bootstrap-4.5.0/scss/` to `wykoj/scss/bootstrap/`.
- Compile (and minify) `wykoj/scss/style.scss` to `wykoj/static/style.min.css`
  (Settings are configured for the VS Code
  [Live SASS Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass) extension.)
- Install/Upgrade dependencies: `pip install -U -r requirements.txt`.
- Create `config.json` in the inner `wykoj` directory with
  `JUDGE_HOST`, `SECRET_KEY` and `DB_URI`. (add details later)
- Initialize database: `python init_db.py`.
- Run: `hypercorn -b 0.0.0.0:3000 "wykoj:create_app()"`.

Access the online judge at http://localhost:3000.

## Issues
- Server crashes when test cases are too large (>100 MB)

## Roadmap
- Implement OGP properly (with new block in jinja)
- Batch user creation
- Upload file for submission
- Drop solve columns, replace with query
- Add language specs to Info page
- Chess rating leaderboard
- Lichess games
- Stats in user page and contests page
- Task stats page (hide link during contest, contest redirect)
- Custom page creation (admin)
- Replace refreshing of submission page in `main.js` with
  https://pgjones.gitlab.io/quart/tutorials/broadcast_tutorial.html
- Advanced filtering form footer for submissions page
- Categorization for tasks
- Groups and assignments
- Maybe SPA but probably not
