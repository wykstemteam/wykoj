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
- Install [Bootstrap Sass (v5.0.2)](https://github.com/twbs/bootstrap/archive/refs/tags/v5.0.2.zip).
- Copy all files in `bootstrap-5.0.2/scss/` to `wykoj/scss/bootstrap/`.
- Compile (and minify) `wykoj/scss/style.scss` to `wykoj/static/style.min.css`
  (Settings are configured for the VS Code
  [Live SASS Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass) extension.)
- Install/Upgrade dependencies: `pip install -U -r requirements.txt`.
- Create `config.json` in the inner `wykoj` directory with
  `JUDGE_HOST`, `SECRET_KEY` and `DB_URI`. (add details later)
- Initialize database: `python init_db.py`.
- Run: `hypercorn -b 0.0.0.0:3000 "wykoj:create_app()"`.

Access the online judge at http://localhost:3000.

## Roadmap
- Test Contest 2: Grader, Batched Task
- Batch user creation
- Upload file for submission
- Add scoring table for batched test cases
- Description for test cases
- Drop solve columns, replace with query
- Add language specs to Info page
- Play Baka Mitai on chess page
- Chess rating leaderboard
- Lichess games
- Stats in user page and contests page
- Task stats page (hide link during contest, contest redirect)
- Replace refreshing of submission page in `main.js` with
  https://pgjones.gitlab.io/quart/tutorials/broadcast_tutorial.html
- Spinning Ame animation on submission page if pending
- Custom page creation (admin)
- Add tags to tasks
- Advanced filtering form footer for submissions page
- Categorization for tasks
- Groups and assignments
- Maybe SPA but probably not
