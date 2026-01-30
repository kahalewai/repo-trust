"""
Signing module for Repo Trust.

Handles SSH-based signing of manifest files.
"""

import os
import subprocess
import sys


def sign_file(filepath: str) -> str:
    """
    Sign a file using SSH signing.
    
    Args:
        filepath: Path to the file to sign
        
    Returns:
        Path to the signature file
        
    Raises:
        RuntimeError: If signing fails
    """
    key_path = os.environ.get("REPO_TRUST_KEY_PATH")
    if not key_path:
        raise ValueError("REPO_TRUST_KEY_PATH environment variable is required")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Signing key not found at: {key_path}")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File to sign not found: {filepath}")
    
    # SSH signing creates a .sig file
    sig_path = f"{filepath}.sig"
    
    try:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y", "sign",
                "-f", key_path,
                "-n", "repo-trust",
                filepath
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"[repo-trust] Successfully signed: {filepath}")
        
    except subprocess.CalledProcessError as e:
        print(f"[repo-trust] Signing failed: {e.stderr}", file=sys.stderr)
        raise RuntimeError(f"Failed to sign file: {e.stderr}")
    
    if not os.path.exists(sig_path):
        raise RuntimeError(f"Signature file was not created: {sig_path}")
    
    return sig_path


def verify_signature(filepath: str, signature_path: str) -> bool:
    """
    Verify an SSH signature.
    
    Args:
        filepath: Path to the signed file
        signature_path: Path to the signature file
        
    Returns:
        True if signature is valid
        
    Raises:
        RuntimeError: If verification fails
    """
    allowed_signers = os.environ.get("REPO_TRUST_ALLOWED_SIGNERS")
    if not allowed_signers:
        raise ValueError("REPO_TRUST_ALLOWED_SIGNERS environment variable is required")
    
    if not os.path.exists(allowed_signers):
        raise FileNotFoundError(f"Allowed signers file not found: {allowed_signers}")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File to verify not found: {filepath}")
    
    if not os.path.exists(signature_path):
        raise FileNotFoundError(f"Signature file not found: {signature_path}")
    
    try:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y", "verify",
                "-f", allowed_signers,
                "-I", "repo-trust",
                "-n", "repo-trust",
                "-s", signature_path
            ],
            stdin=open(filepath, "rb"),
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"[repo-trust] Signature verified: {filepath}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[repo-trust] Signature verification failed: {e.stderr}", file=sys.stderr)
        return False
