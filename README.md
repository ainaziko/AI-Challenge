# AI Challenge 2 — Submissions

Four task submissions for the Vention AI Challenge, by Ainazik Momunalieva
([@ainaziko](https://github.com/ainaziko)).

Each task lives in its own folder with its own `README.md`, `report.md`, and
source. A short summary of every task is below — start there, then drop into
the per-task folder for details.

| # | Task | Folder | Key artifact |
| - | --- | --- | --- |
| 1 | Company leaderboard clone | [`task-1/`](./task-1) | Live page at `https://ainaziko.github.io/<repo>/` (see below) |
| 2 | Event hosting platform on Lovable | [`task-2/`](./task-2) | [`PROMPT_PLAYBOOK.md`](./task-2/PROMPT_PLAYBOOK.md) + sample CSV |
| 3 | n8n Telegram learning assistant | [`task-3/`](./task-3) | [`learning-bot.workflow.json`](./task-3/learning-bot.workflow.json) |
| 4 | MCP Air-Traffic-Control server | [`task-4/`](./task-4) | Python MCP server (`python -m atc_mcp`) |

---

## Task 1 — Company Leaderboard

Pure HTML / CSS / JavaScript clone of an internal SharePoint leaderboard
widget, with fake names, roles, and activities. No corporate data was sent
to any AI tool — only annotated screenshots of the UI structure.

- Three filter dropdowns (Year / Quarter / Category) + animated search
- Top-3 podium with gold / silver / bronze rank badges
- Expandable rows showing a "Recent Activity" table per person

Run locally: `cd task-1 && python3 -m http.server 8000`.

## Task 2 — Lovable event platform (Meetly)

A prompt-by-prompt build playbook for the event hosting and attendance
platform required by the brief. Paste the prompts from
[`task-2/PROMPT_PLAYBOOK.md`](./task-2/PROMPT_PLAYBOOK.md) into Lovable in
order; each prompt is acceptance-criteria-driven so the build stays on rails.

Includes:
- A 14-prompt build script covering hosts, events, RSVP, waitlist, tickets,
  QR codes, check-in, roles, dashboard, CSV export, gallery, feedback,
  reporting, seed data, and a self-audit QA pass.
- [`sample-rsvps-export.csv`](./task-2/sample-rsvps-export.csv) — a
  representative file showing the exact export schema.
- Targeted fix + recovery prompts for when Lovable gets stuck.

## Task 3 — n8n Telegram learning bot

A single n8n workflow that turns Telegram into an AI learning assistant. The
workflow has two distinct AI roles:

- **Teacher** — fetches a URL, extracts the text, returns 5–7 key points,
  3–6 main concepts, and a difficulty rating.
- **Examiner** — generates a 5-question multiple-choice quiz from the saved
  material, scores answers, and explains the wrong ones.

Persistence lives in n8n's workflow static data, so users can come back
later to `/quiz` anything they've learned without any external database.
Step-by-step BotFather + n8n setup is in [`task-3/setup.md`](./task-3/setup.md).

## Task 4 — MCP Air-Traffic-Control server

Python MCP server (FastMCP) that coordinates flight operations:

- 5 tools — `submit_flight`, `generate_schedule`, `get_airport_status`,
  `cancel_flight`, `bottleneck_analysis`.
- 3 resources — `atc://flights/queue`, `atc://runways/usage`,
  `atc://timeline`.
- Deterministic, priority-aware, dependency-respecting scheduler with
  runway / gate / ground-crew constraints loaded from environment
  variables.
- 8 unit tests covering all three validation scenarios from the brief,
  plus determinism, cancellation, bottleneck, and config validation.

Run: `cd task-4 && pip install -r requirements.txt && python -m atc_mcp`.

---

## Pushing to GitHub

You have a clean, ready-to-push tree. Here's the one-shot recipe:

```bash
# from inside the ai-challenge-2/ folder

git init
git add .
git commit -m "AI Challenge 2: tasks 1–4"

# create the repo on github.com first (public). Then:
git branch -M main
git remote add origin https://github.com/ainaziko/ai-challenge-2.git
git push -u origin main
```

> Repo name suggestion: `ai-challenge-2`. If you prefer something else,
> swap the URL above.

## Enabling GitHub Pages for Task 1

GitHub Pages serves a repo from a single folder, so we use a tiny shim to
publish only the `task-1/` files at the root of the published site.

### Option A — easiest, dedicated repo (recommended)

1. Create a SECOND public repo named e.g. `leaderboard`.
2. Copy the contents of `task-1/` (not the folder itself — its contents)
   to the root of that repo.

   ```bash
   # from outside ai-challenge-2/
   git clone https://github.com/ainaziko/leaderboard.git
   cp ai-challenge-2/task-1/* leaderboard/
   cd leaderboard
   git add .
   git commit -m "Leaderboard clone"
   git push
   ```
3. On github.com → repo `leaderboard` → **Settings → Pages** → Source =
   "Deploy from a branch", Branch = `main`, Folder = `/ (root)`. Save.
4. Wait ~1 minute. URL: `https://ainaziko.github.io/leaderboard/`.

### Option B — keep everything in the monorepo

1. In the `ai-challenge-2` repo, copy `task-1/` to `docs/`:

   ```bash
   cp -r task-1/* docs/
   git add docs/
   git commit -m "Publish leaderboard to docs/ for GitHub Pages"
   git push
   ```
2. github.com → repo `ai-challenge-2` → **Settings → Pages** → Source =
   "Deploy from a branch", Branch = `main`, Folder = `/docs`. Save.
3. URL: `https://ainaziko.github.io/ai-challenge-2/`.

Either way, paste the final URL into the submission form.

## What to put on the submission form

Per the [submission form](https://forms.office.com/r/b4H97DZ2VE):

- **Task 1 deployed URL**: `https://ainaziko.github.io/leaderboard/`
  (Option A) or `https://ainaziko.github.io/ai-challenge-2/` (Option B).
- **Task 1 GitHub repo**: same as the published Pages source.
- **Task 2 deployed URL**: published Lovable URL (after running the
  playbook).
- **Task 2 GitHub repo**: `https://github.com/ainaziko/ai-challenge-2`
  pointing at the `task-2/` folder (or a linked Lovable-synced repo if you
  connect Lovable to GitHub).
- **Task 3 GitHub repo + bot link**: repo URL + your `@<bot_name>` from
  BotFather.
- **Task 4 GitHub repo**: same monorepo, point reviewers at `task-4/`.

## Repository layout

```
ai-challenge-2/
├── README.md                       ← you are here
├── .gitignore
├── task-1/                         ← Leaderboard clone (Task 1)
│   ├── README.md
│   ├── report.md
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── data.js
├── task-2/                         ← Lovable event platform (Task 2)
│   ├── README.md
│   ├── report.md
│   ├── PROMPT_PLAYBOOK.md
│   └── sample-rsvps-export.csv
├── task-3/                         ← n8n + Telegram learning bot (Task 3)
│   ├── README.md
│   ├── report.md
│   ├── setup.md
│   └── learning-bot.workflow.json
└── task-4/                         ← MCP ATC server (Task 4)
    ├── README.md
    ├── report.md
    ├── requirements.txt
    ├── pyproject.toml
    ├── .env.example
    ├── atc_mcp/
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── airport.py
    │   ├── config.py
    │   ├── models.py
    │   ├── scheduler.py
    │   └── server.py
    └── tests/
        ├── __init__.py
        └── test_scenarios.py
```

## Responsible AI compliance

All four tasks were built without sending any corporate data — real names,
photos, document content, internal URLs — to any AI tool. The only inputs
were:

- Public requirements text from the challenge brief.
- Annotated UI screenshots of the original leaderboard (Task 1) without
  any of the surrounding real-person data being read into the model. Where
  real names appeared in screenshots, they were not used as inputs to any
  prompt and have been replaced wholesale with fictional names in the
  delivered code.
