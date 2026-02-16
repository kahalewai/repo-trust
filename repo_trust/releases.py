"""
Release data module for Repo Trust.

Fetches the latest release information from the GitHub API
and writes it as JSON for the pages module to embed in the
verified download page.
"""

import json
import os
import sys
import requests


def fetch_latest_release():
    """Fetch the latest release from the GitHub API."""
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")

    if not repository:
        print("[repo-trust] ERROR: GITHUB_REPOSITORY is required")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}" if token else "",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-trust/2.0",
    }

    # Try to get the specific release tag if triggered by a release event
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if tag:
        url = f"{api_url}/repos/{repository}/releases/tags/{tag}"
        print(f"[repo-trust] Fetching release: {tag}")
    else:
        url = f"{api_url}/repos/{repository}/releases/latest"
        print("[repo-trust] Fetching latest release")

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        print("[repo-trust] No releases found. The download page will be published without release assets.")
        print("[repo-trust] Create a release and re-run to populate downloads.")
        return None

    if not response.ok:
        print(f"[repo-trust] WARNING: GitHub API returned {response.status_code}")
        print(f"[repo-trust] Response: {response.text[:200]}")
        return None

    return response.json()


def format_size(size_bytes):
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def extract_release_data(release):
    """Extract relevant data from the GitHub API release response."""
    if release is None:
        return {
            "tag": None,
            "name": None,
            "published_at": None,
            "html_url": None,
            "assets": [],
        }

    assets = []
    for asset in release.get("assets", []):
        # Skip repo-trust files from previous runs
        if asset["name"].startswith("repo-trust-"):
            continue

        assets.append({
            "name": asset["name"],
            "size": asset.get("size", 0),
            "size_display": format_size(asset.get("size", 0)),
            "download_url": asset["browser_download_url"],
            "download_count": asset.get("download_count", 0),
        })

    return {
        "tag": release.get("tag_name", ""),
        "name": release.get("name", release.get("tag_name", "")),
        "published_at": release.get("published_at", ""),
        "html_url": release.get("html_url", ""),
        "assets": assets,
    }


def main():
    """Fetch release data and write to JSON file."""
    release = fetch_latest_release()
    data = extract_release_data(release)

    output_path = "release-data.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    if data["tag"]:
        print(f"[repo-trust] Release: {data['name']} ({data['tag']})")
        print(f"[repo-trust] Assets: {len(data['assets'])}")
    else:
        print("[repo-trust] No release data available")

    print(f"[repo-trust] Release data written to {output_path}")


if __name__ == "__main__":
    main()
