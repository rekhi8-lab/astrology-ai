from __future__ import annotations
from ephemeris.resolver import build_ephemeris_context

import asyncio
import logging
from collections import defaultdict
from datetime import date
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from ai.claude_client import generate_response
from config import settings
from ephemeris.loader import load_ephemeris_data
from ephemeris.parser import RAW_DIR, parse_ephemeris_pdf, save_ephemeris_data
from ephemeris.service import resolve_ephemeris
from ingestion.router import process_input
from memory.chroma_db import is_valid_memory, store_documents, store_interaction
from memory.insight_evolution import compare_insights
from memory.insight_extractor import extract_user_insight
from memory.ranking import rank_context
from memory.retriever import get_insight_sequence, get_recent_insights, get_relevant_insights, retrieve_context
from memory.trajectory import build_learning_trajectory
from memory.user_profiles import get_user_profile, update_user_profile
from storage.sheets_logger import log_entry
from utils.cost_tracker import estimate_cost
from utils.helpers import delete_file, ensure_directory
from utils.prompt_builder import build_prompt
from utils.reflection import generate_reflection


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
FIRST_PERSON_INDICATORS = (
    "i think",
    "i feel",
    "maybe",
    "it seems",
    "in my case",
)
REFLECTION_REPLY_PHRASES = (
    "this relates",
    "this connects",
    "i understand",
)


def has_topic_overlap(query: str, frequent_topics: list[str]) -> bool:
    lowered = query.lower()
    if any(topic in lowered for topic in frequent_topics):
        return True

    query_terms = {term for term in lowered.split() if len(term) > 2}
    for topic in frequent_topics:
        topic_terms = {term for term in topic.lower().split() if len(term) > 2}
        if query_terms & topic_terms:
            return True
    return False


def is_reflection_reply(user_message: str) -> bool:
    lowered = user_message.lower().strip()
    if len(lowered) <= 20:
        return False

    has_first_person = any(indicator in lowered for indicator in FIRST_PERSON_INDICATORS)
    has_reflection_phrase = any(phrase in lowered for phrase in REFLECTION_REPLY_PHRASES)
    return has_first_person or has_reflection_phrase


def should_extract_insight(user_message: str) -> bool:
    lowered = user_message.lower().strip()
    if len(lowered) <= 30:
        return False
    if lowered in {"yes", "yeah", "okay", "ok", "sure", "got it", "understood"}:
        return False
    return True


def handle_reflection_response(
    user_profile: dict,
    user_message: str,
    retrieved_context: list[dict],
    relevant_insights: list[dict],
    ephemeris_context: str,
) -> tuple[str, object | None]:
    context = "\n\n".join(
        f"[Reflection Context {index + 1}]\n{item['text']}"
        for index, item in enumerate(retrieved_context)
    )
    insights = "\n".join(
        f"- {item['metadata'].get('interpretation', item['text'])}"
        for item in relevant_insights[:2]
    )
    frequent_topics = ", ".join(user_profile.get("frequent_topics", [])) or "None yet"
    depth_preference = user_profile.get("depth_preference", "short")
    insights_section = (
        "Previously, the user expressed:\n" + insights
        if insights
        else "No directly relevant prior insights."
    )

    prompt = f"""
You are responding to a user's reflection, not a question.

Your role:
- Interpret their thinking.
- Expand it.
- Gently guide deeper insight.
- Avoid repeating definitions.

Response goals:
- Briefly acknowledge their reflection.
- Summarize the meaning of what they are expressing.
- Add one layer of deeper insight or a gentle correction if needed.
- End with one specific follow-up question.
- Compare the user's current reflection with their past insights.
- Highlight any shift, reinforcement, or contradiction when relevant.

User profile:
- Preferred depth: {depth_preference}
- Frequent topics: {frequent_topics}

User insights:
{insights_section}

Retrieved context:
{context or "No relevant prior reflection context found."}

Ephemeris context:
{ephemeris_context or "No ephemeris context matched."}

User reflection:
{user_message}
""".strip()

    return generate_response(prompt)


