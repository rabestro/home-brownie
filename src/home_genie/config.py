"""Environment-driven configuration and multi-tenant RBAC provider for home-genie."""

import json
import os
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class UserPermissions(BaseModel):
    """Permissions and API tokens mapped to a specific family user."""

    name: str
    paperless_token: str | None = None
    github_token: str | None = None
    home_assistant_token: str | None = None
    cloudflare_token: str | None = None


class Config:
    """Configuration provider for home-genie."""

    TELEGRAM_BOT_TOKEN: str = ""
    PAPERLESS_URL: str = ""
    HOME_ASSISTANT_URL: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Mapping of Telegram user IDs to UserPermissions objects
    FAMILY_USERS: ClassVar[dict[int, UserPermissions]] = {}

    @classmethod
    def validate(cls) -> None:
        """Validates required environment variables and parses family user RBAC mappings.

        Raises:
            ValueError: If any required configuration is missing or invalid.
        """
        cls.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        cls.PAPERLESS_URL = os.environ.get("PAPERLESS_URL", "")
        cls.HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL", "")
        cls.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        cls.GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "gemini-3.1-flash-lite"

        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set!")

        raw_users = os.environ.get("FAMILY_USERS", "")
        if not raw_users:
            raise ValueError("FAMILY_USERS environment variable is not set!")

        try:
            users_dict = json.loads(raw_users)
            cls.FAMILY_USERS = {
                int(k): UserPermissions.model_validate(v) for k, v in users_dict.items()
            }
        except Exception as e:
            raise ValueError(f"Failed to parse FAMILY_USERS JSON mapping: {e}") from e

    @classmethod
    def get_user_permissions(cls, user_id: int) -> UserPermissions:
        """Retrieves permissions for a Telegram user ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            UserPermissions object.

        Raises:
            KeyError: If user_id is not authorized in FAMILY_USERS.
        """
        if user_id not in cls.FAMILY_USERS:
            raise KeyError(f"User ID {user_id} is not authorized.")
        return cls.FAMILY_USERS[user_id]
