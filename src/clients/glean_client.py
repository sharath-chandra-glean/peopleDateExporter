"""Glean API Client for pushing people data."""
import logging
import uuid
from datetime import datetime
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
        disable_stale_data_deletion: bool = False,
    ):
        """
        Initialize Glean client.

        Args:
            api_url: Glean API base URL (e.g., https://api.glean.com)
            api_token: API token for authentication
            datasource: Datasource identifier
            timeout: Request timeout in seconds
            use_bulk_index: Use bulk indexing API (True) or individual indexing API (False)
            disable_stale_data_deletion: Disable automatic deletion of stale data in Glean
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.datasource = datasource
        self.timeout = timeout
        self.use_bulk_index = use_bulk_index
        self.disable_stale_data_deletion = disable_stale_data_deletion

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
        Transform Keycloak user data to Glean employee format.

        Supported Keycloak attributes (from attributes object):
        - department: Employee's department
        - title: Job title
        - businessUnit: Business unit
        - phoneNumber: Phone number
        - managerEmail: Manager's email address
        - bio: Employee biography
        - photoUrl: Profile photo URL

        Args:
            keycloak_user: User data from Keycloak

        Returns:
            Formatted employee data for Glean
        """
        email = keycloak_user.get("email", "")
        first_name = keycloak_user.get("firstName", "")
        last_name = keycloak_user.get("lastName", "")
        user_id = keycloak_user.get("id", "")
        enabled = keycloak_user.get("enabled", True)
        attributes = keycloak_user.get("attributes", {})
        
        employee_data = {}

        if email:
            employee_data["email"] = email
        
        if first_name:
            employee_data["firstName"] = first_name
        
        if last_name:
            employee_data["lastName"] = last_name
        
        if user_id:
            employee_data["id"] = email
        
        if attributes:
            if "department" in attributes and attributes["department"]:
                department_value = attributes["department"]
                if isinstance(department_value, list) and department_value:
                    employee_data["department"] = department_value[0]
                elif isinstance(department_value, str):
                    employee_data["department"] = department_value
            
            if "title" in attributes and attributes["title"]:
                title_value = attributes["title"]
                if isinstance(title_value, list) and title_value:
                    employee_data["title"] = title_value[0]
                elif isinstance(title_value, str):
                    employee_data["title"] = title_value
            
            if "businessUnit" in attributes and attributes["businessUnit"]:
                business_unit_value = attributes["businessUnit"]
                if isinstance(business_unit_value, list) and business_unit_value:
                    employee_data["businessUnit"] = business_unit_value[0]
                elif isinstance(business_unit_value, str):
                    employee_data["businessUnit"] = business_unit_value
            
            if "phoneNumber" in attributes and attributes["phoneNumber"]:
                phone_value = attributes["phoneNumber"]
                if isinstance(phone_value, list) and phone_value:
                    employee_data["phoneNumber"] = phone_value[0]
                elif isinstance(phone_value, str):
                    employee_data["phoneNumber"] = phone_value
            
            if "managerEmail" in attributes and attributes["managerEmail"]:
                manager_value = attributes["managerEmail"]
                if isinstance(manager_value, list) and manager_value:
                    employee_data["managerEmail"] = manager_value[0]
                    employee_data["managerId"] = manager_value[0]
                elif isinstance(manager_value, str):
                    employee_data["managerEmail"] = manager_value
                    employee_data["managerId"] = manager_value
            
            if "bio" in attributes and attributes["bio"]:
                bio_value = attributes["bio"]
                if isinstance(bio_value, list) and bio_value:
                    employee_data["bio"] = bio_value[0]
                elif isinstance(bio_value, str):
                    employee_data["bio"] = bio_value
            
            if "photoUrl" in attributes and attributes["photoUrl"]:
                photo_value = attributes["photoUrl"]
                if isinstance(photo_value, list) and photo_value:
                    employee_data["photoUrl"] = photo_value[0]
                elif isinstance(photo_value, str):
                    employee_data["photoUrl"] = photo_value
        
        employee_data["status"] = "CURRENT" if enabled else "FORMER"

        created_timestamp = keycloak_user.get("createdTimestamp")
        if created_timestamp:
            start_date = datetime.fromtimestamp(created_timestamp / 1000).strftime("%Y-%m-%d")
            employee_data["startDate"] = start_date

        return employee_data

    def index_employee(self, employee_data: Dict) -> Dict:
        """
        Index a single employee to Glean using the individual index API.

        Args:
            employee_data: Formatted employee data

        Returns:
            Response from Glean API
        """
        payload = {
            "employee": employee_data,
            "version": 0
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
            logger.error(f"Failed to index employee {employee_data.get('email', 'unknown')}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def bulk_index_employees(
        self,
        employees: List[Dict],
        upload_id: str = None,
        is_first_page: bool = True,
        is_last_page: bool = True,
        force_restart_upload: bool = False,
        disable_stale_data_deletion_check: bool = False,
    ) -> Dict:
        """
        Bulk index employees to Glean.

        Args:
            employees: List of formatted employee data
            upload_id: Optional upload identifier for multi-page uploads (auto-generated if not provided)
            is_first_page: Whether this is the first page of a multi-page upload
            is_last_page: Whether this is the last page of a multi-page upload
            force_restart_upload: Force restart of an existing upload
            disable_stale_data_deletion_check: Disable automatic deletion of stale data

        Returns:
            Response from Glean API
        """
        logger.info(f"Bulk indexing {len(employees)} employees to Glean")

        if not upload_id:
            upload_id = str(uuid.uuid4())
            logger.debug(f"Generated upload_id: {upload_id}")

        payload = {
            "uploadId": upload_id,
            "employees": employees,
            "isFirstPage": is_first_page,
            "isLastPage": is_last_page,
        }

        if force_restart_upload:
            payload["forceRestartUpload"] = force_restart_upload

        if disable_stale_data_deletion_check:
            payload["disableStaleDataDeletionCheck"] = disable_stale_data_deletion_check

        try:
            response = self.session.post(
                f"{self.api_url}/api/index/v1/bulkindexemployees",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            logger.info(f"Response from Glean: {response}")
            response.raise_for_status()
            logger.info("Successfully bulk indexed employees to Glean")
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bulk index employees to Glean: {e}")
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
            return self.bulk_index_employees(
                employees=users,
                disable_stale_data_deletion_check=self.disable_stale_data_deletion,
            )
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

