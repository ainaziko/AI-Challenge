# Task 3 — Report

## Approach

I built the bot as a single n8n workflow with two AI agents
(Teacher + Examiner) and a Telegram interface, working in
**Cowork mode** with Claude. The architecture, prompts, and
Code-node logic were drafted upfront as a JSON workflow,
imported into my n8n Cloud account, and refined iteratively in
the editor while learning the platform.

The workflow runs as one tight loop:

```
Telegram Trigger
   ↓
Parse Update  (classifies intent: start / learn / quiz / topic_pick / answer)
   ↓
Switch: Route
   ├ start          → Send Welcome
   ├ learn          → Fetch URL → Extract Content → Teacher AI → Save → Send Summary
   ├ quiz_menu      → List Saved Materials → Send Topic List
   ├ topic_pick     → Load Material → Examiner AI → Start Quiz → Send First Question
   └ quiz_answer    → Handle Answer → (more Qs? next | else build results)
```

State (saved materials per user, active quiz) lives in
`$getWorkflowStaticData('global')` — n8n's workflow-scoped
persistent store. No external database is needed.

## What worked

- **Single importable workflow.** The whole 24-node graph imports
  in one paste — no copy-paste assembly needed in n8n. Anyone
  reviewing or re-running the bot just imports the JSON and hooks
  up two credentials.
- **n8n free OpenAI credits** scoped to `gpt-4o-mini` were more
  than enough for both AI agents and several end-to-end test
  runs.
- **Workflow static data for persistence.** Saved materials and
  active quiz state survive across executions without any
  database setup. Trivial to deploy, fine for the brief's scale.
- **Pre-generated quiz explanations.** The Examiner returns the
  correct answer + explanation in the same call that generates
  the 5 questions, so the answer-validation phase doesn't need a
  second AI roundtrip.

## Engineering decisions

The most interesting decision: **using HTTP Request nodes
instead of n8n's native Telegram node for the 4 outbound
messages that need inline keyboards** (Send Summary, Send Topic
List, Send First Question, Send Next Question).

n8n's native Telegram node accepts only statically-defined
inline keyboards through its UI. For dynamic keyboards (a
variable number of topic buttons, variable number of answer
choices), the cleanest path is calling `POST
https://api.telegram.org/bot<token>/sendMessage` directly with
the full payload (`chat_id`, `text`, `parse_mode`,
`reply_markup`). The HTTP Request node accepts arbitrary JSON
expressions for the body, so the inline keyboard structure
produced upstream by the Code nodes passes through unmodified.

The other Telegram nodes (Welcome, Bad URL, Missing Notice,
Results, Unknown) stay on the native node because they don't
need dynamic keyboards.

A second, smaller decision: **all answer explanations are
generated at quiz-creation time**, not on demand. Saves one
AI call per quiz, and keeps the final results message
deterministic for a given generated quiz.

## Tools and techniques used

- **n8n Cloud** (free trial) for workflow orchestration, webhook
  hosting, and persistent storage.
- **Telegram Bot API** — `telegramTrigger` for incoming updates;
  `HTTP Request` for outgoing messages where inline keyboards
  matter; native Telegram node for plain text messages.
- **OpenAI `gpt-4o-mini`** via n8n's hosted free credits for both
  agents. Temperature 0.2 for the Teacher (faithful
  summarisation), 0.3 for the Examiner (slightly more variety
  across question generation).
- **Claude in Cowork mode** for drafting the workflow,
  Code-node logic (intent parsing, state persistence, question
  advancement, result building), and the two AI agent prompts.

## Notable decisions

- **One workflow, not multiple.** Simpler to import, simpler to
  review, simpler to ship.
- **Static data over external DB.** No infra; saved materials
  per chat survive between executions on the same workflow.
- **HTTP Request for dynamic outbound messages.** Avoids the
  static-keyboard limitation in n8n's Telegram node.
- **Idempotent answer handling.** If a user double-taps a quiz
  button (or Telegram retries the callback), the Code node
  detects the answer was already recorded and replies with a
  no-op acknowledgement instead of advancing the cursor.
