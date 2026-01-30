"""
GitHub Pages publishing module for Repo Trust.

Publishes the trust badge to GitHub Pages in a non-destructive manner
that coexists with existing Pages content.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from repo_trust.badge import render_verified_badge, render_unverified_badge


# The reserved subdirectory for Repo Trust
REPO_TRUST_PATH = "repo-trust"


def run_git(*args, cwd=None, check=True, capture_output=False):
    """Run a git command with proper error handling."""
    cmd = ["git"] + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        check=False
    )
    
    if check and result.returncode != 0:
        stderr = result.stderr if capture_output else ""
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{stderr}")
    
    return result


def branch_exists(branch: str, cwd: str) -> bool:
    """Check if a remote branch exists."""
    result = run_git(
        "ls-remote", "--heads", "origin", branch,
        cwd=cwd,
        check=False,
        capture_output=True
    )
    return bool(result.stdout.strip())


def publish_badge(verified: bool = True):
    """
    Publish the trust badge to GitHub Pages.
    
    This function:
    1. Clones the gh-pages branch if it exists, or creates a new one
    2. Creates/updates only the /repo-trust/ subdirectory
    3. Commits and pushes without force (preserving history)
    4. Never deletes or modifies other Pages content
    
    Args:
        verified: Whether the verification succeeded
    """
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise ValueError("GITHUB_REPOSITORY environment variable is required")
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    
    # Create a temporary directory for git operations
    with tempfile.TemporaryDirectory() as tmpdir:
        pages_dir = Path(tmpdir) / "pages"
        pages_dir.mkdir()
        
        # Configure git
        run_git("init", cwd=str(pages_dir))
        run_git("config", "user.name", "repo-trust-bot", cwd=str(pages_dir))
        run_git("config", "user.email", "repo-trust@users.noreply.github.com", cwd=str(pages_dir))
        
        # Set up remote with token authentication
        remote_url = f"https://x-access-token:{token}@{server_url.replace('https://', '')}/{repository}.git"
        run_git("remote", "add", "origin", remote_url, cwd=str(pages_dir))
        
        # Try to fetch the gh-pages branch
        gh_pages_exists = branch_exists("gh-pages", str(pages_dir))
        
        if gh_pages_exists:
            print("[repo-trust] Found existing gh-pages branch, fetching...")
            run_git("fetch", "origin", "gh-pages", cwd=str(pages_dir))
            run_git("checkout", "-b", "gh-pages", "origin/gh-pages", cwd=str(pages_dir))
        else:
            print("[repo-trust] Creating new gh-pages branch...")
            run_git("checkout", "--orphan", "gh-pages", cwd=str(pages_dir))
            # Create a minimal .nojekyll file to disable Jekyll processing
            (pages_dir / ".nojekyll").touch()
            run_git("add", ".nojekyll", cwd=str(pages_dir))
        
        # Create the repo-trust subdirectory
        repo_trust_dir = pages_dir / REPO_TRUST_PATH
        repo_trust_dir.mkdir(exist_ok=True)
        
        # Generate and write the badge
        badge_content = render_verified_badge() if verified else render_unverified_badge()
        badge_path = repo_trust_dir / "distribution.svg"
        badge_path.write_text(badge_content)
        
        print(f"[repo-trust] Generated badge: {'VERIFIED' if verified else 'UNVERIFIED'}")
        
        # Create an index.html with verification info
        index_content = generate_index_html(verified)
        index_path = repo_trust_dir / "index.html"
        index_path.write_text(index_content)
        
        # Stage changes
        run_git("add", REPO_TRUST_PATH, cwd=str(pages_dir))
        
        # Check if there are changes to commit
        status_result = run_git(
            "status", "--porcelain",
            cwd=str(pages_dir),
            capture_output=True
        )
        
        if not status_result.stdout.strip():
            print("[repo-trust] No changes to commit")
            return
        
        # Commit changes
        run_git(
            "commit", "-m", "Update Repo Trust verification badge",
            cwd=str(pages_dir)
        )
        
        # Push to gh-pages (without force!)
        print("[repo-trust] Pushing to gh-pages branch...")
        run_git("push", "origin", "gh-pages", cwd=str(pages_dir))
        
        print("[repo-trust] Badge published successfully!")


def generate_index_html(verified: bool) -> str:
    """Generate an informational HTML page for the Repo Trust directory."""
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    owner = repository.split("/")[0] if "/" in repository else ""
    repo_name = repository.split("/")[1] if "/" in repository else ""
    
    status = "VERIFIED" if verified else "UNVERIFIED"
    status_color = "#2ea44f" if verified else "#d73a49"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repo Trust - {repository}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background: #f6f8fa;
            color: #24292f;
        }}
        .header {{
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        .status {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-weight: bold;
            color: white;
            background: {status_color};
        }}
        .badge {{
            margin: 2rem 0;
        }}
        .badge img {{
            max-width: 100%;
        }}
        .info {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 1rem 0;
        }}
        a {{
            color: #0969da;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Repo Trust</h1>
        <p>Distribution verification for <a href="https://github.com/{repository}">{repository}</a></p>
        <div class="status">{status}</div>
        <div class="badge">
            <img src="distribution.svg" alt="Repo Trust Badge">
        </div>
    </div>
    <div class="info">
        <h2>What does this mean?</h2>
        <p>
            <strong>Repo Trust</strong> provides cryptographic verification that downloadable 
            artifacts were published by the official repository owner.
        </p>
        <ul>
            <li><strong>🟢 VERIFIED</strong> - The release was signed by the repository owner's key</li>
            <li><strong>🔴 UNVERIFIED</strong> - No valid signature found (could be a fork or impersonation)</li>
        </ul>
        <h2>How to verify</h2>
        <p>
            Each GitHub Release includes a <code>repo-trust-manifest.json</code> and 
            <code>repo-trust-manifest.json.sig</code> file that you can verify manually.
        </p>
        <h2>Learn more</h2>
        <p>
            <a href="https://github.com/repo-trust/action">Repo Trust on GitHub</a>
        </p>
    </div>
</body>
</html>
"""


def main():
    """Publish the trust badge to GitHub Pages."""
    try:
        # For now, always publish as verified since we only reach here if verification passed
        publish_badge(verified=True)
        
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        owner = repository.split("/")[0] if "/" in repository else ""
        repo_name = repository.split("/")[1] if "/" in repository else ""
        
        print("")
        print("[repo-trust] Badge URL:")
        print(f"    https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/distribution.svg")
        print("")
        print("[repo-trust] Add this to your README:")
        print(f'    ![Repo Trust](https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/distribution.svg)')
        
    except Exception as e:
        print(f"[repo-trust] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
