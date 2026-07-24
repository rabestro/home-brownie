"""Telegram bot handlers and the create_bot() factory for home-genie."""

import logging

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from home_genie.agent import run_agent_query
from home_genie.config import Config, UserPermissions

logger = logging.getLogger(__name__)

# Telegram message length cap
_TELEGRAM_MESSAGE_LIMIT = 4000


def _chunk_text(text: str, limit: int = _TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Splits text into limit-sized chunks for Telegram delivery.

    Args:
        text: The text to split.
        limit: Maximum characters per chunk.

    Returns:
        List of text chunks.
    """
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def is_allowed(message: Message) -> bool:
    """Checks if the sender of the message is authorized to use home-genie.

    Args:
        message: The received Telegram message.

    Returns:
        True if the user is authorized in Config.FAMILY_USERS, False otherwise.
    """
    if message.from_user is None:
        return False
    return message.from_user.id in Config.FAMILY_USERS


def _get_accessible_systems_summary(perms: UserPermissions) -> str:
    """Generates a summary of systems accessible to the user based on their tokens.

    Args:
        perms: The user's UserPermissions.

    Returns:
        Formatted summary string with emoji icons.
    """
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
    """Sends a welcome message explaining available assistant capabilities.

    Args:
        message: The received Telegram message.
        bot: The bot instance (injected by telebot via pass_bot).
    """
    if not is_allowed(message) or not message.from_user:
        await bot.reply_to(message, "⛔ Access Denied. You are not authorized to use Home Genie.")
        return

    perms = Config.get_user_permissions(message.from_user.id)
    summary = _get_accessible_systems_summary(perms)

    await bot.reply_to(
        message,
        f"🧞 Hello, {perms.name}! I am **Home Genie**, your personal AI assistant.\n\n"
        f"Connected Systems:\n{summary}\n\n"
        "Ask me anything in plain text or voice messages\n"
        "(e.g. 'Search roof repair docs' or 'Turn on kitchen lights').",
    )


async def handle_text_query(message: Message, bot: AsyncTeleBot) -> None:
    """Processes natural language text queries using the AI agent.

    Args:
        message: The received Telegram message.
        bot: The bot instance (injected by telebot via pass_bot).
    """
    if not is_allowed(message) or not message.from_user:
        return

    if not message.text or message.text.startswith("/"):
        return

    status_message = await bot.reply_to(message, "🧠 Processing query with AI...")

    try:
        perms = Config.get_user_permissions(message.from_user.id)
        agent_report = await run_agent_query(perms, message.text)

        await bot.delete_message(
            chat_id=status_message.chat.id, message_id=status_message.message_id
        )

        for chunk in _chunk_text(agent_report):
            await bot.send_message(message.chat.id, chunk)

    except Exception as e:
        logger.exception("Error processing user text query")
        await bot.edit_message_text(
            f"❌ An error occurred: {e}",
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
        )


def create_bot(config: type[Config]) -> AsyncTeleBot:
    """Builds an AsyncTeleBot with all handlers registered.

    Args:
        config: The validated configuration providing the bot token.

    Returns:
        A configured AsyncTeleBot ready to start polling.
    """
    bot = AsyncTeleBot(config.TELEGRAM_BOT_TOKEN)

    bot.register_message_handler(
        send_welcome,  # type: ignore[arg-type]
        commands=["start", "help"],
        pass_bot=True,
    )
    bot.register_message_handler(
        handle_text_query,  # type: ignore[arg-type]
        content_types=["text"],
        pass_bot=True,
    )

    return bot
