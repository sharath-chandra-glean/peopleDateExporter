"""Main orchestration script for syncing Keycloak data to Glean."""
import logging
import sys

from src.clients.keycloak_client import KeycloakClient
from src.clients.glean_client import GleanClient
from src.config.settings import load_settings
from src.utils.logger import setup_logging


logger = logging.getLogger(__name__)


class PeopleDataExporter:
    """Orchestrates data export from Keycloak to Glean."""

    def __init__(self):
        """Initialize the exporter with configuration."""
        self.settings = load_settings()
        setup_logging(self.settings.app.log_level)
        
        self.keycloak_client = KeycloakClient(
            base_url=self.settings.keycloak.base_url,
            realm=self.settings.keycloak.realm,
            client_id=self.settings.keycloak.client_id,
            client_secret=self.settings.keycloak.client_secret,
            timeout=self.settings.keycloak.timeout,
        )
        
        self.glean_client = GleanClient(
            api_url=self.settings.glean.api_url,
            api_token=self.settings.glean.api_token,
            datasource=self.settings.glean.datasource,
            timeout=self.settings.glean.timeout,
            use_bulk_index=self.settings.glean.use_bulk_index,
        )

    def sync_users(self) -> int:
        """
        Fetch users from Keycloak and push to Glean.

        Returns:
            Number of users synced
        """
        logger.info("Starting user sync")
        
        users = self.keycloak_client.get_users(
            max_users=self.settings.app.max_users
        )
        
        if not users:
            logger.warning("No users found in Keycloak")
            return 0

        glean_users = [
            self.glean_client.format_user_for_glean(user)
            for user in users
        ]

        if self.settings.app.dry_run:
            logger.info(f"DRY RUN: Would push {len(glean_users)} users to Glean")
            logger.debug(f"Sample user data: {glean_users[0] if glean_users else 'N/A'}")
            return len(glean_users)

        self.glean_client.push_users(glean_users)
        logger.info(f"Successfully synced {len(glean_users)} users")
        return len(glean_users)

    def sync_groups(self) -> int:
        """
        Fetch groups from Keycloak and push to Glean as teams.

        Returns:
            Number of groups synced
        """
        logger.info("Starting groups sync")
        
        groups = self.keycloak_client.get_groups()
        
        if not groups:
            logger.warning("No groups found in Keycloak")
            return 0

        users = self.keycloak_client.get_users()
        user_email_map = {
            user["id"]: user.get("email", "")
            for user in users
            if user.get("email")
        }

        glean_teams = []
        for group in groups:
            group_id = group.get("id")
            if not group_id:
                continue

            try:
                members = self.keycloak_client.get_user_groups(group_id)
                member_emails = [
                    user_email_map.get(member["id"])
                    for member in members
                    if member.get("id") in user_email_map
                ]
                
                team = self.glean_client.format_group_for_glean(
                    group, member_emails
                )
                glean_teams.append(team)
            except Exception as e:
                logger.error(f"Failed to process group {group.get('name')}: {e}")
                continue

        if not glean_teams:
            logger.warning("No teams to sync")
            return 0

        if self.settings.app.dry_run:
            logger.info(f"DRY RUN: Would push {len(glean_teams)} teams to Glean")
            logger.debug(f"Sample team data: {glean_teams[0] if glean_teams else 'N/A'}")
            return len(glean_teams)

        self.glean_client.push_teams(glean_teams)
        logger.info(f"Successfully synced {len(glean_teams)} teams")
        return len(glean_teams)

    def run(self) -> None:
        """Run the complete sync process."""
        logger.info("=" * 60)
        logger.info("People Data Exporter - Starting sync")
        logger.info(f"Indexing mode: {'BULK' if self.settings.glean.use_bulk_index else 'INDIVIDUAL'}")
        logger.info("=" * 60)
        
        try:
            self.keycloak_client.authenticate()
            
            users_synced = self.sync_users()
            groups_synced = self.sync_groups()
            
            logger.info("=" * 60)
            logger.info("Sync completed successfully")
            logger.info(f"  Users synced: {users_synced}")
            logger.info(f"  Groups synced: {groups_synced}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.keycloak_client.close()
            self.glean_client.close()


def main():
    """Entry point for the application."""
    try:
        exporter = PeopleDataExporter()
        exporter.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

