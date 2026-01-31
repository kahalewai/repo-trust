"""
Upload module for Repo Trust.

Handles uploading the signed manifest to GitHub Releases.
"""

import json
import os

from repo_trust.github import get_api
from repo_trust.logging import (
    debug, info, warning, error, section, end_section,
    handle_errors, RepoTrustError
)


MANIFEST_FILENAME = "repo-trust-manifest.json"
SIGNATURE_FILENAME = "repo-trust-manifest.json.sig"


def upload_manifest() -> None:
    """
    Upload the signed manifest and signature to the GitHub release.
    
    Raises:
        RepoTrustError: If upload fails
    """
    api = get_api()
    
    # Check files exist
    if not os.path.exists(MANIFEST_FILENAME):
        raise RepoTrustError(
            f"Manifest not found: {MANIFEST_FILENAME}",
            context={"hint": "Run manifest generation first"}
        )
    
    if not os.path.exists(SIGNATURE_FILENAME):
        raise RepoTrustError(
            f"Signature not found: {SIGNATURE_FILENAME}",
            context={"hint": "Manifest may not have been signed"}
        )
    
    # Load manifest to get release ID
    try:
        with open(MANIFEST_FILENAME, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise RepoTrustError(
            "Failed to parse manifest",
            context={"error": str(e)}
        )
    
    release_id = manifest.get("release", {}).get("release_id")
    if not release_id:
        raise RepoTrustError(
            "Manifest does not contain release_id",
            context={"hint": "Manifest may be malformed or from an older version"}
        )
    
    info(f"Uploading to release", release_id=release_id)
    
    # Upload manifest
    section("Uploading manifest")
    info(f"Uploading: {MANIFEST_FILENAME}")
    manifest_size = os.path.getsize(MANIFEST_FILENAME)
    debug(f"Manifest size", size=manifest_size)
    
    try:
        api.upload_release_asset(
            release_id,
            MANIFEST_FILENAME,
            content_type="application/json"
        )
    except Exception as e:
        raise RepoTrustError(
            f"Failed to upload manifest",
            context={"error": str(e)}
        )
    end_section()
    
    # Upload signature
    section("Uploading signature")
    info(f"Uploading: {SIGNATURE_FILENAME}")
    sig_size = os.path.getsize(SIGNATURE_FILENAME)
    debug(f"Signature size", size=sig_size)
    
    try:
        api.upload_release_asset(
            release_id,
            SIGNATURE_FILENAME,
            content_type="application/octet-stream"
        )
    except Exception as e:
        raise RepoTrustError(
            f"Failed to upload signature",
            context={"error": str(e)}
        )
    end_section()
    
    info("Manifest and signature uploaded successfully")


@handle_errors
def main():
    """Upload the manifest to the release."""
    section("Uploading to GitHub Release")
    upload_manifest()
    end_section()


if __name__ == "__main__":
    main()
