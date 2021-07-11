# WYK Online Judge
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
  (You may use [Live SASS Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass) in VS Code).
- Install/Upgrade dependencies: `pip install -U -r requirements.txt`.
- Create `config.json` in the inner `wykoj` directory with `JUDGE_HOST`, `SECRET_KEY` and `DB_URL`. (add details later)
- Initialize database: `python init_db.py`.
- Run: `hypercorn -b 0.0.0.0:3000 "wykoj:create_app()"`.

Access the online judge at http://localhost:3000.

## Issues
- Server crashes when test cases are too large (>100 MB)

## Roadmap
- Upgrade Bootstrap + Bootswatch
- Upgrade Chart.js (https://www.chartjs.org/docs/latest/getting-started/v3-migration.html)
- Leaderboard (split to all time, weekly and daily), only show all time on narrow screens
- Add language specs to Info page
- Upload file for submission
- Mass user creation
- Stats in user page and contests page
- Task stats page (hide link during contest, contest redirect)
- Replace refreshing of submission page in `main.js` with
  https://pgjones.gitlab.io/quart/tutorials/broadcast_tutorial.html
- Advanced filtering form footer for submissions page
- Categorization for tasks
