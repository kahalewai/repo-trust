"""
Manifest generation module for Repo Trust.

Generates a signed manifest containing cryptographic hashes of all release artifacts.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from repo_trust.github import get_api
from repo_trust.signing import sign_file


def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def generate_manifest() -> dict[str, Any]:
    """
    Generate a Repo Trust manifest for the current release.
    
    Returns:
        The manifest dictionary
    """
    api = get_api()
    
    # Get release information
    tag = os.environ.get("GITHUB_REF_NAME")
    if not tag:
        raise ValueError("GITHUB_REF_NAME environment variable is required")
    
    commit_sha = os.environ.get("GITHUB_SHA", "")
    
    print(f"[repo-trust] Fetching release: {tag}")
    release = api.get_release_by_tag(tag)
    
    # Process each release asset
    artifacts = []
    
    print(f"[repo-trust] Found {len(release.get('assets', []))} release assets")
    
    for asset in release.get("assets", []):
        filename = asset["name"]
        
        # Skip existing repo-trust files
        if filename.startswith("repo-trust-manifest"):
            print(f"[repo-trust] Skipping existing manifest file: {filename}")
            continue
        
        print(f"[repo-trust] Processing: {filename}")
        
        # Download the asset
        download_url = asset["url"]  # API URL for authenticated download
        api.download_asset(download_url, filename)
        
        # Compute hash
        file_hash = compute_sha256(filename)
        file_size = os.path.getsize(filename)
        
        artifacts.append({
            "filename": filename,
            "sha256": file_hash,
            "size_bytes": file_size,
            "download_url": asset["browser_download_url"]
        })
        
        print(f"[repo-trust]   SHA-256: {file_hash}")
        print(f"[repo-trust]   Size: {file_size} bytes")
        
        # Clean up downloaded file
        os.remove(filename)
    
    # Build manifest
    manifest = {
        "repo_trust_version": "1.0",
        "repository": {
            "owner": api.owner,
            "name": api.repo_name,
            "full_name": api.repository,
            "git_url": f"{api.server_url}/{api.repository}"
        },
        "release": {
            "tag": tag,
            "commit": commit_sha,
            "published_at": release.get("published_at", ""),
            "release_id": release["id"]
        },
        "artifacts": artifacts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": {
            "name": "repo-trust",
            "version": "1.0.0"
        }
    }
    
    return manifest


def main():
    """Generate and sign the Repo Trust manifest."""
    try:
        # Generate manifest
        manifest = generate_manifest()
        
        # Write manifest to file
        manifest_path = "repo-trust-manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"[repo-trust] Manifest written to: {manifest_path}")
        
        # Sign the manifest
        sig_path = sign_file(manifest_path)
        print(f"[repo-trust] Signature written to: {sig_path}")
        
        # Output summary
        print(f"[repo-trust] Manifest generation complete")
        print(f"[repo-trust]   Repository: {manifest['repository']['full_name']}")
        print(f"[repo-trust]   Release: {manifest['release']['tag']}")
        print(f"[repo-trust]   Artifacts: {len(manifest['artifacts'])}")
        
    except Exception as e:
        print(f"[repo-trust] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
