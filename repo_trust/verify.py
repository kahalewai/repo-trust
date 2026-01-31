"""
Manifest verification module for Repo Trust.

Verifies that the signed manifest is valid and matches the current repository.
"""

import json
import os
from typing import Any

from repo_trust.signing import verify_signature
from repo_trust.logging import (
    debug, info, warning, error, section, end_section,
    handle_errors, VerificationError, ConfigurationError
)


MANIFEST_FILENAME = "repo-trust-manifest.json"
SIGNATURE_FILENAME = "repo-trust-manifest.json.sig"


def load_manifest(manifest_path: str) -> dict[str, Any]:
    """
    Load and parse a manifest file.
    
    Args:
        manifest_path: Path to the manifest file
        
    Returns:
        Parsed manifest dictionary
        
    Raises:
        VerificationError: If manifest is invalid
    """
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise VerificationError(
            "Manifest is not valid JSON",
            context={
                "path": manifest_path,
                "error": str(e)
            }
        )
    except FileNotFoundError:
        raise VerificationError(
            f"Manifest file not found: {manifest_path}"
        )
    
    # Validate required fields
    required_fields = ["repo_trust_version", "repository", "release", "artifacts"]
    missing = [f for f in required_fields if f not in manifest]
    
    if missing:
        raise VerificationError(
            "Manifest missing required fields",
            context={
                "missing_fields": missing
            }
        )
    
    # Validate repository structure
    repo_fields = ["owner", "name", "full_name"]
    repo = manifest.get("repository", {})
    missing_repo = [f for f in repo_fields if f not in repo]
    
    if missing_repo:
        raise VerificationError(
            "Manifest repository section incomplete",
            context={
                "missing_fields": missing_repo
            }
        )
    
    return manifest


def verify_repository_identity(manifest: dict[str, Any]) -> None:
    """
    Verify the manifest repository matches the current environment.
    
    Args:
        manifest: Parsed manifest dictionary
        
    Raises:
        VerificationError: If repository identity doesn't match
    """
    expected_repo = os.environ.get("GITHUB_REPOSITORY")
    if not expected_repo:
        raise ConfigurationError(
            "GITHUB_REPOSITORY environment variable is required"
        )
    
    manifest_repo = manifest.get("repository", {}).get("full_name")
    
    if manifest_repo != expected_repo:
        raise VerificationError(
            "Repository identity mismatch",
            context={
                "manifest_repo": manifest_repo,
                "expected_repo": expected_repo,
                "hint": "This manifest was generated for a different repository"
            }
        )
    
    debug("Repository identity verified", repository=expected_repo)


def verify_manifest_version(manifest: dict[str, Any]) -> None:
    """
    Check manifest version compatibility.
    
    Args:
        manifest: Parsed manifest dictionary
    """
    version = manifest.get("repo_trust_version", "unknown")
    
    if version == "1.0":
        debug("Manifest version OK", version=version)
    else:
        warning(f"Unexpected manifest version: {version}")
        warning("Verification will continue but results may be unexpected")


def verify_manifest() -> dict[str, Any]:
    """
    Verify the Repo Trust manifest signature and contents.
    
    Returns:
        The verified manifest dictionary
        
    Raises:
        VerificationError: If verification fails
    """
    manifest_path = MANIFEST_FILENAME
    signature_path = SIGNATURE_FILENAME
    
    # Check files exist
    if not os.path.exists(manifest_path):
        raise VerificationError(
            f"Manifest not found: {manifest_path}",
            context={
                "hint": "Run manifest generation first"
            }
        )
    
    if not os.path.exists(signature_path):
        raise VerificationError(
            f"Signature not found: {signature_path}",
            context={
                "hint": "The manifest may not have been signed"
            }
        )
    
    section("Verifying cryptographic signature")
    
    # Verify cryptographic signature
    verify_signature(manifest_path, signature_path)
    
    info("Cryptographic signature is valid")
    end_section()
    
    # Load and validate manifest structure
    section("Validating manifest contents")
    
    manifest = load_manifest(manifest_path)
    debug("Manifest structure valid")
    
    # Check version compatibility
    verify_manifest_version(manifest)
    
    # Verify repository identity
    verify_repository_identity(manifest)
    
    info("Repository identity verified")
    end_section()
    
    return manifest


@handle_errors
def main():
    """Verify the Repo Trust manifest."""
    section("Repo Trust Verification")
    
    manifest = verify_manifest()
    
    # Output verification summary
    section("Verification Summary")
    info("✓ Signature valid")
    info("✓ Repository identity confirmed")
    info("✓ Manifest structure valid")
    print("")
    info(f"Repository: {manifest['repository']['full_name']}")
    info(f"Release: {manifest['release']['tag']}")
    info(f"Artifacts: {len(manifest.get('artifacts', []))}")
    info(f"Generated: {manifest.get('generated_at', 'unknown')}")
    end_section()


if __name__ == "__main__":
    main()
