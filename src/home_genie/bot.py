"""Telegram bot handlers and the create_bot() factory for home-genie."""

import logging
import os
import re
from datetime import UTC, datetime

from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from home_genie.agent import run_agent_query, run_archiving_agent
from home_genie.config import Config, UserPermissions
from home_genie.paperless import DuplicateDocumentError, PaperlessClient

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".webp", ".bmp"}
)

_TELEGRAM_MESSAGE_LIMIT = 4000
_DOC_TAG_RE = re.compile(r"\[#(\d+)\]")


def _chunk_text(text: str, limit: int = _TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Splits text into limit-sized chunks for Telegram delivery."""
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _extract_doc_ids(text: str) -> list[int]:
    """Returns unique document IDs from [#ID] markers."""
    seen: set[int] = set()
    doc_ids: list[int] = []
    for m in _DOC_TAG_RE.finditer(text):
        doc_id = int(m.group(1))
        if doc_id not in seen:
            seen.add(doc_id)
            doc_ids.append(doc_id)
    return doc_ids


def _build_doc_keyboard(doc_ids: list[int]) -> InlineKeyboardMarkup | None:
    """Builds InlineKeyboardMarkup with download buttons for doc IDs."""
    if not doc_ids:
        return None
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton(text=f"📥 #{doc_id}", callback_data=f"get_doc:{doc_id}")
        for doc_id in doc_ids
    ]
    keyboard.add(*buttons)
    return keyboard


def is_allowed(message: Message) -> bool:
    """Checks if sender is authorized in Config.FAMILY_USERS."""
    if message.from_user is None:
        return False
    return message.from_user.id in Config.FAMILY_USERS


def _get_accessible_systems_summary(perms: UserPermissions) -> str:
    """Generates accessible systems summary for user."""
    systems: list[str] = []
    if perms.paperless_token:
        systems.append("🏛 Paperless-ngx Archive")
    if perms.github_token:
        systems.append("📚 GitHub Wiki (Quartz)")
    if perms.home_assistant_token:
        systems.append("🏠 Home Assistant Smart Home")
    if perms.cloudflare_token:
        systems.append("☁️ Cloudflare Network")
    if perms.home_connect_token:
        systems.append("🔌 Home Connect Appliances")

    if not systems:
        return "⚠️ No active system permissions assigned."
    return "\n".join(f"• {s}" for s in systems)


async def send_welcome(message: Message, bot: AsyncTeleBot) -> None:
    """Sends welcome message explaining assistant capabilities."""
    if not is_allowed(message) or not message.from_user:
        await bot.reply_to(message, "⛔ Access Denied. You are not authorized to use Home Genie.")
        return

    perms = Config.get_user_permissions(message.from_user.id)
    summary = _get_accessible_systems_summary(perms)

    await bot.reply_to(
        message,
        f"🧞 Hello, {perms.name}! I am **Home Genie**, your personal AI assistant.\n\n"
        f"Connected Systems:\n{summary}\n\n"
        "Commands:\n"
        "• /get <doc_id> — Download PDF from Paperless archive\n\n"
        "Send me documents/photos to archive, or ask questions in plain text.",
    )


async def handle_get(message: Message, bot: AsyncTeleBot) -> None:
    """Downloads a document by Paperless ID and sends it as PDF."""
    if not is_allowed(message) or not message.from_user:
        return

    parts = (message.text or "").strip().split()
    if len(parts) != 2 or not parts[1].isdigit():  # noqa: PLR2004
        await bot.reply_to(message, "⚠️ Usage: /get <document_id>\nExample: /get 42")
        return

    doc_id = int(parts[1])
    perms = Config.get_user_permissions(message.from_user.id)
    if not perms.paperless_token:
        await bot.reply_to(message, "❌ You do not have Paperless archive permissions.")
        return

    status_msg = await bot.reply_to(message, f"📄 Fetching document #{doc_id}...")
    try:
        client = PaperlessClient(Config.PAPERLESS_URL, perms.paperless_token)
        info = await client.fetch_document_info(doc_id)
        if info is None:
            await bot.edit_message_text(
                f"❌ Document #{doc_id} not found.",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id,
            )
            return

        title = info.title or f"document_{doc_id}"
        orig_name = info.original_file_name or f"{doc_id}.pdf"
        caption = f"📄 {title}"
        if info.created_date:
            caption += f"\n📅 {info.created_date}"

        pdf_bytes = await client.download_pdf(doc_id)
        await bot.delete_message(chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        await bot.send_document(message.chat.id, document=(orig_name, pdf_bytes), caption=caption)
    except Exception as e:
        logger.exception("Error fetching document #%d", doc_id)
        await bot.edit_message_text(
            f"❌ Failed to fetch document #{doc_id}: {e}",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
        )


async def _archive_file(  # noqa: PLR0913
    bot: AsyncTeleBot,
    *,
    file_bytes: bytes,
    file_name: str,
    perms: UserPermissions,
    chat_id: int,
    status_message_id: int,
) -> None:
    """Uploads file to Paperless-ngx and runs archiving AI agent."""
    if not perms.paperless_token:
        await bot.edit_message_text(
            "❌ You do not have Paperless archive permissions.",
            chat_id=chat_id,
            message_id=status_message_id,
        )
        return

    client = PaperlessClient(Config.PAPERLESS_URL, perms.paperless_token)

    async def _report(status: str) -> None:
        await bot.edit_message_text(status, chat_id=chat_id, message_id=status_message_id)

    try:
        doc_id = await client.upload_and_wait_for_ocr(
            file_bytes=file_bytes,
            file_name=file_name,
            on_status=_report,
        )
        await _report("🧠 Analyzing document with AI...")

        agent_report = await run_archiving_agent(perms, doc_id, file_name)
        await bot.edit_message_text(
            "✅ Document successfully processed and archived!",
            chat_id=chat_id,
            message_id=status_message_id,
        )
        for chunk in _chunk_text(agent_report):
            await bot.send_message(chat_id, chunk)

    except DuplicateDocumentError as e:
        logger.info("Duplicate document detected: ID %d", e.doc_id)
        keyboard = _build_doc_keyboard([e.doc_id])
        await bot.edit_message_text(
            f"⚠️ This document already exists in archive as #{e.doc_id}.",
            chat_id=chat_id,
            message_id=status_message_id,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.exception("Error archiving file %s", file_name)
        await bot.edit_message_text(
            f"❌ Processing error: {e}",
            chat_id=chat_id,
            message_id=status_message_id,
        )


async def handle_document(message: Message, bot: AsyncTeleBot) -> None:
    """Handles document upload."""
    if not is_allowed(message) or not message.document or not message.from_user:
        return

    file_name = message.document.file_name or ""
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        await bot.reply_to(
            message,
            f"❌ Unsupported file extension '{ext}'. Accepted: PDF, JPG, PNG, GIF, WEBP, BMP.",
        )
        return

    status_msg = await bot.reply_to(message, "📥 Downloading file...")
    try:
        perms = Config.get_user_permissions(message.from_user.id)
        file_info = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        await _archive_file(
            bot,
            file_bytes=file_bytes,
            file_name=file_name,
            perms=perms,
            chat_id=message.chat.id,
            status_message_id=status_msg.message_id,
        )
    except Exception as e:
        logger.exception("Error downloading document")
        await bot.edit_message_text(
            f"❌ Error: {e}", chat_id=message.chat.id, message_id=status_msg.message_id
        )


async def handle_photo(message: Message, bot: AsyncTeleBot) -> None:
    """Handles direct photo upload."""
    if not is_allowed(message) or not message.photo or not message.from_user:
        return

    status_msg = await bot.reply_to(message, "📥 Downloading photo...")
    try:
        perms = Config.get_user_permissions(message.from_user.id)
        best = message.photo[-1]
        file_info = await bot.get_file(best.file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        caption_slug = (
            message.caption.strip().replace(" ", "_")[:40]
            if message.caption
            else datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        )
        file_name = f"{caption_slug}.jpg"
        await _archive_file(
            bot,
            file_bytes=file_bytes,
            file_name=file_name,
            perms=perms,
            chat_id=message.chat.id,
            status_message_id=status_msg.message_id,
        )
    except Exception as e:
        logger.exception("Error downloading photo")
        await bot.edit_message_text(
            f"❌ Error: {e}", chat_id=message.chat.id, message_id=status_msg.message_id
        )


async def handle_doc_button(call: CallbackQuery, bot: AsyncTeleBot) -> None:
    """Handles inline get_doc:<id> button callbacks."""
    if not call.from_user or call.from_user.id not in Config.FAMILY_USERS:
        await bot.answer_callback_query(call.id, "⛔ Not authorized.")
        return

    if not call.data or not call.message or not hasattr(call.message, "chat"):
        await bot.answer_callback_query(call.id, "⚠️ Invalid callback data.")
        return

    chat_id = call.message.chat.id
    doc_id = int(call.data.split(":", 1)[1])
    await bot.answer_callback_query(call.id, f"⬇️ Fetching document #{doc_id}...")

    perms = Config.get_user_permissions(call.from_user.id)
    if not perms.paperless_token:
        await bot.send_message(chat_id, "❌ No Paperless permissions.")
        return

    try:
        client = PaperlessClient(Config.PAPERLESS_URL, perms.paperless_token)
        info = await client.fetch_document_info(doc_id)
        if info is None:
            await bot.send_message(chat_id, f"❌ Document #{doc_id} not found.")
            return

        title = info.title or f"document_{doc_id}"
        orig_name = info.original_file_name or f"{doc_id}.pdf"
        caption = f"📄 {title}"
        if info.created_date:
            caption += f"\n📅 {info.created_date}"

        pdf_bytes = await client.download_pdf(doc_id)
        await bot.send_document(chat_id, document=(orig_name, pdf_bytes), caption=caption)
    except Exception as e:
        logger.exception("Error downloading doc #%d via button", doc_id)
        await bot.send_message(chat_id, f"❌ Download error: {e}")


async def handle_text_query(message: Message, bot: AsyncTeleBot) -> None:
    """Processes natural language text queries using AI agent."""
    if not is_allowed(message) or not message.from_user:
        return

    if not message.text or message.text.startswith("/"):
        return

    status_message = await bot.reply_to(message, "🧠 Querying assistant...")
    try:
        perms = Config.get_user_permissions(message.from_user.id)
        agent_report = await run_agent_query(perms, message.text)

        await bot.delete_message(
            chat_id=status_message.chat.id, message_id=status_message.message_id
        )

        doc_ids = _extract_doc_ids(agent_report)
        clean_text = _DOC_TAG_RE.sub("", agent_report).strip()
        keyboard = _build_doc_keyboard(doc_ids)
        chunks = _chunk_text(clean_text)

        for chunk in chunks[:-1]:
            await bot.send_message(message.chat.id, chunk)
        await bot.send_message(message.chat.id, chunks[-1], reply_markup=keyboard)

    except Exception as e:
        logger.exception("Error processing user text query")
        await bot.edit_message_text(
            f"❌ An error occurred: {e}",
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
        )


def create_bot(config: type[Config]) -> AsyncTeleBot:
    """Builds an AsyncTeleBot with all handlers registered."""
    bot = AsyncTeleBot(config.TELEGRAM_BOT_TOKEN)

    bot.register_message_handler(
        send_welcome,  # type: ignore[arg-type]
        commands=["start", "help"],
        pass_bot=True,
    )
    bot.register_message_handler(
        handle_get,  # type: ignore[arg-type]
        commands=["get"],
        pass_bot=True,
    )
    bot.register_message_handler(
        handle_document,  # type: ignore[arg-type]
        content_types=["document"],
        pass_bot=True,
    )
    bot.register_message_handler(
        handle_photo,  # type: ignore[arg-type]
        content_types=["photo"],
        pass_bot=True,
    )
    bot.register_message_handler(
        handle_text_query,  # type: ignore[arg-type]
        content_types=["text"],
        pass_bot=True,
    )
    bot.register_callback_query_handler(
        handle_doc_button,  # type: ignore[arg-type]
        func=lambda call: bool(call.data) and call.data.startswith("get_doc:"),
        pass_bot=True,
    )

    return bot
