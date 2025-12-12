"""Glean API Client for pushing people data."""
import logging
from typing import Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class GleanClient:
    """Client for interacting with Glean People API."""

    def __init__(
        self,
        api_url: str,
        api_token: str,
        datasource: str,
        timeout: int = 30,
        use_bulk_index: bool = True,
    ):
        """
        Initialize Glean client.

        Args:
            api_url: Glean API base URL (e.g., https://api.glean.com)
            api_token: API token for authentication
            datasource: Datasource identifier
            timeout: Request timeout in seconds
            use_bulk_index: Use bulk indexing API (True) or individual indexing API (False)
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.datasource = datasource
        self.timeout = timeout
        self.use_bulk_index = use_bulk_index

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def format_user_for_glean(self, keycloak_user: Dict) -> Dict:
        """
        Transform Keycloak user data to Glean format.

        Args:
            keycloak_user: User data from Keycloak

        Returns:
            Formatted user data for Glean
        """
        email = keycloak_user.get("email", "")
        first_name = keycloak_user.get("firstName", "")
        last_name = keycloak_user.get("lastName", "")
        
        user_data = {
            "email": email,
            "name": f"{first_name} {last_name}".strip() or email,
            "datasource": self.datasource,
        }

        if first_name:
            user_data["firstName"] = first_name
        if last_name:
            user_data["lastName"] = last_name
        if keycloak_user.get("username"):
            user_data["username"] = keycloak_user["username"]
        if keycloak_user.get("attributes"):
            user_data["customAttributes"] = keycloak_user["attributes"]

        return user_data

    def index_employee(self, user: Dict) -> Dict:
        """
        Index a single employee to Glean using the individual index API.

        Args:
            user: Formatted user data

        Returns:
            Response from Glean API
        """
        payload = {
            "datasource": self.datasource,
            "employee": user,
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/index/v1/indexemployee",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to index employee {user.get('email', 'unknown')}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def bulk_index_employees(self, users: List[Dict]) -> Dict:
        """
        Bulk index employees to Glean.

        Args:
            users: List of formatted user data

        Returns:
            Response from Glean API
        """
        logger.info(f"Bulk indexing {len(users)} users to Glean")

        payload = {
            "datasource": self.datasource,
            "users": users,
            "isFullPush": True,
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/index/v1/people/bulkindexemployees",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Successfully bulk indexed users to Glean")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bulk index users to Glean: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def push_users(self, users: List[Dict]) -> Dict:
        """
        Push users to Glean using either bulk or individual indexing.

        Args:
            users: List of formatted user data

        Returns:
            Response from Glean API (or summary for individual indexing)
        """
        if self.use_bulk_index:
            return self.bulk_index_employees(users)
        else:
            logger.info(f"Individually indexing {len(users)} users to Glean")
            results = {
                "total": len(users),
                "successful": 0,
                "failed": 0,
                "errors": []
            }

            for idx, user in enumerate(users, 1):
                try:
                    self.index_employee(user)
                    results["successful"] += 1
                    if idx % 10 == 0:
                        logger.info(f"Progress: {idx}/{len(users)} users indexed")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "email": user.get("email", "unknown"),
                        "error": str(e)
                    })
                    logger.warning(f"Failed to index user {user.get('email', 'unknown')}: {e}")

            logger.info(
                f"Individual indexing completed: "
                f"{results['successful']} successful, {results['failed']} failed"
            )
            return results

    def push_teams(self, teams: List[Dict]) -> Dict:
        """
        Push teams/groups to Glean.

        Args:
            teams: List of formatted team data

        Returns:
            Response from Glean API
        """
        logger.info(f"Pushing {len(teams)} teams to Glean")

        payload = {
            "datasource": self.datasource,
            "teams": teams,
            "isFullPush": True,
        }

        try:
            response = self.session.post(
                f"{self.api_url}/api/index/v1/people/bulkindexteams",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Successfully pushed teams to Glean")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to push teams to Glean: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def format_group_for_glean(self, keycloak_group: Dict, member_emails: List[str]) -> Dict:
        """
        Transform Keycloak group data to Glean team format.

        Args:
            keycloak_group: Group data from Keycloak
            member_emails: List of member email addresses

        Returns:
            Formatted team data for Glean
        """
        team_data = {
            "name": keycloak_group.get("name", ""),
            "datasource": self.datasource,
            "members": [{"email": email} for email in member_emails if email],
        }

        if keycloak_group.get("id"):
            team_data["externalId"] = keycloak_group["id"]

        return team_data

    def close(self) -> None:
        """Close the session."""
        self.session.close()

