"""
Signing module for Repo Trust.

Handles SSH-based signing of manifest files with proper error handling
and detailed diagnostics.
"""

import os
import subprocess
import shutil
from typing import Optional

from repo_trust.logging import (
    debug, info, warning, error,
    SigningError, ConfigurationError, VerificationError
)


def check_ssh_keygen() -> str:
    """
    Check that ssh-keygen is available.
    
    Returns:
        Path to ssh-keygen executable
        
    Raises:
        ConfigurationError: If ssh-keygen is not found
    """
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        raise ConfigurationError(
            "ssh-keygen not found",
            context={
                "hint": "Install OpenSSH client: apt-get install openssh-client"
            }
        )
    debug("Found ssh-keygen", path=ssh_keygen)
    return ssh_keygen


def validate_key_file(key_path: str, is_private: bool = True) -> None:
    """
    Validate that a key file exists and has proper permissions.
    
    Args:
        key_path: Path to the key file
        is_private: Whether this is a private key (checks permissions)
        
    Raises:
        ConfigurationError: If key file is invalid
    """
    if not os.path.exists(key_path):
        raise ConfigurationError(
            f"Key file not found: {key_path}",
            context={"key_type": "private" if is_private else "public"}
        )
    
    if not os.path.isfile(key_path):
        raise ConfigurationError(
            f"Key path is not a file: {key_path}"
        )
    
    # Check file size (keys should be reasonable size)
    size = os.path.getsize(key_path)
    if size == 0:
        raise ConfigurationError(
            f"Key file is empty: {key_path}"
        )
    
    if size > 10000:  # 10KB should be more than enough for any SSH key
        warning(f"Key file unusually large", path=key_path, size=size)
    
    # Check permissions for private key
    if is_private:
        mode = os.stat(key_path).st_mode & 0o777
        if mode & 0o077:  # Any group/other permissions
            warning(f"Private key has loose permissions", 
                   path=key_path, mode=oct(mode),
                   hint="Consider chmod 600")
    
    debug(f"Key file validated", path=key_path, size=size)


def sign_file(filepath: str, key_path: Optional[str] = None) -> str:
    """
    Sign a file using SSH signing.
    
    Args:
        filepath: Path to the file to sign
        key_path: Path to the private key (or use REPO_TRUST_KEY_PATH env var)
        
    Returns:
        Path to the signature file
        
    Raises:
        SigningError: If signing fails
        ConfigurationError: If configuration is invalid
    """
    # Get key path
    if key_path is None:
        key_path = os.environ.get("REPO_TRUST_KEY_PATH")
    
    if not key_path:
        raise ConfigurationError(
            "No signing key provided",
            context={
                "hint": "Set REPO_TRUST_KEY_PATH or pass key_path argument"
            }
        )
    
    # Validate inputs
    check_ssh_keygen()
    validate_key_file(key_path, is_private=True)
    
    if not os.path.exists(filepath):
        raise SigningError(
            f"File to sign not found: {filepath}"
        )
    
    # Perform signing
    sig_path = f"{filepath}.sig"
    
    debug(f"Signing file", filepath=filepath, key=key_path)
    
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
            timeout=30
        )
        
        if result.returncode != 0:
            # Parse common errors
            stderr = result.stderr.lower()
            
            if "invalid format" in stderr or "incorrect passphrase" in stderr:
                raise SigningError(
                    "Invalid key format or key requires passphrase",
                    context={
                        "hint": "Repo Trust requires passphrase-less keys",
                        "stderr": result.stderr
                    }
                )
            
            if "permission denied" in stderr:
                raise SigningError(
                    "Permission denied accessing signing key",
                    context={
                        "key_path": key_path,
                        "hint": "Check file permissions on the key"
                    }
                )
            
            raise SigningError(
                "Signing failed",
                context={
                    "exit_code": result.returncode,
                    "stderr": result.stderr,
                    "stdout": result.stdout
                }
            )
        
    except subprocess.TimeoutExpired:
        raise SigningError(
            "Signing timed out",
            context={
                "hint": "This may indicate a hung process or slow I/O"
            }
        )
    except FileNotFoundError:
        raise ConfigurationError(
            "ssh-keygen not found during execution",
            context={
                "hint": "The system PATH may have changed"
            }
        )
    
    # Verify signature file was created
    if not os.path.exists(sig_path):
        raise SigningError(
            "Signature file was not created",
            context={
                "expected_path": sig_path,
                "hint": "ssh-keygen may have failed silently"
            }
        )
    
    info(f"File signed successfully", filepath=filepath)
    debug(f"Signature written", sig_path=sig_path, size=os.path.getsize(sig_path))
    
    return sig_path


def verify_signature(filepath: str, signature_path: str, 
                    allowed_signers_path: Optional[str] = None) -> bool:
    """
    Verify an SSH signature.
    
    Args:
        filepath: Path to the signed file
        signature_path: Path to the signature file
        allowed_signers_path: Path to allowed_signers file (or use env var)
        
    Returns:
        True if signature is valid
        
    Raises:
        VerificationError: If verification fails
        ConfigurationError: If configuration is invalid
    """
    # Get allowed signers path
    if allowed_signers_path is None:
        allowed_signers_path = os.environ.get("REPO_TRUST_ALLOWED_SIGNERS")
    
    if not allowed_signers_path:
        raise ConfigurationError(
            "No allowed signers file provided",
            context={
                "hint": "Set REPO_TRUST_ALLOWED_SIGNERS or pass allowed_signers_path"
            }
        )
    
    # Validate inputs
    check_ssh_keygen()
    
    if not os.path.exists(allowed_signers_path):
        raise ConfigurationError(
            f"Allowed signers file not found: {allowed_signers_path}"
        )
    
    if not os.path.exists(filepath):
        raise VerificationError(
            f"File to verify not found: {filepath}"
        )
    
    if not os.path.exists(signature_path):
        raise VerificationError(
            f"Signature file not found: {signature_path}"
        )
    
    debug(f"Verifying signature", 
          filepath=filepath, 
          signature=signature_path,
          allowed_signers=allowed_signers_path)
    
    try:
        # Read file content to pass via stdin
        with open(filepath, "rb") as f:
            file_content = f.read()
        
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y", "verify",
                "-f", allowed_signers_path,
                "-I", "repo-trust",
                "-n", "repo-trust",
                "-s", signature_path
            ],
            input=file_content,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            info(f"Signature verified successfully", filepath=filepath)
            return True
        else:
            stderr = result.stderr.decode() if result.stderr else ""
            
            # Parse specific verification failures
            if "signature" in stderr.lower() and "not" in stderr.lower():
                raise VerificationError(
                    "Signature verification failed - signature does not match",
                    context={
                        "filepath": filepath,
                        "hint": "The file may have been tampered with or signed with a different key"
                    }
                )
            
            if "no principal matched" in stderr.lower():
                raise VerificationError(
                    "Signature verification failed - signer not in allowed list",
                    context={
                        "filepath": filepath,
                        "hint": "The public key may not be in the allowed_signers file"
                    }
                )
            
            raise VerificationError(
                "Signature verification failed",
                context={
                    "exit_code": result.returncode,
                    "stderr": stderr
                }
            )
            
    except subprocess.TimeoutExpired:
        raise VerificationError(
            "Verification timed out",
            context={
                "hint": "This may indicate a hung process"
            }
        )
    except FileNotFoundError:
        raise ConfigurationError("ssh-keygen not found during verification")
