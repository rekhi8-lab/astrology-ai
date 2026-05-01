# Astrology AI Backend

Production-oriented Telegram + Claude + Chroma backend for a personal RAG assistant.

## Features

- Telegram bot interface for text, images, PDFs, and URLs
- Claude generation through the official `messages.create` pattern
- Persistent Chroma-backed retrieval memory
- Google Sheets logging that can be enabled or skipped via environment variables
- Railway-friendly process layout using `Procfile`

## Environment variables

Set these in Railway:

- `TELEGRAM_TOKEN`
- `CLAUDE_API_KEY`
- `CLAUDE_MODEL`
- `TOP_K`
- `MAX_RETRIEVAL_TIME`
- `MAX_AI_TIME`
- `DAILY_COST_LIMIT`
- `CHROMA_PATH`
- `CHROMA_COLLECTION`
- `GOOGLE_SHEET_NAME`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

`GOOGLE_SERVICE_ACCOUNT_JSON` should contain the full service account JSON as a single environment variable. If it is omitted, Sheets logging is disabled and the bot still runs.

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Railway

Use a worker deployment with start command:

```bash
python main.py
```
