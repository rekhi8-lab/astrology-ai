from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import date

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from ai.claude_client import generate_response
from config import settings
from ingestion.router import process_input
from memory.chroma_db import store_interaction
from memory.ranking import rank_context
from memory.retriever import retrieve_context
from storage.sheets_logger import log_entry
from utils.cost_tracker import estimate_cost
from utils.prompt_builder import build_prompt


logger = logging.getLogger(__name__)


class DailyBudget:
    def __init__(self) -> None:
        self._day = date.today()
        self._total_cost = 0.0
        self._count = 0

    def record(self, cost: float) -> tuple[bool, int, float]:
        today = date.today()
        if today != self._day:
            self._day = today
            self._total_cost = 0.0
            self._count = 0

        self._total_cost += cost
        self._count += 1
        exceeded = self._total_cost >= settings.daily_cost_limit
        return exceeded, self._count, self._total_cost


budget = DailyBudget()
user_failures: defaultdict[int, int] = defaultdict(int)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    try:
        raw_input = await process_input(message)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return
    except Exception:
        logger.exception("Failed to process inbound message")
        await message.reply_text("I couldn't read that input. Try a text message, image, PDF, or URL.")
        return

    if not raw_input.strip():
        await message.reply_text("I couldn't extract usable text from that message.")
        return

    try:
        chunks = await asyncio.wait_for(
            asyncio.to_thread(retrieve_context, raw_input),
            timeout=settings.max_retrieval_time,
        )
        ranked = rank_context(chunks)
    except Exception:
        logger.exception("Context retrieval failed")
        ranked = []

    prompt = build_prompt(raw_input, ranked)

    try:
        response, usage = await asyncio.wait_for(
            asyncio.to_thread(generate_response, prompt),
            timeout=settings.max_ai_time,
        )
    except asyncio.TimeoutError:
        await message.reply_text("The model took too long to respond. Please try again.")
        return

    cost = estimate_cost(usage)
    exceeded, count, total_cost = budget.record(cost)

    await message.reply_text(response)

    try:
        await asyncio.to_thread(
            store_interaction,
            user_input=raw_input,
            response=response,
            metadata={
                "type": "interaction",
                "user_id": str(user.id),
                "chat_id": str(update.effective_chat.id) if update.effective_chat else "unknown",
            },
        )
    except Exception:
        logger.exception("Failed to store interaction in Chroma")

    try:
        await asyncio.to_thread(log_entry, raw_input, response, cost)
    except Exception:
        logger.exception("Failed to log interaction to Sheets")

    if exceeded:
        await message.reply_text(
            f"Daily budget warning: today's tracked cost is about Rs. {total_cost:.2f}."
        )
    elif count % 10 == 0:
        await message.reply_text(
            f"Tracked cost for the latest {count} requests today: Rs. {total_cost:.2f}."
        )


def run() -> None:
    settings.require_runtime_secrets()
    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))
    logger.info("Starting Telegram polling")
    app.run_polling(drop_pending_updates=True)
