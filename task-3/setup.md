# Step-by-step setup

Estimated total time: ~8 minutes.

## 1. Create the Telegram bot

1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot`.
3. Pick a display name (e.g. "My Learning Buddy").
4. Pick a unique username ending in `bot` (e.g. `my_learning_bb_bot`).
5. BotFather replies with an **HTTP API token** that looks like
   `1234567890:AAH...`. Copy it — you'll paste it into n8n in a moment.
6. (Optional) `/setcommands` → paste:

   ```
   start - Show help
   learn - Summarise a URL: /learn <url>
   quiz - Take a quiz on a saved topic
   ```

   This makes the commands auto-complete in the Telegram client.

## 2. Start n8n

Pick one of:

- **n8n Cloud (recommended for the challenge)** — sign up at
  [app.n8n.cloud/register](https://app.n8n.cloud/register). The free trial
  includes the AI nodes and credits.
- **Self-host** — `npx n8n` (requires Node.js 18+), or
  `docker run -it --rm -p 5678:5678 n8nio/n8n`. Open `http://localhost:5678`.

## 3. Add credentials

Inside n8n, click **Credentials → New** and create:

### Telegram Bot

- Search "Telegram"
- Paste the BotFather token into **Access Token**.
- Save.

### OpenAI

Two options:

**(a) Use n8n's hosted credits (free trial only).**
n8n Cloud's free trial exposes a managed OpenAI credential automatically.
Pick `OpenAI` when prompted and select the managed credential — no API key
needed.

**(b) Use your own OpenAI key.**
- Create a key at <https://platform.openai.com/api-keys>.
- In n8n → Credentials → New → "OpenAI" → paste the key → Save.

## 4. Import the workflow

1. In n8n, go to **Workflows → Import from File**.
2. Pick `learning-bot.workflow.json` from this folder.
3. Open the workflow.

Now wire credentials onto the nodes (the import leaves credential refs
empty):

- **Telegram Trigger** → Credentials → pick your Telegram Bot credential.
- **Send Welcome / Send Bad URL / Send Summary / Send Topic List /
  Send Missing Notice / Send First Question / Send Next Question /
  Send Results / Send Unknown** → same Telegram credential on each.
- **Teacher AI** and **Examiner AI** → pick your OpenAI credential.

## 5. Activate the workflow

Top right → **Active** toggle on. n8n registers the Telegram webhook
automatically. Within ~1 second your bot starts answering.

## 6. Smoke test

In Telegram, open your new bot and send:

```
/start
/learn https://en.wikipedia.org/wiki/Spaced_repetition
/quiz
```

Tap a topic in the quiz menu and answer the five questions. You should
receive a scored result with explanations for anything you got wrong.

## Common gotchas

- **Webhook conflict.** A Telegram bot can only have one webhook at a time.
  If you previously used the same token elsewhere, n8n will replace the
  webhook automatically on first activation. If you see "Conflict: terminated
  by setWebhook request", re-activating the workflow once usually clears it.
- **Self-hosted n8n behind NAT.** Telegram needs to POST to a publicly
  reachable URL. Use the n8n tunnel (`n8n start --tunnel`) or a service like
  ngrok during development.
- **Model name.** The workflow uses `gpt-4o-mini` because it's cheap and
  fast. If your OpenAI account doesn't have access, change the model id on
  both AI nodes (Teacher + Examiner) to something you have, e.g. `gpt-4.1-mini`
  or `gpt-3.5-turbo`.
- **Updates list on the trigger.** The Telegram Trigger node must subscribe
  to BOTH `message` and `callback_query` updates — otherwise the quiz answer
  buttons won't reach the workflow.
