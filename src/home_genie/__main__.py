"""Main entry point for running home-genie."""

import asyncio
import logging
import sys

from home_genie.bot import create_bot
from home_genie.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Validates configuration and starts the Telegram bot async polling loop."""
    logger.info("Starting Home Genie...")
    try:
        Config.validate()
    except Exception as e:
        logger.error("Configuration validation failed: %s", e)
        sys.exit(1)

    bot = create_bot(Config)
    logger.info("Home Genie initialized. Starting async polling...")
    await bot.polling(non_stop=True)


if __name__ == "__main__":
    asyncio.run(main())
