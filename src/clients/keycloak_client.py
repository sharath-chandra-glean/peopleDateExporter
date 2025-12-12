"""Keycloak API Client for fetching user and group data."""
import logging
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class KeycloakClient:
    """Client for interacting with Keycloak Admin API."""

    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout: int = 30,
    ):
        """
        Initialize Keycloak client.

        Args:
            base_url: Keycloak server URL (e.g., https://keycloak.example.com)
            realm: Keycloak realm name
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.access_token: Optional[str] = None

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_token_url(self) -> str:
        """Get the token endpoint URL."""
        return f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

    def _get_admin_url(self) -> str:
        """Get the admin API base URL."""
        return f"{self.base_url}/admin/realms/{self.realm}"

    def authenticate(self) -> None:
        """Authenticate and obtain access token."""
        logger.info("Authenticating with Keycloak")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            response = self.session.post(
                self._get_token_url(),
                data=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Successfully authenticated with Keycloak")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with Keycloak: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token."""
        if not self.access_token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_users(self, max_users: Optional[int] = None) -> List[Dict]:
        """
        Fetch all users from Keycloak.

        Args:
            max_users: Maximum number of users to fetch (None for all)

        Returns:
            List of user dictionaries
        """
        logger.info("Fetching users from Keycloak")
        users = []
        first = 0
        batch_size = 100

        try:
            while True:
                params = {"first": first, "max": batch_size}
                response = self.session.get(
                    f"{self._get_admin_url()}/users",
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                batch = response.json()

                if not batch:
                    break

                users.extend(batch)
                logger.debug(f"Fetched {len(batch)} users (total: {len(users)})")

                if max_users and len(users) >= max_users:
                    users = users[:max_users]
                    break

                if len(batch) < batch_size:
                    break

                first += batch_size

            logger.info(f"Successfully fetched {len(users)} users")
            return users

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch users: {e}")
            raise

    def get_user_groups(self, user_id: str) -> List[Dict]:
        """
        Fetch groups for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of group dictionaries
        """
        try:
            response = self.session.get(
                f"{self._get_admin_url()}/users/{user_id}/groups",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch groups for user {user_id}: {e}")
            raise

    def get_groups(self) -> List[Dict]:
        """
        Fetch all groups from Keycloak.

        Returns:
            List of group dictionaries
        """
        logger.info("Fetching groups from Keycloak")
        
        try:
            response = self.session.get(
                f"{self._get_admin_url()}/groups",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            groups = response.json()
            logger.info(f"Successfully fetched {len(groups)} groups")
            return groups
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch groups: {e}")
            raise

    def close(self) -> None:
        """Close the session."""
        self.session.close()

