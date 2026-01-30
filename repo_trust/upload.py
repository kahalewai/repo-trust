"""
Upload module for Repo Trust.

Handles uploading the signed manifest to GitHub Releases.
"""

import json
import os
import sys

from repo_trust.github import get_api


def upload_manifest():
    """
    Upload the signed manifest and signature to the GitHub release.
    """
    api = get_api()
    
    manifest_path = "repo-trust-manifest.json"
    signature_path = "repo-trust-manifest.json.sig"
    
    # Check files exist
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    if not os.path.exists(signature_path):
        raise FileNotFoundError(f"Signature not found: {signature_path}")
    
    # Load manifest to get release ID
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    release_id = manifest["release"]["release_id"]
    
    print(f"[repo-trust] Uploading to release ID: {release_id}")
    
    # Upload manifest
    print(f"[repo-trust] Uploading: {manifest_path}")
    api.upload_release_asset(
        release_id, 
        manifest_path, 
        content_type="application/json"
    )
    
    # Upload signature
    print(f"[repo-trust] Uploading: {signature_path}")
    api.upload_release_asset(
        release_id, 
        signature_path, 
        content_type="application/octet-stream"
    )
    
    print("[repo-trust] Manifest and signature uploaded successfully")


def main():
    """Upload the manifest to the release."""
    try:
        upload_manifest()
    except Exception as e:
        print(f"[repo-trust] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
