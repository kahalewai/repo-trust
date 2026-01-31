"""
GitHub Pages publishing module for Repo Trust.

Publishes the trust badge to GitHub Pages in a non-destructive manner
that coexists with existing Pages content.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from repo_trust.badge import render_verified_badge, render_unverified_badge
from repo_trust.logging import (
    debug, info, warning, error, section, end_section,
    handle_errors, PublishError, ConfigurationError
)


# The reserved subdirectory for Repo Trust
REPO_TRUST_PATH = "repo-trust"

# Git operation timeout (seconds)
GIT_TIMEOUT = 60


class GitError(PublishError):
    """Git operation failed."""
    pass


def run_git(*args, cwd: Optional[str] = None, check: bool = True, 
            capture_output: bool = False, timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess:
    """
    Run a git command with proper error handling.
    
    Args:
        *args: Git command arguments
        cwd: Working directory
        check: Whether to check return code
        capture_output: Whether to capture stdout/stderr
        timeout: Command timeout in seconds
        
    Returns:
        CompletedProcess result
        
    Raises:
        GitError: If command fails and check=True
    """
    cmd = ["git"] + list(args)
    debug(f"Running git command", cmd=" ".join(cmd), cwd=cwd)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        
        if check and result.returncode != 0:
            stderr = result.stderr if capture_output else ""
            raise GitError(
                f"Git command failed: {' '.join(args)}",
                context={
                    "exit_code": result.returncode,
                    "stderr": stderr[:500] if stderr else None
                }
            )
        
        return result
        
    except subprocess.TimeoutExpired:
        raise GitError(
            f"Git command timed out: {' '.join(args)}",
            context={"timeout": timeout}
        )
    except FileNotFoundError:
        raise ConfigurationError(
            "Git not found",
            context={"hint": "Install git: apt-get install git"}
        )


def branch_exists(branch: str, cwd: str) -> bool:
    """Check if a remote branch exists."""
    result = run_git(
        "ls-remote", "--heads", "origin", branch,
        cwd=cwd,
        check=False,
        capture_output=True
    )
    return bool(result.stdout.strip())


def publish_badge(verified: bool = True) -> str:
    """
    Publish the trust badge to GitHub Pages.
    
    This function:
    1. Clones the gh-pages branch if it exists, or creates a new one
    2. Creates/updates only the /repo-trust/ subdirectory
    3. Commits and pushes without force (preserving history)
    4. Never deletes or modifies other Pages content
    
    Args:
        verified: Whether the verification succeeded
        
    Returns:
        URL of the published badge
        
    Raises:
        PublishError: If publishing fails
        ConfigurationError: If configuration is invalid
    """
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise ConfigurationError("GITHUB_REPOSITORY environment variable is required")
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ConfigurationError("GITHUB_TOKEN environment variable is required")
    
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    
    owner, repo_name = repository.split("/", 1)
    badge_url = f"https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/distribution.svg"
    
    info(f"Publishing badge to GitHub Pages")
    debug(f"Target URL", url=badge_url)
    
    # Create a temporary directory for git operations
    with tempfile.TemporaryDirectory() as tmpdir:
        pages_dir = Path(tmpdir) / "pages"
        pages_dir.mkdir()
        
        section("Setting up git repository")
        
        # Initialize git
        run_git("init", cwd=str(pages_dir))
        run_git("config", "user.name", "repo-trust-bot", cwd=str(pages_dir))
        run_git("config", "user.email", "repo-trust@users.noreply.github.com", cwd=str(pages_dir))
        
        # Set up remote with token authentication
        # Mask the token in logs
        remote_host = server_url.replace("https://", "").replace("http://", "")
        remote_url = f"https://x-access-token:{token}@{remote_host}/{repository}.git"
        run_git("remote", "add", "origin", remote_url, cwd=str(pages_dir))
        
        end_section()
        
        # Try to fetch the gh-pages branch
        section("Checking for existing gh-pages branch")
        gh_pages_exists = branch_exists("gh-pages", str(pages_dir))
        
        if gh_pages_exists:
            info("Found existing gh-pages branch, fetching...")
            run_git("fetch", "origin", "gh-pages", cwd=str(pages_dir))
            run_git("checkout", "-b", "gh-pages", "origin/gh-pages", cwd=str(pages_dir))
        else:
            info("Creating new gh-pages branch...")
            run_git("checkout", "--orphan", "gh-pages", cwd=str(pages_dir))
            # Create a minimal .nojekyll file to disable Jekyll processing
            (pages_dir / ".nojekyll").touch()
            run_git("add", ".nojekyll", cwd=str(pages_dir))
        
        end_section()
        
        # Create the repo-trust subdirectory
        section("Generating badge")
        repo_trust_dir = pages_dir / REPO_TRUST_PATH
        repo_trust_dir.mkdir(exist_ok=True)
        
        # Generate and write the badge
        badge_content = render_verified_badge(repository) if verified else render_unverified_badge(repository)
        badge_path = repo_trust_dir / "distribution.svg"
        badge_path.write_text(badge_content)
        
        info(f"Generated badge: {'VERIFIED' if verified else 'UNVERIFIED'}")
        debug(f"Badge file", path=str(badge_path), size=len(badge_content))
        
        # Create an index.html with verification info
        index_content = generate_index_html(verified, repository)
        index_path = repo_trust_dir / "index.html"
        index_path.write_text(index_content)
        
        end_section()
        
        # Stage changes
        section("Committing and pushing")
        run_git("add", REPO_TRUST_PATH, cwd=str(pages_dir))
        
        # Check if there are changes to commit
        status_result = run_git(
            "status", "--porcelain",
            cwd=str(pages_dir),
            capture_output=True
        )
        
        if not status_result.stdout.strip():
            info("No changes to commit (badge already up to date)")
            end_section()
            return badge_url
        
        # Commit changes
        run_git(
            "commit", "-m", "Update Repo Trust verification badge",
            cwd=str(pages_dir)
        )
        
        # Push to gh-pages (without force!)
        info("Pushing to gh-pages branch...")
        try:
            run_git("push", "origin", "gh-pages", cwd=str(pages_dir))
        except GitError as e:
            error_context = e.context.get("stderr", "").lower()
            
            if "protected branch" in error_context:
                raise PublishError(
                    "Cannot push to gh-pages: branch is protected",
                    context={
                        "hint": "Remove branch protection from gh-pages or add an exception for GitHub Actions"
                    }
                )
            
            if "denied" in error_context or "forbidden" in error_context:
                raise PublishError(
                    "Cannot push to gh-pages: permission denied",
                    context={
                        "hint": "Check that GITHUB_TOKEN has 'contents: write' permission"
                    }
                )
            
            if "would clobber" in error_context or "non-fast-forward" in error_context:
                warning("gh-pages branch has diverged, attempting to pull and retry")
                run_git("pull", "--rebase", "origin", "gh-pages", cwd=str(pages_dir))
                run_git("push", "origin", "gh-pages", cwd=str(pages_dir))
            else:
                raise
        
        end_section()
        
        info(f"Badge published successfully")
        return badge_url


def generate_index_html(verified: bool, repository: str) -> str:
    """
    Generate the verification page that performs Referer-based commit verification.
    
    This is the KEY security feature that detects repo squatting attacks:
    1. When user clicks badge, browser sends Referer header with full URL
    2. If URL contains /tree/<commit_hash>, we check if that commit is in official history
    3. If it's a detached fork commit (repo squatting), we show a WARNING
    4. If no suspicious commit hash or commit is legitimate, we show VERIFIED
    
    Auto-redirect feature:
    - VERIFIED: Redirects back to official repo after 8 seconds
    - WARNING: Redirects to official repo after 15 seconds (rescues user from attacker)
    - User can cancel redirect by clicking "Stay on this page"
    """
    owner = repository.split("/")[0] if "/" in repository else ""
    repo_name = repository.split("/")[1] if "/" in repository else ""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repo Trust Verification - {repository}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background: #f6f8fa;
            color: #24292f;
            line-height: 1.6;
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
            padding: 0.75rem 2rem;
            border-radius: 6px;
            font-weight: 600;
            font-size: 1.2rem;
            color: white;
            margin: 1rem 0;
        }}
        .status.verified {{ background: #2ea44f; }}
        .status.warning {{ background: #d73a49; }}
        .status.checking {{ background: #6e7681; }}
        .status.unknown {{ background: #bf8700; }}
        
        .alert {{
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .alert.danger {{
            background: #ffebe9;
            border: 1px solid #d73a49;
        }}
        .alert.success {{
            background: #dafbe1;
            border: 1px solid #2ea44f;
        }}
        .alert.warning {{
            background: #fff8c5;
            border: 1px solid #bf8700;
        }}
        .alert h3 {{
            margin: 0 0 0.5rem 0;
            color: inherit;
        }}
        
        .info {{
            background: white;
            padding: 1.5rem 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }}
        h1 {{
            margin: 0 0 0.5rem 0;
            font-size: 1.8rem;
        }}
        h2 {{
            margin: 1.5rem 0 1rem 0;
            font-size: 1.2rem;
            color: #57606a;
        }}
        a {{
            color: #0969da;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background: #f6f8fa;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9rem;
            word-break: break-all;
        }}
        .referrer-info {{
            font-size: 0.85rem;
            color: #57606a;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #d0d7de;
        }}
        .footer {{
            text-align: center;
            color: #57606a;
            font-size: 0.9rem;
            margin-top: 2rem;
        }}
        #verification-result {{
            min-height: 200px;
        }}
        .spinner {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* Redirect countdown styles */
        .redirect-notice {{
            background: #f0f4f8;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-top: 1.5rem;
            text-align: center;
        }}
        .redirect-notice.warning-redirect {{
            background: #fff1e5;
            border-color: #fd8c73;
        }}
        .countdown {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #0969da;
            margin: 0.5rem 0;
        }}
        .redirect-notice.warning-redirect .countdown {{
            color: #cf222e;
        }}
        .cancel-btn {{
            display: inline-block;
            margin-top: 0.75rem;
            padding: 0.5rem 1rem;
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            color: #24292f;
        }}
        .cancel-btn:hover {{
            background: #f6f8fa;
            border-color: #1b1f23;
        }}
        .progress-bar {{
            height: 4px;
            background: #d0d7de;
            border-radius: 2px;
            margin-top: 1rem;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: #2ea44f;
            transition: width 1s linear;
        }}
        .redirect-notice.warning-redirect .progress-bar-fill {{
            background: #cf222e;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Repo Trust Verification</h1>
        <p>Verifying distribution authenticity for <strong>{repository}</strong></p>
        <div id="status-badge" class="status checking">
            <span class="spinner"></span> Verifying...
        </div>
    </div>
    
    <div id="verification-result">
        <!-- Populated by JavaScript -->
    </div>
    
    <div id="redirect-container">
        <!-- Redirect countdown will appear here -->
    </div>
    
    <div class="info">
        <h2>About This Verification</h2>
        <p>
            This page verifies that you came from an <strong>official</strong> page of 
            <a href="https://github.com/{repository}">{repository}</a>, not a fork or impersonation.
        </p>
        <p>
            <strong>How it works:</strong> When you click the verification badge, your browser 
            tells us which page you came from. We check that page against the official repository 
            to detect repo squatting attacks.
        </p>
    </div>
    
    <div class="footer">
        <p>Powered by <a href="https://github.com/repo-trust/action">Repo Trust</a></p>
    </div>

    <script>
    (function() {{
        const REPO_OWNER = '{owner}';
        const REPO_NAME = '{repo_name}';
        const FULL_REPO = '{repository}';
        const OFFICIAL_REPO_URL = 'https://github.com/{repository}';
        
        // Redirect timing (in seconds)
        const VERIFIED_REDIRECT_DELAY = 8;
        const WARNING_REDIRECT_DELAY = 15;
        
        const statusBadge = document.getElementById('status-badge');
        const resultDiv = document.getElementById('verification-result');
        const redirectContainer = document.getElementById('redirect-container');
        
        // Get the referrer (the page user clicked from)
        const referrer = document.referrer || '';
        
        // Redirect state
        let redirectTimer = null;
        let countdownInterval = null;
        let redirectCancelled = false;
        
        // Extract commit hash from URL if present
        function extractCommitFromUrl(url) {{
            const patterns = [
                /\\/tree\\/([a-f0-9]{{40}})/i,
                /\\/tree\\/([a-f0-9]{{7,40}})/i,
                /\\/commit\\/([a-f0-9]{{40}})/i,
                /\\/commit\\/([a-f0-9]{{7,40}})/i,
                /\\/blob\\/([a-f0-9]{{40}})\\//i,
                /\\/blob\\/([a-f0-9]{{7,40}})\\//i
            ];
            for (const pattern of patterns) {{
                const match = url.match(pattern);
                if (match) return match[1];
            }}
            return null;
        }}
        
        // Check if referrer is from the expected repository
        function isFromExpectedRepo(url) {{
            if (!url) return false;
            const expectedPatterns = [
                new RegExp(`github\\.com\\/${{REPO_OWNER}}\\/${{REPO_NAME}}(\\/|$|\\?|#)`, 'i'),
                new RegExp(`${{REPO_OWNER}}\\.github\\.io\\/${{REPO_NAME}}(\\/|$|\\?|#)`, 'i')
            ];
            return expectedPatterns.some(p => p.test(url));
        }}
        
        // Check if a commit is in the default branch using GitHub API
        async function isCommitInDefaultBranch(commitSha) {{
            try {{
                const repoResponse = await fetch(
                    `https://api.github.com/repos/${{FULL_REPO}}`,
                    {{ headers: {{ 'Accept': 'application/vnd.github.v3+json' }} }}
                );
                if (!repoResponse.ok) return {{ error: 'repo_not_found' }};
                const repoData = await repoResponse.json();
                const defaultBranch = repoData.default_branch;
                
                const compareResponse = await fetch(
                    `https://api.github.com/repos/${{FULL_REPO}}/compare/${{commitSha}}...${{defaultBranch}}`,
                    {{ headers: {{ 'Accept': 'application/vnd.github.v3+json' }} }}
                );
                
                if (compareResponse.status === 404) {{
                    return {{ inDefaultBranch: false, reason: 'commit_not_found' }};
                }}
                
                if (!compareResponse.ok) {{
                    return {{ error: 'api_error' }};
                }}
                
                const compareData = await compareResponse.json();
                const validStatuses = ['ahead', 'identical', 'behind'];
                const isInHistory = validStatuses.includes(compareData.status);
                
                return {{ 
                    inDefaultBranch: isInHistory,
                    status: compareData.status,
                    defaultBranch: defaultBranch
                }};
            }} catch (e) {{
                console.error('API error:', e);
                return {{ error: 'network_error' }};
            }}
        }}
        
        // Start redirect countdown
        function startRedirect(seconds, isWarning, targetUrl) {{
            if (redirectCancelled) return;
            
            let remaining = seconds;
            const warningClass = isWarning ? 'warning-redirect' : '';
            const message = isWarning 
                ? `Redirecting you to the <strong>official repository</strong> for your safety...`
                : `Returning you to <strong>{repository}</strong>...`;
            
            redirectContainer.innerHTML = `
                <div class="redirect-notice ${{warningClass}}">
                    <p>${{message}}</p>
                    <div class="countdown" id="countdown">${{remaining}}</div>
                    <div class="progress-bar">
                        <div class="progress-bar-fill" id="progress-fill" style="width: 100%"></div>
                    </div>
                    <button class="cancel-btn" onclick="window.cancelRedirect()">Stay on this page</button>
                </div>
            `;
            
            const countdownEl = document.getElementById('countdown');
            const progressEl = document.getElementById('progress-fill');
            
            countdownInterval = setInterval(() => {{
                remaining--;
                if (countdownEl) countdownEl.textContent = remaining;
                if (progressEl) progressEl.style.width = ((remaining / seconds) * 100) + '%';
                
                if (remaining <= 0) {{
                    clearInterval(countdownInterval);
                    if (!redirectCancelled) {{
                        window.location.href = targetUrl;
                    }}
                }}
            }}, 1000);
        }}
        
        // Cancel redirect (exposed globally for onclick)
        window.cancelRedirect = function() {{
            redirectCancelled = true;
            if (countdownInterval) clearInterval(countdownInterval);
            redirectContainer.innerHTML = `
                <div class="redirect-notice">
                    <p>Redirect cancelled. <a href="${{OFFICIAL_REPO_URL}}">Go to {repository} →</a></p>
                </div>
            `;
        }};
        
        function showVerified(message, details) {{
            statusBadge.className = 'status verified';
            statusBadge.innerHTML = '✅ VERIFIED';
            resultDiv.innerHTML = `
                <div class="alert success">
                    <h3>✅ Official Distribution Confirmed</h3>
                    <p>${{message}}</p>
                    ${{details ? `<p style="font-size: 0.9rem; margin-top: 1rem;">${{details}}</p>` : ''}}
                </div>
                <div class="info">
                    <h2>You're Safe</h2>
                    <p>You are viewing the official <strong>{repository}</strong> repository. 
                    Downloads from this page are from the legitimate maintainer.</p>
                </div>
                ${{referrer ? `<div class="referrer-info">Verified from: <code>${{escapeHtml(referrer)}}</code></div>` : ''}}
            `;
            
            // Start redirect back to where they came from (or official repo)
            const returnUrl = referrer && isFromExpectedRepo(referrer) ? referrer : OFFICIAL_REPO_URL;
            startRedirect(VERIFIED_REDIRECT_DELAY, false, returnUrl);
        }}
        
        function showWarning(message, details) {{
            statusBadge.className = 'status warning';
            statusBadge.innerHTML = '⚠️ WARNING';
            resultDiv.innerHTML = `
                <div class="alert danger">
                    <h3>⚠️ Possible Repo Squatting Detected</h3>
                    <p>${{message}}</p>
                    ${{details ? `<p style="font-size: 0.9rem; margin-top: 1rem;">${{details}}</p>` : ''}}
                </div>
                <div class="info">
                    <h2>What Should I Do?</h2>
                    <p><strong>Do not download</strong> any files from the page you came from.</p>
                    <p>We will redirect you to the official repository:</p>
                    <p style="text-align: center; margin: 1rem 0;">
                        <a href="${{OFFICIAL_REPO_URL}}" style="font-size: 1.1rem; font-weight: 600;">
                            → github.com/{repository}
                        </a>
                    </p>
                </div>
                <div class="info">
                    <h2>What is Repo Squatting?</h2>
                    <p>Attackers can fork a legitimate repository and modify the README to include 
                    malicious download links. Due to how GitHub works, these malicious commits can 
                    appear under the official repository's URL.</p>
                    <p>This verification page detected that you may have been viewing such a malicious commit.</p>
                </div>
                ${{referrer ? `<div class="referrer-info">Suspicious referrer: <code>${{escapeHtml(referrer)}}</code></div>` : ''}}
            `;
            
            // Redirect to official repo (rescue the user from the attacker!)
            startRedirect(WARNING_REDIRECT_DELAY, true, OFFICIAL_REPO_URL);
        }}
        
        function showUnknown(message) {{
            statusBadge.className = 'status unknown';
            statusBadge.innerHTML = '❓ MANUAL CHECK REQUIRED';
            resultDiv.innerHTML = `
                <div class="alert warning">
                    <h3>❓ Unable to Verify Automatically</h3>
                    <p>${{message}}</p>
                </div>
                <div class="info">
                    <h2>Please Verify Manually</h2>
                    <p>Make sure you are on the official repository page:</p>
                    <p style="text-align: center; margin: 1rem 0;">
                        <a href="${{OFFICIAL_REPO_URL}}" style="font-size: 1.1rem; font-weight: 600;">
                            → github.com/{repository}
                        </a>
                    </p>
                    <p>Check that:</p>
                    <ul>
                        <li>The URL is exactly <code>github.com/{repository}</code></li>
                        <li>You're viewing the main branch, not a specific commit</li>
                        <li>The repository owner matches what you expect</li>
                    </ul>
                </div>
            `;
            // No auto-redirect for unknown - user needs to decide
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // Main verification logic
        async function verify() {{
            // Case 1: No referrer (privacy settings, direct navigation, etc.)
            if (!referrer) {{
                showUnknown(
                    'Your browser did not send referrer information. This can happen due to ' +
                    'privacy settings or if you navigated here directly.'
                );
                return;
            }}
            
            // Case 2: Referrer is not from expected repository
            if (!isFromExpectedRepo(referrer)) {{
                if (referrer.includes('github.com/')) {{
                    showWarning(
                        'You came from a different repository than expected.',
                        `Expected: github.com/{repository}<br>Actual: ${{escapeHtml(referrer)}}`
                    );
                }} else {{
                    showUnknown(
                        `You came from an external site. Please verify you're on the official repository.`
                    );
                }}
                return;
            }}
            
            // Case 3: Referrer contains a commit hash - need to verify it's legitimate
            const commitHash = extractCommitFromUrl(referrer);
            if (commitHash) {{
                statusBadge.innerHTML = '<span class="spinner"></span> Checking commit...';
                
                const result = await isCommitInDefaultBranch(commitHash);
                
                if (result.error) {{
                    showUnknown(
                        `Unable to verify commit due to API error. Please verify manually that ` +
                        `you're viewing the official repository.`
                    );
                    return;
                }}
                
                if (!result.inDefaultBranch) {{
                    showWarning(
                        'You are viewing a commit that is <strong>NOT</strong> part of the official repository history. ' +
                        'This is a strong indicator of a <strong>repo squatting attack</strong>.',
                        `Commit: <code>${{commitHash}}</code><br>` +
                        `This commit may be from a fork that was used to inject malicious content.`
                    );
                    return;
                }}
                
                showVerified(
                    'The commit you viewed is part of the official repository history.',
                    `Commit <code>${{commitHash.substring(0, 7)}}</code> is in the <code>${{result.defaultBranch}}</code> branch.`
                );
                return;
            }}
            
            // Case 4: Normal referrer from expected repo without commit hash
            showVerified(
                'You came from the official <strong>{repository}</strong> repository page.',
                'No suspicious commit hash detected in the URL.'
            );
        }}
        
        // Run verification
        verify();
    }})();
    </script>
</body>
</html>
"""


@handle_errors
def main():
    """Publish the trust badge to GitHub Pages."""
    section("Publishing to GitHub Pages")
    
    # Publish as verified (we only reach here if verification passed)
    badge_url = publish_badge(verified=True)
    
    end_section()
    
    # Output badge URL for users
    section("Badge Published")
    print("")
    info(f"Badge URL: {badge_url}")
    print("")
    info("Add this to your README:")
    
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    print(f'    ![Repo Trust]({badge_url})')
    print("")
    
    end_section()


if __name__ == "__main__":
    main()
