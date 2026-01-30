"""
Manifest verification module for Repo Trust.

Verifies that the signed manifest is valid and matches the current repository.
"""

import json
import os
import sys
from typing import Any

from repo_trust.signing import verify_signature


def verify_manifest() -> dict[str, Any]:
    """
    Verify the Repo Trust manifest signature and contents.
    
    Returns:
        The verified manifest dictionary
        
    Raises:
        RuntimeError: If verification fails
    """
    manifest_path = "repo-trust-manifest.json"
    signature_path = "repo-trust-manifest.json.sig"
    
    # Check files exist
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    if not os.path.exists(signature_path):
        raise FileNotFoundError(f"Signature not found: {signature_path}")
    
    # Verify cryptographic signature
    print("[repo-trust] Verifying cryptographic signature...")
    if not verify_signature(manifest_path, signature_path):
        raise RuntimeError("Manifest signature verification failed")
    
    print("[repo-trust] Signature is valid")
    
    # Load manifest
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    # Verify repository identity matches
    expected_repo = os.environ.get("GITHUB_REPOSITORY")
    manifest_repo = manifest.get("repository", {}).get("full_name")
    
    if manifest_repo != expected_repo:
        raise RuntimeError(
            f"Repository mismatch: manifest says '{manifest_repo}', "
            f"but running in '{expected_repo}'"
        )
    
    print(f"[repo-trust] Repository identity verified: {expected_repo}")
    
    # Verify manifest version
    version = manifest.get("repo_trust_version")
    if version != "1.0":
        print(f"[repo-trust] Warning: Unexpected manifest version: {version}")
    
    return manifest


def main():
    """Verify the Repo Trust manifest."""
    try:
        manifest = verify_manifest()
        
        print("[repo-trust] Verification successful!")
        print(f"[repo-trust]   Repository: {manifest['repository']['full_name']}")
        print(f"[repo-trust]   Release: {manifest['release']['tag']}")
        print(f"[repo-trust]   Artifacts: {len(manifest.get('artifacts', []))}")
        print(f"[repo-trust]   Generated: {manifest.get('generated_at', 'unknown')}")
        
    except FileNotFoundError as e:
        print(f"[repo-trust] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"[repo-trust] VERIFICATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[repo-trust] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
