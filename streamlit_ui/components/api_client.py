"""HTTP client for VibeJudge FastAPI backend."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


# Custom exceptions for API errors
class APIError(Exception):
    """Base exception for API errors."""

    pass


class AuthenticationError(APIError):
    """Raised when API key is invalid (HTTP 401)."""

    pass


class ValidationError(APIError):
    """Raised when request validation fails (HTTP 422)."""

    pass


class ResourceNotFoundError(APIError):
    """Raised when resource is not found (HTTP 404)."""

    pass


class ConflictError(APIError):
    """Raised when there's a conflict (HTTP 409)."""

    pass


class BudgetExceededError(APIError):
    """Raised when budget limit is exceeded (HTTP 402)."""

    pass


class RateLimitError(APIError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    pass


class ServerError(APIError):
    """Raised when server encounters an error (HTTP 500)."""

    pass


class ServiceUnavailableError(APIError):
    """Raised when service is unavailable (HTTP 503)."""

    pass


class BadRequestError(APIError):
    """Raised when request is malformed (HTTP 400)."""

    pass


class ConnectionTimeoutError(APIError):
    """Raised when connection times out."""

    pass


class APIClient:
    """HTTP client for VibeJudge FastAPI backend.

    This client handles all communication with the backend API, including:
    - Automatic X-API-Key header injection
    - Timeout configuration
    - Error handling and logging

    Attributes:
        base_url: The base URL of the FastAPI backend
        api_key: The API key for authentication
        session: The requests.Session instance with configured headers
        timeout: Default timeout in seconds for all requests
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 10) -> None:
        """Initialize the API client.

        Args:
            base_url: The base URL of the FastAPI backend (e.g., "http://localhost:8000")
            api_key: The API key for authentication
            timeout: Default timeout in seconds for all requests (default: 10)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Create session with X-API-Key header
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def handle_error(self, response: requests.Response) -> None:
        """Map HTTP status codes to user-friendly error messages.

        This method examines the HTTP status code and raises the appropriate
        custom exception with a user-friendly error message.

        Args:
            response: The HTTP response object from requests

        Raises:
            BadRequestError: For HTTP 400 (Bad Request)
            AuthenticationError: For HTTP 401 (Unauthorized)
            BudgetExceededError: For HTTP 402 (Payment Required)
            ResourceNotFoundError: For HTTP 404 (Not Found)
            ConflictError: For HTTP 409 (Conflict)
            ValidationError: For HTTP 422 (Unprocessable Entity)
            RateLimitError: For HTTP 429 (Too Many Requests)
            ServerError: For HTTP 500 (Internal Server Error)
            ServiceUnavailableError: For HTTP 503 (Service Unavailable)
            APIError: For any other error status code
        """
        status_code = response.status_code

        # Try to extract detail from response body
        try:
            error_detail = response.json().get("detail", "")
        except Exception:
            error_detail = ""

        # Map status codes to exceptions and messages
        if status_code == 400:
            message = "Bad request. Please check your input."
            logger.error(f"HTTP 400: {message} - {error_detail}")
            raise BadRequestError(message)

        elif status_code == 401:
            message = "Invalid API key. Please check your credentials."
            logger.error(f"HTTP 401: {message}")
            raise AuthenticationError(message)

        elif status_code == 402:
            message = "Budget limit exceeded. Increase your budget or reduce scope."
            logger.error(f"HTTP 402: {message} - {error_detail}")
            raise BudgetExceededError(message)

        elif status_code == 404:
            message = "Resource not found."
            logger.error(f"HTTP 404: {message} - {error_detail}")
            raise ResourceNotFoundError(message)

        elif status_code == 409:
            # Include detail in message for conflicts (e.g., "Analysis already running")
            if error_detail:
                message = f"Conflict: {error_detail}"
            else:
                message = "Conflict: The requested operation conflicts with the current state."
            logger.error(f"HTTP 409: {message}")
            raise ConflictError(message)

        elif status_code == 422:
            # Include validation details in message
            if error_detail:
                message = f"Validation error: {error_detail}"
            else:
                message = "Validation error: Please check your input."
            logger.error(f"HTTP 422: {message}")
            raise ValidationError(message)

        elif status_code == 429:
            message = "Rate limit exceeded. Please try again later."
            logger.error(f"HTTP 429: {message}")
            raise RateLimitError(message)

        elif status_code == 500:
            message = "Server error. Please try again."
            logger.error(f"HTTP 500: {message} - {error_detail}")
            raise ServerError(message)

        elif status_code == 503:
            message = "Service unavailable. Please try again later."
            logger.error(f"HTTP 503: {message} - {error_detail}")
            raise ServiceUnavailableError(message)

        else:
            # Generic error for other status codes
            message = f"API error (HTTP {status_code}). Please try again."
            logger.error(f"HTTP {status_code}: {message} - {error_detail}")
            raise APIError(message)

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a GET request to the backend API.

        Args:
            endpoint: The API endpoint (e.g., "/hackathons")
            params: Optional query parameters

        Returns:
            The JSON response as a dictionary

        Raises:
            ConnectionTimeoutError: When connection times out
            ServiceUnavailableError: When connection fails
            APIError: For HTTP errors (mapped to specific exception types)
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"GET {url} with params={params}")

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Check for HTTP errors and handle them
            if not response.ok:
                self.handle_error(response)

            return response.json()
        except requests.Timeout as err:
            message = "Connection timeout. Please check your network."
            logger.error(f"Timeout error for GET {url}: {message}")
            raise ConnectionTimeoutError(message) from err
        except requests.ConnectionError as err:
            message = "Service unavailable. Cannot connect to server."
            logger.error(f"Connection error for GET {url}: {message}")
            raise ServiceUnavailableError(message) from err

    def post(self, endpoint: str, json: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request to the backend API.

        Args:
            endpoint: The API endpoint (e.g., "/hackathons")
            json: The JSON payload to send

        Returns:
            The JSON response as a dictionary

        Raises:
            ConnectionTimeoutError: When connection times out
            ServiceUnavailableError: When connection fails
            APIError: For HTTP errors (mapped to specific exception types)
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"POST {url} with json={json}")

        try:
            response = self.session.post(url, json=json, timeout=self.timeout)

            # Check for HTTP errors and handle them
            if not response.ok:
                self.handle_error(response)

            return response.json()
        except requests.Timeout as err:
            message = "Connection timeout. Please check your network."
            logger.error(f"Timeout error for POST {url}: {message}")
            raise ConnectionTimeoutError(message) from err
        except requests.ConnectionError as err:
            message = "Service unavailable. Cannot connect to server."
            logger.error(f"Connection error for POST {url}: {message}")
            raise ServiceUnavailableError(message) from err

    def delete(self, endpoint: str) -> bool:
        """Send a DELETE request to the backend API.

        Args:
            endpoint: The API endpoint (e.g., "/hackathons/123")

        Returns:
            True if deletion was successful (HTTP 204)

        Raises:
            ConnectionTimeoutError: When connection times out
            ServiceUnavailableError: When connection fails
            APIError: For HTTP errors (mapped to specific exception types)
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"DELETE {url}")

        try:
            response = self.session.delete(url, timeout=self.timeout)

            # Check for HTTP errors and handle them
            if not response.ok:
                self.handle_error(response)

            return response.status_code == 204
        except requests.Timeout as err:
            message = "Connection timeout. Please check your network."
            logger.error(f"Timeout error for DELETE {url}: {message}")
            raise ConnectionTimeoutError(message) from err
        except requests.ConnectionError as err:
            message = "Service unavailable. Cannot connect to server."
            logger.error(f"Connection error for DELETE {url}: {message}")
            raise ServiceUnavailableError(message) from err
