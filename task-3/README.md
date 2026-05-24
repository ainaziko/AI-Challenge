# Task 3 — AI Learning Assistant (Telegram Bot)

## Live bot

**Try the bot:** [@graspItAIBot](https://t.me/graspItAIBot)

The workflow runs on n8n Cloud and listens to Telegram via webhook. Send `/start` to the bot to begin, then `/learn <url>` to summarise any article and `/quiz` to test yourself on it.

A Telegram bot that turns any URL into a structured summary and a
multiple-choice quiz. Built as a single n8n workflow with two AI
roles:

- **Teacher** — fetches the page, extracts the text, returns 5–7
  key points, 3–6 main concepts, and a difficulty rating.
- **Examiner** — generates a 5-question multiple-choice quiz from
  the saved material, scores the user's answers, and explains
  anything they got wrong.

State (saved materials per user, active quiz) persists across
executions in n8n's workflow static data — no external database.

## How to use the bot

Open the bot in Telegram and send commands:

| Command | What happens |
| --- | --- |
| `/start` | Welcome message + cheat sheet |
| `/learn <url>` | Fetches the page, the Teacher summarises it, you get key points + main concepts + difficulty back. Material is saved for later quizzing. |
| `/quiz` | Lists your saved materials. Tap one → Examiner generates 5 questions → answer via inline buttons → get a scored report. |

After every `/learn` summary there's a **🎯 Quiz me on this**
button that starts the quiz immediately on that material.

## Example walkthrough

```
You: /learn https://en.wikipedia.org/wiki/Spaced_repetition
Bot: 📘 Spaced Repetition
     Difficulty: intermediate
     Key points: 1, 2, 3, 4, 5...
     Main concepts: • term — definition...
     [🎯 Quiz me on this]

You: (tap the button)
Bot: Quiz: Spaced Repetition
     Q1/5: ...
     [A. ...] [B. ...] [C. ...] [D. ...]

(after 5 questions)

Bot: 🏁 Quiz complete — 80%
     4/5 correct on Spaced Repetition
     ❌ Q3. ...
        Your answer: ...
        Correct: ...
        explanation ...
```

## Files in this folder

```
task-3/
├── README.md                    ← you are here
├── report.md                    ← decisions, what worked, what didn't
├── setup.md                     ← step-by-step BotFather + n8n setup
└── learning-bot.workflow.json   ← importable n8n workflow
```

## Setup for reviewers

If you want to run this bot yourself, see [`setup.md`](./setup.md)
for the step-by-step (~8 minutes): create the bot in BotFather,
sign up for n8n Cloud, import the workflow JSON, hook up Telegram
+ OpenAI credentials, publish.

