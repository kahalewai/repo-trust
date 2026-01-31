"""
Tests for Repo Trust.

Run with: pytest tests/ -v
"""

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestBadge:
    """Tests for badge generation."""
    
    def test_render_verified_badge(self):
        """Test rendering a verified badge."""
        from repo_trust.badge import render_verified_badge
        
        svg = render_verified_badge("test/repo")
        
        assert "<svg" in svg
        assert "Click to Verify" in svg
        assert "test/repo" in svg
        assert "Repo Trust" in svg
    
    def test_render_unverified_badge(self):
        """Test rendering an unverified badge."""
        from repo_trust.badge import render_unverified_badge
        
        svg = render_unverified_badge("test/repo")
        
        assert "<svg" in svg
        assert "Not Configured" in svg
        assert "test/repo" in svg
    
    def test_badge_includes_repo_name(self):
        """Test that badge includes repository name for anti-impersonation."""
        from repo_trust.badge import render_verified_badge
        
        svg = render_verified_badge("myorg/myproject")
        
        assert "myorg/myproject" in svg
    
    def test_badge_without_repo_name(self):
        """Test badge generation without repo name."""
        from repo_trust.badge import render_badge
        
        svg = render_badge(repo_name=None)
        
        assert "<svg" in svg
        assert "Click to Verify" in svg


class TestLogging:
    """Tests for logging infrastructure."""
    
    def test_exception_classes_exist(self):
        """Test that custom exception classes are available."""
        from repo_trust.logging import (
            RepoTrustError,
            ConfigurationError,
            GitHubAPIError,
            SigningError,
            VerificationError,
            PublishError
        )
        
        # Test inheritance
        assert issubclass(ConfigurationError, RepoTrustError)
        assert issubclass(GitHubAPIError, RepoTrustError)
        assert issubclass(SigningError, RepoTrustError)
        assert issubclass(VerificationError, RepoTrustError)
        assert issubclass(PublishError, RepoTrustError)
    
    def test_error_context(self):
        """Test that errors can carry context."""
        from repo_trust.logging import RepoTrustError
        
        error = RepoTrustError(
            "Test error",
            context={"key": "value"},
            recoverable=True,
            exit_code=2
        )
        
        assert error.message == "Test error"
        assert error.context == {"key": "value"}
        assert error.recoverable is True
        assert error.exit_code == 2


class TestSigning:
    """Tests for signing functionality."""
    
    def test_check_ssh_keygen(self):
        """Test that ssh-keygen detection works."""
        from repo_trust.signing import check_ssh_keygen
        
        # Should not raise if ssh-keygen is available
        path = check_ssh_keygen()
        assert path is not None
        assert "ssh-keygen" in path
    
    def test_sign_and_verify(self):
        """Test signing and verification round-trip."""
        from repo_trust.signing import sign_file, verify_signature
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate a test key
            key_path = Path(tmpdir) / "test-key"
            pub_path = Path(tmpdir) / "test-key.pub"
            
            os.system(f'ssh-keygen -t ed25519 -f {key_path} -N "" -C "test" 2>/dev/null')
            
            # Create a test file
            test_file = Path(tmpdir) / "test.json"
            test_file.write_text('{"test": "data"}')
            
            # Set up environment
            os.environ["REPO_TRUST_KEY_PATH"] = str(key_path)
            
            # Sign
            sig_path = sign_file(str(test_file))
            assert os.path.exists(sig_path)
            
            # Create allowed signers file
            allowed_signers = Path(tmpdir) / "allowed_signers"
            pub_key = pub_path.read_text().strip()
            allowed_signers.write_text(f"repo-trust {pub_key}")
            os.environ["REPO_TRUST_ALLOWED_SIGNERS"] = str(allowed_signers)
            
            # Verify
            result = verify_signature(str(test_file), sig_path)
            assert result is True


class TestManifestSchema:
    """Tests for manifest structure."""
    
    def test_manifest_has_required_fields(self):
        """Test that a generated manifest would have required fields."""
        # This tests the schema, not actual generation (which needs GitHub API)
        required_fields = [
            "repo_trust_version",
            "repository",
            "release",
            "artifacts",
            "generated_at",
            "generator"
        ]
        
        # Mock manifest structure
        manifest = {
            "repo_trust_version": "1.0",
            "repository": {
                "owner": "test",
                "name": "repo",
                "full_name": "test/repo",
                "git_url": "https://github.com/test/repo"
            },
            "release": {
                "tag": "v1.0.0",
                "commit": "abc123",
                "published_at": "2025-01-01T00:00:00Z",
                "release_id": 123
            },
            "artifacts": [],
            "generated_at": "2025-01-01T00:00:00Z",
            "generator": {
                "name": "repo-trust",
                "version": "1.0.0"
            }
        }
        
        for field in required_fields:
            assert field in manifest


class TestVerification:
    """Tests for manifest verification."""
    
    def test_load_valid_manifest(self):
        """Test loading a valid manifest."""
        from repo_trust.verify import load_manifest
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "repo_trust_version": "1.0",
                "repository": {
                    "owner": "test",
                    "name": "repo",
                    "full_name": "test/repo"
                },
                "release": {"tag": "v1.0.0"},
                "artifacts": []
            }, f)
            f.flush()
            
            manifest = load_manifest(f.name)
            assert manifest["repo_trust_version"] == "1.0"
            
            os.unlink(f.name)
    
    def test_load_invalid_json(self):
        """Test that invalid JSON raises error."""
        from repo_trust.verify import load_manifest
        from repo_trust.logging import VerificationError
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            
            with pytest.raises(VerificationError):
                load_manifest(f.name)
            
            os.unlink(f.name)


# Integration tests would go here, but require GitHub API mocking
# or a dedicated test repository

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
