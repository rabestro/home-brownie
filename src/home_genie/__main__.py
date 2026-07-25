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
    except Exception:
        logger.exception("Configuration validation failed")
        sys.exit(1)

    bot = create_bot(Config)
    logger.info("Home Genie initialized. Starting async polling...")
    while True:
        try:
            await bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception:
            logger.exception("Polling error encountered. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
