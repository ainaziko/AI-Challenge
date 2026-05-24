# Task 1 — Report

## Approach

I built this leaderboard as a single-file static site using **Claude
in Cowork mode** — pair-programming with an AI that has direct
access to a working folder on my computer. The workflow was tight
and iterative: I sent annotated screenshots of the original widget,
Claude generated and updated HTML / CSS / JS, I refreshed the local
preview, and we kept refining the visual details across ~20 rounds
of feedback until the clone matched.

The deliverable covers the full UI of the original — top-3 podium
with gold / silver / bronze badges, three filter dropdowns (Year /
Quarter / Category), animated search input, expandable list rows
with a Recent Activity table, hide-on-scroll subnav, and a
SharePoint-style chrome around it. All filters, sorting, and search
work end-to-end.

## How I handled the data replacement

The brief forbids any real data from the original. Everything on
the page is fictional:

- **14 invented employees** with plausible-but-fake names (Marlow
  Vance, Indira Whitfield, Theo Brennan, Felix Marquez, …).
- **Generic role titles** — "Engineering Lead", "Product Designer",
  "Senior Backend Engineer" — no real organisational codes.
- **Activity titles written from scratch** with my own bracket
  prefixes: `[CONF]`, `[SESH]`, `[MNT]`, `[OUT]`, `[OSS]`.
- **Renamed categories** — Mentorship / Talks / Outreach /
  Open Source.
- **Initial-based avatars** in colour-seeded gradient circles —
  no photos.
- **Placeholder brand** ("acme") in the SharePoint-style top bar.

No corporate data was sent to any AI tool at any point. The only
inputs were cropped screenshots of UI structure that I prepared
myself.

## Tools and techniques

- **Claude in Cowork mode** as the primary IDE — Claude edited
  files directly in my workspace and ran a local `python3 -m
  http.server` to verify the page rendered correctly.
- **Hand-written HTML / CSS / JavaScript** — no framework, no
  build step, no runtime dependencies.
- **GitHub Pages** for deployment, served from the `/docs` folder
  of this repo.

The four source files (`index.html`, `styles.css`, `app.js`,
`data.js`) are self-contained and require no installation step
to run locally — open `index.html` in any browser or serve the
folder with `python3 -m http.server`.
