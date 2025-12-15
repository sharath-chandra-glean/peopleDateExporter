"""Configuration management using environment variables."""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class KeycloakConfig:
    """Keycloak configuration."""
    base_url: str
    realm: str
    client_id: str
    client_secret: str
    timeout: int = 30


@dataclass
class GleanConfig:
    """Glean configuration."""
    api_url: str
    api_token: str
    datasource: str
    timeout: int = 30
    use_bulk_index: bool = True
    disable_stale_data_deletion: bool = False


@dataclass
class AppConfig:
    """Application configuration."""
    log_level: str = "INFO"
    dry_run: bool = False
    max_users: Optional[int] = None


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings from environment variables."""
        self.keycloak = self._load_keycloak_config()
        self.glean = self._load_glean_config()
        self.app = self._load_app_config()

    def _load_keycloak_config(self) -> KeycloakConfig:
        """Load Keycloak configuration."""
        required_vars = [
            "KEYCLOAK_BASE_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
            "KEYCLOAK_CLIENT_SECRET",
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return KeycloakConfig(
            base_url=os.getenv("KEYCLOAK_BASE_URL"),
            realm=os.getenv("KEYCLOAK_REALM"),
            client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
            client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
            timeout=int(os.getenv("KEYCLOAK_TIMEOUT", "30")),
        )

    def _load_glean_config(self) -> GleanConfig:
        """Load Glean configuration."""
        required_vars = [
            "GLEAN_API_URL",
            "GLEAN_API_TOKEN",
            "GLEAN_DATASOURCE",
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        use_bulk_index = os.getenv("GLEAN_USE_BULK_INDEX", "true").lower() in ("true", "1", "yes")
        disable_stale_data_deletion = os.getenv("GLEAN_DISABLE_STALE_DATA_DELETION", "false").lower() in ("true", "1", "yes")

        return GleanConfig(
            api_url=os.getenv("GLEAN_API_URL"),
            api_token=os.getenv("GLEAN_API_TOKEN"),
            datasource=os.getenv("GLEAN_DATASOURCE"),
            timeout=int(os.getenv("GLEAN_TIMEOUT", "30")),
            use_bulk_index=use_bulk_index,
            disable_stale_data_deletion=disable_stale_data_deletion,
        )

    def _load_app_config(self) -> AppConfig:
        """Load application configuration."""
        dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
        max_users_str = os.getenv("MAX_USERS")
        max_users = int(max_users_str) if max_users_str else None

        return AppConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            dry_run=dry_run,
            max_users=max_users,
        )


def load_settings() -> Settings:
    """Load and return application settings."""
    return Settings()

