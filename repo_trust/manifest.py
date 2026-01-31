"""
Manifest generation module for Repo Trust.

Generates a signed manifest containing cryptographic hashes of all release artifacts.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from repo_trust.github import get_api
from repo_trust.signing import sign_file
from repo_trust.logging import (
    debug, info, warning, error, section, end_section,
    handle_errors, ConfigurationError, RepoTrustError
)


MANIFEST_FILENAME = "repo-trust-manifest.json"
MANIFEST_VERSION = "1.0"
GENERATOR_VERSION = "1.0.0"


def compute_sha256(filepath: str) -> str:
    """
    Compute SHA-256 hash of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def generate_manifest() -> tuple[dict[str, Any], int]:
    """
    Generate a Repo Trust manifest for the current release.
    
    Returns:
        Tuple of (manifest dict, artifact count)
    """
    api = get_api()
    
    # Get release information
    tag = os.environ.get("GITHUB_REF_NAME")
    if not tag:
        raise ConfigurationError(
            "GITHUB_REF_NAME environment variable is required",
            context={"hint": "This should be the release tag"}
        )
    
    commit_sha = os.environ.get("GITHUB_SHA", "")
    
    section(f"Fetching release: {tag}")
    release = api.get_release_by_tag(tag)
    debug("Release fetched", 
          release_id=release["id"], 
          tag=tag,
          created_at=release.get("created_at"))
    end_section()
    
    # Process each release asset
    artifacts = []
    assets = release.get("assets", [])
    
    # Filter out existing repo-trust files
    non_rt_assets = [a for a in assets if not a["name"].startswith("repo-trust-manifest")]
    asset_count = len(non_rt_assets)
    
    section(f"Processing {asset_count} release assets")
    
    if asset_count == 0:
        warning("Release has no artifacts to verify")
        warning("The manifest will be created but will list zero artifacts")
        warning("Consider adding release assets before running Repo Trust")
    
    for i, asset in enumerate(assets, 1):
        filename = asset["name"]
        
        # Skip existing repo-trust files
        if filename.startswith("repo-trust-manifest"):
            debug(f"Skipping existing manifest file", filename=filename)
            continue
        
        info(f"[{i}/{asset_count}] Processing: {filename}")
        
        try:
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
            
            debug(f"Asset processed",
                  filename=filename,
                  sha256=file_hash[:16] + "...",
                  size=file_size)
            
            # Clean up downloaded file
            os.remove(filename)
            
        except Exception as e:
            error(f"Failed to process asset: {filename}", error=str(e))
            raise RepoTrustError(
                f"Failed to process release asset: {filename}",
                context={"error": str(e)}
            )
    
    end_section()
    
    # Build manifest
    manifest = {
        "repo_trust_version": MANIFEST_VERSION,
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
            "version": GENERATOR_VERSION
        }
    }
    
    return manifest, len(artifacts)


@handle_errors
def main():
    """Generate and sign the Repo Trust manifest."""
    section("Generating Repo Trust Manifest")
    
    # Generate manifest
    manifest, artifact_count = generate_manifest()
    
    # Write manifest to file
    manifest_path = MANIFEST_FILENAME
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    info(f"Manifest written", path=manifest_path, size=os.path.getsize(manifest_path))
    
    # Sign the manifest
    section("Signing manifest")
    sig_path = sign_file(manifest_path)
    end_section()
    
    # Output summary
    section("Manifest generation complete")
    info(f"Repository: {manifest['repository']['full_name']}")
    info(f"Release: {manifest['release']['tag']}")
    info(f"Artifacts: {artifact_count}")
    info(f"Manifest: {manifest_path}")
    info(f"Signature: {sig_path}")
    end_section()


if __name__ == "__main__":
    main()