async def handle_upload_ephemeris(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    document = message.document
    if document is None or not (
        document.mime_type == "application/pdf"
        or (document.file_name or "").lower().endswith(".pdf")
    ):
        await message.reply_text("Attach a PDF with the /upload_ephemeris command in the caption.")
        return

    ensure_directory(RAW_DIR)
    target_path = RAW_DIR / (document.file_name or f"{document.file_id}.pdf")

    try:
        telegram_file = await context.bot.get_file(document.file_id)
        await telegram_file.download_to_drive(str(target_path))
        parsed = await asyncio.to_thread(parse_ephemeris_pdf, target_path)
        if not parsed:
            await message.reply_text("I could not parse usable ephemeris rows from that PDF.")
            return

        saved_paths = await asyncio.to_thread(save_ephemeris_data, parsed)
        load_ephemeris_data()
        saved_names = ", ".join(path.name for path in saved_paths)
        await message.reply_text(f"Ephemeris parsed successfully. Saved: {saved_names}")
    except Exception:
        logger.exception("Failed to upload ephemeris PDF")
        await message.reply_text("I couldn't parse that ephemeris PDF.")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if (message.caption or "").strip().startswith("/upload_ephemeris"):
        return

    file_path: str | None = None

    try:
        if message.text:
            processed_input = await asyncio.to_thread(process_input, message.text, None)
        elif message.photo:
            file_id = message.photo[-1].file_id
            temp_dir = Path("/tmp") if Path("/tmp").exists() else Path("tmp")
            ensure_directory(temp_dir)
            file_path = str(temp_dir / f"{file_id}.jpg")
            telegram_file = await context.bot.get_file(file_id)
            await telegram_file.download_to_drive(file_path)
            processed_input = await asyncio.to_thread(process_input, None, file_path)
        elif message.document and (
            (message.document.mime_type == "application/pdf")
            or (message.document.file_name or "").lower().endswith(".pdf")
        ):
            file_id = message.document.file_id
            temp_dir = Path("/tmp") if Path("/tmp").exists() else Path("tmp")
            ensure_directory(temp_dir)
            file_path = str(temp_dir / f"{file_id}.pdf")
            telegram_file = await context.bot.get_file(file_id)
            await telegram_file.download_to_drive(file_path)
            processed_input = await asyncio.to_thread(process_input, None, file_path)
        else:
            raise ValueError("Unsupported message type. Send text, an image, a PDF, or a link.")

        raw_input = processed_input.text
    except ValueError as exc:
        await message.reply_text(str(exc))
        return
    except Exception:
        logger.exception("Failed to process inbound message")
        await message.reply_text("Could not extract readable content from file")
        return
    finally:
        if file_path:
            delete_file(file_path)

    if not raw_input.strip():
        await message.reply_text("I couldn't extract usable text from that message.")
        return

    prior_topics = list(get_user_profile(user.id).get("frequent_topics", []))
    user_profile = update_user_profile(user.id, raw_input)
    timestamp = datetime.utcnow().isoformat()
    reflection_mode = is_reflection_reply(raw_input)

    # --- Astro detection ---
    _ASTRO_KEYWORDS = [
        "saturn", "jupiter", "mars", "venus", "mercury", "moon", "sun",
        "transit", "planet", "dasha", "astrology", "natal", "zodiac",
        "date", "202",
        "now", "right now", "currently", "these days", "this phase",
    ]
    is_astro_query = any(word in raw_input.lower() for word in _ASTRO_KEYWORDS)

    # --- Ephemeris gating ---
    if is_astro_query:
        ephemeris_context = await asyncio.to_thread(build_ephemeris_context, raw_input)
    else:
        ephemeris_context = None

    # --- Store memory ---
    if processed_input.should_store and is_valid_memory(raw_input) and not reflection_mode:
        try:
            await asyncio.to_thread(
                store_documents,
                raw_input,
                {
                    "type": processed_input.source_type,
                    "user_id": str(user.id),
                    "chat_id": str(update.effective_chat.id) if update.effective_chat else "unknown",
                    "stored_at": timestamp,
                },
            )
        except Exception:
            logger.exception("Failed to store inbound content in Chroma")

    if is_astro_query:
        ranked = []
        relevant_insights = []
    else:
        try:
            chunks = await asyncio.wait_for(
                asyncio.to_thread(retrieve_context, raw_input),
                timeout=settings.max_retrieval_time,
            )
            ranked = rank_context(chunks)[:2]

            relevant_insights = await asyncio.wait_for(
                asyncio.to_thread(get_relevant_insights, user.id, raw_input, 2),
                timeout=settings.max_retrieval_time,
            )
        except Exception:
            logger.exception("Context retrieval failed")
            ranked = []
            relevant_insights = []

    # --- Generate response ---
    try:
        if reflection_mode:
            response, usage = await asyncio.wait_for(
                asyncio.to_thread(
                    handle_reflection_response,
                    user_profile,
                    raw_input,
                    ranked,
                    relevant_insights,
                    ephemeris_context,
                ),
                timeout=settings.max_ai_time,
            )
        else:
            prompt = await asyncio.to_thread(
                build_prompt,
                raw_input,
                ranked,
                user_profile,
                relevant_insights,
                ephemeris_context,
            )
            max_tokens = 300 if is_astro_query else 800

            response, usage = await asyncio.wait_for(
                asyncio.to_thread(generate_response, prompt, max_tokens),
                timeout=settings.max_ai_time,
            )

    except asyncio.TimeoutError:
        await message.reply_text("The model took too long to respond. Please try again.")
        return

    if not reflection_mode and has_topic_overlap(raw_input, prior_topics):
        response = f"You've explored this topic before. Let's go deeper.\n\n{response}"

    if reflection_mode:
        final_response = response
    else:
        reflection = generate_reflection(user_profile, raw_input, response)
        final_response = response if not reflection else f"{response}\n\n{reflection}"

    cost = estimate_cost(usage)
    exceeded, count, total_cost = budget.record(cost)

    await message.reply_text(final_response)
    try:
        await asyncio.to_thread(
            store_interaction,
            user_input=raw_input,
            response=final_response,
            metadata={
                "type": "reflection" if reflection_mode else "interaction",
                "intent": "user_interpretation" if reflection_mode else "question_answer",
                "user_id": str(user.id),
                "chat_id": str(update.effective_chat.id) if update.effective_chat else "unknown",
                "stored_at": timestamp,
            },
        )
    except Exception:
        logger.exception("Failed to store interaction in Chroma")

    try:
        await asyncio.to_thread(log_entry, raw_input, final_response, cost)
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
    app.add_handler(CommandHandler("upload_ephemeris", handle_upload_ephemeris))
    app.add_handler(
        MessageHandler(
            filters.Document.PDF & filters.CaptionRegex(r"^/upload_ephemeris"),
            handle_upload_ephemeris,
        )
    )
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))
    logger.info("Starting Telegram polling")
    app.run_polling(drop_pending_updates=True)
