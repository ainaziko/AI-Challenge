# Task 1 — Company Leaderboard

A single-page clone of an internal SharePoint leaderboard widget, built with
plain HTML, CSS and JavaScript. All names, roles, and activities are
fictional — the original corporate data was never fed to the AI tools used
to build this.

## What it does

- Lists employees ranked by total points across all contributions.
- Top 3 are highlighted on a podium (with the gold #1 sitting taller than
  the silver / bronze runners-up).
- Three filter dropdowns and a search field:
  - **Year** — defaults to "All Years", populates from the data.
  - **Quarter** — All Quarters / Q1 / Q2 / Q3 / Q4.
  - **Category** — All / Mentorship / Talks / Outreach / Open Source.
  - **Search** — substring match on the person's name. The magnifying-glass
    icon slides out to the left when the input is focused, just like the
    original.
- Each list row is expandable: clicking the row (or the chevron) opens a
  table of that person's recent activity, with category pill and points.
- Filtering recomputes totals, podium, ranks, and the per-row activity
  table on the fly.

## Run locally

No build step. Just open the page:

```bash
cd task-1
python3 -m http.server 8000
# then open http://localhost:8000
```

Or double-click `index.html` directly — everything is static and
relative-pathed.

## Deploy to GitHub Pages

There are two reasonable layouts. Pick one.

### Option A — dedicated repo (simplest)

1. Create a new public repo, e.g. `leaderboard`.
2. Copy the contents of `task-1/` into the repo root.
3. Push to `main`.
4. Repo → Settings → Pages → Source = "Deploy from a branch" → branch =
   `main`, folder = `/ (root)` → Save.
5. Wait ~1 minute. Your URL is `https://<your-gh-username>.github.io/leaderboard/`.

### Option B — keep it inside the challenge monorepo

The challenge repo expects `task-1/` to live alongside the other tasks. To
serve it from the monorepo:

1. Push the whole repo.
2. Repo → Settings → Pages → Source = "Deploy from a branch" → branch =
   `main`, folder = `/docs` → Save.
3. Add a `docs/` directory at the repo root containing the same files as
   `task-1/` (or a symlink in CI). The hosted URL is
   `https://<your-gh-username>.github.io/<repo>/`.

The root README has a copy-paste script for option B.

## Files

```
task-1/
├── index.html      # markup
├── styles.css      # all visual styling, transitions, responsive rules
├── app.js          # rendering + filtering + dropdown / expand logic
├── data.js         # fictional people + activities (the only data source)
├── README.md       # this file
└── report.md       # write-up
```

The data lives in `data.js` as a plain JS object on `window.LEADERBOARD_DATA`.
To tweak the demo, edit that file — nothing else needs to change.

## Browser support

Targets modern evergreen browsers (Chrome, Firefox, Safari, Edge). Uses
CSS Grid, `:focus-within`, CSS custom properties, and ES2017 syntax — all
of which have been universally supported for years.

## Accessibility notes

- Each dropdown has `role="listbox"` and `aria-expanded` state.
- Search input has a visually hidden label.
- The expand button has `aria-expanded` and `aria-label`.
- Detail panel uses `aria-hidden` when collapsed.
- Focus rings are styled via `:focus-visible`.
