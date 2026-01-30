"""
GitHub API interaction module for Repo Trust.

Handles all communication with the GitHub API for releases, assets, and uploads.
"""

import os
import sys
from typing import Any, Optional
import requests


class GitHubAPI:
    """GitHub API client for Repo Trust operations."""
    
    def __init__(self):
        self.api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        self.server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        self.token = os.environ.get("GITHUB_TOKEN")
        self.repository = os.environ.get("GITHUB_REPOSITORY")
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not self.repository:
            raise ValueError("GITHUB_REPOSITORY environment variable is required")
        
        self.owner, self.repo_name = self.repository.split("/")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def _api_url(self, path: str) -> str:
        """Construct full API URL for a given path."""
        return f"{self.api_url}/repos/{self.repository}/{path}"
    
    def get_release_by_tag(self, tag: str) -> dict[str, Any]:
        """Fetch release information by tag name."""
        url = self._api_url(f"releases/tags/{tag}")
        response = requests.get(url, headers=self.headers, timeout=30)
        
        if response.status_code == 404:
            raise ValueError(f"Release with tag '{tag}' not found")
        
        response.raise_for_status()
        return response.json()
    
    def download_asset(self, asset_url: str, filename: str) -> str:
        """Download a release asset to a local file."""
        # Use the asset URL directly with Accept header for binary content
        download_headers = {
            **self.headers,
            "Accept": "application/octet-stream"
        }
        
        response = requests.get(
            asset_url, 
            headers=download_headers, 
            timeout=300,
            allow_redirects=True
        )
        response.raise_for_status()
        
        with open(filename, "wb") as f:
            f.write(response.content)
        
        return filename
    
    def upload_release_asset(self, release_id: int, filepath: str, content_type: str = "application/json") -> dict[str, Any]:
        """Upload an asset to a GitHub release."""
        filename = os.path.basename(filepath)
        
        # Get upload URL from release
        release_url = self._api_url(f"releases/{release_id}")
        release_response = requests.get(release_url, headers=self.headers, timeout=30)
        release_response.raise_for_status()
        release_data = release_response.json()
        
        # Construct upload URL (remove template part)
        upload_url = release_data["upload_url"].replace("{?name,label}", "")
        upload_url = f"{upload_url}?name={filename}"
        
        # Check if asset already exists and delete it
        for asset in release_data.get("assets", []):
            if asset["name"] == filename:
                delete_url = self._api_url(f"releases/assets/{asset['id']}")
                delete_response = requests.delete(delete_url, headers=self.headers, timeout=30)
                if delete_response.status_code not in (204, 404):
                    print(f"[repo-trust] Warning: Could not delete existing asset: {delete_response.status_code}")
        
        # Upload new asset
        upload_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": content_type
        }
        
        with open(filepath, "rb") as f:
            response = requests.post(
                upload_url,
                headers=upload_headers,
                data=f,
                timeout=300
            )
        
        response.raise_for_status()
        return response.json()
    
    def get_pages_info(self) -> Optional[dict[str, Any]]:
        """Get GitHub Pages configuration for the repository."""
        url = self._api_url("pages")
        response = requests.get(url, headers=self.headers, timeout=30)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.json()


# Module-level singleton for convenience
_api_instance: Optional[GitHubAPI] = None


def get_api() -> GitHubAPI:
    """Get or create the GitHub API instance."""
    global _api_instance
    if _api_instance is None:
        _api_instance = GitHubAPI()
    return _api_instance
