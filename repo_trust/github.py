"""
GitHub API interaction module for Repo Trust.

Handles all communication with the GitHub API for releases, assets, and uploads.
Includes retry logic, rate limiting awareness, and detailed error reporting.
"""

import os
import time
from typing import Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from repo_trust.logging import (
    debug, info, warning, error,
    GitHubAPIError, ConfigurationError
)


# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # seconds
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# Timeout configuration
CONNECT_TIMEOUT = 10  # seconds
READ_TIMEOUT = 60  # seconds for downloads


def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET", "POST", "DELETE"],
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


class GitHubAPI:
    """GitHub API client for Repo Trust operations."""
    
    def __init__(self):
        self.api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        self.server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        self.token = os.environ.get("GITHUB_TOKEN")
        self.repository = os.environ.get("GITHUB_REPOSITORY")
        
        # Validate required configuration
        if not self.token:
            raise ConfigurationError(
                "GITHUB_TOKEN environment variable is required",
                context={"hint": "This should be automatically provided by GitHub Actions"}
            )
        
        if not self.repository:
            raise ConfigurationError(
                "GITHUB_REPOSITORY environment variable is required",
                context={"hint": "This should be automatically provided by GitHub Actions"}
            )
        
        if "/" not in self.repository:
            raise ConfigurationError(
                "GITHUB_REPOSITORY must be in 'owner/repo' format",
                context={"value": self.repository}
            )
        
        self.owner, self.repo_name = self.repository.split("/", 1)
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-trust/1.0"
        }
        
        self.session = create_session()
        
        debug("GitHub API client initialized", 
              api_url=self.api_url, 
              repository=self.repository)
    
    def _api_url(self, path: str) -> str:
        """Construct full API URL for a given path."""
        return f"{self.api_url}/repos/{self.repository}/{path}"
    
    def _handle_response(self, response: requests.Response, operation: str) -> dict:
        """Handle API response with detailed error reporting."""
        
        # Check for rate limiting
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining and int(remaining) < 10:
            warning(f"GitHub API rate limit low: {remaining} requests remaining")
        
        # Handle specific status codes
        if response.status_code == 401:
            raise GitHubAPIError(
                "GitHub API authentication failed",
                context={
                    "operation": operation,
                    "hint": "Check that GITHUB_TOKEN has required permissions"
                }
            )
        
        if response.status_code == 403:
            # Check for rate limiting vs permission denied
            if "rate limit" in response.text.lower():
                reset_time = response.headers.get("X-RateLimit-Reset")
                raise GitHubAPIError(
                    "GitHub API rate limit exceeded",
                    context={
                        "operation": operation,
                        "reset_time": reset_time,
                        "hint": "Wait for rate limit reset or use a token with higher limits"
                    },
                    recoverable=True
                )
            else:
                raise GitHubAPIError(
                    "GitHub API access forbidden",
                    context={
                        "operation": operation,
                        "hint": "Check repository permissions and token scopes"
                    }
                )
        
        if response.status_code == 404:
            raise GitHubAPIError(
                f"GitHub resource not found: {operation}",
                context={
                    "operation": operation,
                    "url": response.url
                }
            )
        
        if response.status_code == 422:
            # Validation error - try to extract details
            try:
                details = response.json()
                message = details.get("message", "Validation failed")
                errors = details.get("errors", [])
            except Exception:
                message = response.text
                errors = []
            
            raise GitHubAPIError(
                f"GitHub API validation error: {message}",
                context={
                    "operation": operation,
                    "errors": str(errors) if errors else None
                }
            )
        
        if response.status_code >= 500:
            raise GitHubAPIError(
                f"GitHub API server error (HTTP {response.status_code})",
                context={
                    "operation": operation,
                    "hint": "GitHub may be experiencing issues. Try again later."
                },
                recoverable=True
            )
        
        if not response.ok:
            raise GitHubAPIError(
                f"GitHub API request failed (HTTP {response.status_code})",
                context={
                    "operation": operation,
                    "status_code": response.status_code,
                    "response": response.text[:200] if response.text else None
                }
            )
        
        # Success - parse JSON if present
        if response.text:
            try:
                return response.json()
            except ValueError:
                return {"raw": response.text}
        
        return {}
    
    def get_release_by_tag(self, tag: str) -> dict[str, Any]:
        """Fetch release information by tag name."""
        debug(f"Fetching release by tag", tag=tag)
        
        url = self._api_url(f"releases/tags/{tag}")
        response = self.session.get(
            url, 
            headers=self.headers, 
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        
        return self._handle_response(response, f"get_release_by_tag({tag})")
    
    def download_asset(self, asset_url: str, filename: str) -> str:
        """
        Download a release asset to a local file.
        
        Args:
            asset_url: The API URL for the asset (not browser URL)
            filename: Local filename to save to
            
        Returns:
            Path to downloaded file
        """
        debug(f"Downloading asset", filename=filename)
        
        # Use Accept header for binary content
        download_headers = {
            **self.headers,
            "Accept": "application/octet-stream"
        }
        
        try:
            response = self.session.get(
                asset_url,
                headers=download_headers,
                timeout=(CONNECT_TIMEOUT, 300),  # 5 min timeout for large files
                allow_redirects=True,
                stream=True
            )
            
            if not response.ok:
                self._handle_response(response, f"download_asset({filename})")
            
            # Stream to file for memory efficiency
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            actual_size = os.path.getsize(filename)
            debug(f"Download complete", filename=filename, size=actual_size)
            
            if total_size and actual_size != total_size:
                warning(f"Download size mismatch", 
                       expected=total_size, actual=actual_size, filename=filename)
            
            return filename
            
        except requests.exceptions.Timeout:
            raise GitHubAPIError(
                f"Download timed out for {filename}",
                context={"url": asset_url},
                recoverable=True
            )
        except requests.exceptions.ConnectionError as e:
            raise GitHubAPIError(
                f"Connection error downloading {filename}",
                context={"error": str(e)},
                recoverable=True
            )
    
    def upload_release_asset(self, release_id: int, filepath: str, 
                            content_type: str = "application/octet-stream") -> dict[str, Any]:
        """
        Upload an asset to a GitHub release.
        
        Args:
            release_id: The release ID to upload to
            filepath: Path to the file to upload
            content_type: MIME type of the file
            
        Returns:
            API response for the uploaded asset
        """
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        debug(f"Uploading release asset", filename=filename, size=file_size)
        
        # Get release info for upload URL
        release_url = self._api_url(f"releases/{release_id}")
        release_response = self.session.get(
            release_url, 
            headers=self.headers, 
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        release_data = self._handle_response(release_response, f"get_release({release_id})")
        
        # Check for existing asset with same name
        for asset in release_data.get("assets", []):
            if asset["name"] == filename:
                debug(f"Deleting existing asset", asset_id=asset["id"], filename=filename)
                delete_url = self._api_url(f"releases/assets/{asset['id']}")
                delete_response = self.session.delete(
                    delete_url, 
                    headers=self.headers, 
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                )
                if delete_response.status_code not in (204, 404):
                    warning(f"Could not delete existing asset", 
                           filename=filename, status=delete_response.status_code)
        
        # Construct upload URL
        upload_url = release_data["upload_url"].replace("{?name,label}", "")
        upload_url = f"{upload_url}?name={filename}"
        
        # Upload headers
        upload_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": content_type,
            "Content-Length": str(file_size)
        }
        
        try:
            with open(filepath, "rb") as f:
                response = self.session.post(
                    upload_url,
                    headers=upload_headers,
                    data=f,
                    timeout=(CONNECT_TIMEOUT, 300)  # 5 min for large uploads
                )
            
            result = self._handle_response(response, f"upload_asset({filename})")
            info(f"Asset uploaded successfully", filename=filename, size=file_size)
            return result
            
        except requests.exceptions.Timeout:
            raise GitHubAPIError(
                f"Upload timed out for {filename}",
                context={"size": file_size},
                recoverable=True
            )
    
    def get_pages_info(self) -> Optional[dict[str, Any]]:
        """Get GitHub Pages configuration for the repository."""
        debug("Checking GitHub Pages configuration")
        
        url = self._api_url("pages")
        response = self.session.get(
            url, 
            headers=self.headers, 
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        
        if response.status_code == 404:
            debug("GitHub Pages not configured for this repository")
            return None
        
        return self._handle_response(response, "get_pages_info")


# Module-level singleton for convenience
_api_instance: Optional[GitHubAPI] = None


def get_api() -> GitHubAPI:
    """Get or create the GitHub API instance."""
    global _api_instance
    if _api_instance is None:
        _api_instance = GitHubAPI()
    return _api_instance


def reset_api():
    """Reset the API instance (for testing)."""
    global _api_instance
    _api_instance = None
