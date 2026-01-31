"""
Logging module for Repo Trust.

Provides structured, production-grade logging with:
- Consistent formatting
- Log levels
- GitHub Actions annotations
- Error context preservation
"""

import os
import sys
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from functools import wraps


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


# ANSI color codes for terminal output
COLORS = {
    LogLevel.DEBUG: "\033[36m",    # Cyan
    LogLevel.INFO: "\033[32m",     # Green
    LogLevel.WARNING: "\033[33m",  # Yellow
    LogLevel.ERROR: "\033[31m",    # Red
    LogLevel.FATAL: "\033[35m",    # Magenta
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

# Check if we're running in GitHub Actions
IS_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"

# Log level from environment (default INFO)
CURRENT_LEVEL = LogLevel[os.environ.get("REPO_TRUST_LOG_LEVEL", "INFO").upper()]


def _should_log(level: LogLevel) -> bool:
    """Check if a message at this level should be logged."""
    levels = list(LogLevel)
    return levels.index(level) >= levels.index(CURRENT_LEVEL)


def _format_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _format_message(level: LogLevel, message: str, context: Optional[dict] = None) -> str:
    """Format a log message with optional context."""
    timestamp = _format_timestamp()
    
    # Base message
    if IS_GITHUB_ACTIONS:
        # Use GitHub Actions workflow commands for annotations
        if level == LogLevel.DEBUG:
            prefix = "::debug::"
        elif level == LogLevel.WARNING:
            prefix = "::warning::"
        elif level in (LogLevel.ERROR, LogLevel.FATAL):
            prefix = "::error::"
        else:
            prefix = ""
        formatted = f"{prefix}[repo-trust] {message}"
    else:
        # Terminal output with colors
        color = COLORS.get(level, "")
        reset = COLORS["RESET"]
        formatted = f"{color}[{timestamp}] [{level.value:7}] [repo-trust] {message}{reset}"
    
    # Add context if provided
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        formatted += f" ({context_str})"
    
    return formatted


def debug(message: str, **context):
    """Log a debug message."""
    if _should_log(LogLevel.DEBUG):
        print(_format_message(LogLevel.DEBUG, message, context or None))


def info(message: str, **context):
    """Log an info message."""
    if _should_log(LogLevel.INFO):
        print(_format_message(LogLevel.INFO, message, context or None))


def warning(message: str, **context):
    """Log a warning message."""
    if _should_log(LogLevel.WARNING):
        print(_format_message(LogLevel.WARNING, message, context or None), file=sys.stderr)


def error(message: str, **context):
    """Log an error message."""
    if _should_log(LogLevel.ERROR):
        print(_format_message(LogLevel.ERROR, message, context or None), file=sys.stderr)


def fatal(message: str, **context):
    """Log a fatal message (does not exit)."""
    print(_format_message(LogLevel.FATAL, message, context or None), file=sys.stderr)


def exception(message: str, exc: Exception, **context):
    """Log an exception with full traceback."""
    error(message, error_type=type(exc).__name__, error_msg=str(exc), **context)
    if _should_log(LogLevel.DEBUG):
        traceback.print_exc()


def section(title: str):
    """Print a section header."""
    if IS_GITHUB_ACTIONS:
        print(f"::group::{title}")
    else:
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")


def end_section():
    """End a section (GitHub Actions only)."""
    if IS_GITHUB_ACTIONS:
        print("::endgroup::")


def set_output(name: str, value: str):
    """Set a GitHub Actions output variable."""
    if IS_GITHUB_ACTIONS:
        output_file = os.environ.get("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"{name}={value}\n")
    debug(f"Output: {name}={value}")


def mask_secret(value: str):
    """Mask a value in GitHub Actions logs."""
    if IS_GITHUB_ACTIONS and value:
        print(f"::add-mask::{value}")


class RepoTrustError(Exception):
    """Base exception for Repo Trust errors."""
    
    def __init__(self, message: str, context: Optional[dict] = None, 
                 recoverable: bool = False, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.recoverable = recoverable
        self.exit_code = exit_code
    
    def log(self):
        """Log this error with context."""
        if self.recoverable:
            warning(self.message, **self.context)
        else:
            error(self.message, **self.context)


class ConfigurationError(RepoTrustError):
    """Error in configuration or environment setup."""
    pass


class GitHubAPIError(RepoTrustError):
    """Error communicating with GitHub API."""
    pass


class SigningError(RepoTrustError):
    """Error during cryptographic signing."""
    pass


class VerificationError(RepoTrustError):
    """Error during signature verification."""
    pass


class PublishError(RepoTrustError):
    """Error publishing to GitHub Pages."""
    pass


def handle_errors(func):
    """Decorator to handle errors consistently in main functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RepoTrustError as e:
            e.log()
            sys.exit(e.exit_code)
        except KeyboardInterrupt:
            warning("Operation cancelled by user")
            sys.exit(130)
        except Exception as e:
            exception("Unexpected error occurred", e)
            sys.exit(1)
    return wrapper


def summarize_run(success: bool, manifest_path: Optional[str] = None, 
                  badge_url: Optional[str] = None, artifacts_count: int = 0):
    """Print a summary of the Repo Trust run."""
    print("")
    if IS_GITHUB_ACTIONS:
        print("::group::Repo Trust Summary")
    
    print("=" * 60)
    print(" REPO TRUST RUN SUMMARY")
    print("=" * 60)
    
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f" Status:     {status}")
    print(f" Repository: {os.environ.get('GITHUB_REPOSITORY', 'unknown')}")
    print(f" Release:    {os.environ.get('GITHUB_REF_NAME', 'unknown')}")
    print(f" Artifacts:  {artifacts_count}")
    
    if manifest_path:
        print(f" Manifest:   {manifest_path}")
    if badge_url:
        print(f" Badge URL:  {badge_url}")
    
    print("=" * 60)
    
    if IS_GITHUB_ACTIONS:
        print("::endgroup::")
        
        # Set outputs
        set_output("success", str(success).lower())
        set_output("artifacts_count", str(artifacts_count))
        if badge_url:
            set_output("badge_url", badge_url)
