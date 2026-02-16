"""
GitHub Pages publishing module for Repo Trust.

Publishes the verified download page and badge to GitHub Pages.
This is the core of Repo Trust — the GitHub Pages domain is the
trust anchor that attackers cannot control.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from repo_trust.badge import render_badge


REPO_TRUST_PATH = "repo-trust"
GIT_TIMEOUT = 60


def run_git(*args, cwd=None, check=True, capture_output=False):
    """Run a git command with error handling."""
    cmd = ["git"] + list(args)
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=capture_output,
        text=True, timeout=GIT_TIMEOUT,
    )
    if check and result.returncode != 0:
        stderr = result.stderr if capture_output else ""
        raise RuntimeError(f"Git command failed: {' '.join(args)}\n{stderr}")
    return result


def branch_exists(branch, cwd):
    """Check if a remote branch exists."""
    result = run_git(
        "ls-remote", "--heads", "origin", branch,
        cwd=cwd, check=False, capture_output=True,
    )
    return bool(result.stdout.strip())


def generate_download_page(repository, release_data):
    """
    Generate the verified download + verification HTML page.

    This page serves two purposes:
    1. DOWNLOAD PORTAL - lists official release assets from a trusted domain
    2. REFERER CHECK - detects repo squatting when users arrive from suspicious URLs
    """
    owner = repository.split("/")[0] if "/" in repository else ""
    repo_name = repository.split("/")[1] if "/" in repository else ""
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")

    # Build the asset list HTML (baked in at deploy time)
    assets = release_data.get("assets", [])
    tag = release_data.get("tag")
    release_name = release_data.get("name", tag or "")
    release_url = release_data.get("html_url", "")

    if assets:
        asset_rows = ""
        for a in assets:
            asset_rows += (
                f'<tr>'
                f'<td class="asset-name">{_esc(a["name"])}</td>'
                f'<td class="asset-size">{_esc(a["size_display"])}</td>'
                f'<td><a href="{_esc(a["download_url"])}" class="download-btn">Download</a></td>'
                f'</tr>'
            )
        downloads_html = f"""
        <div class="card">
            <h2>📦 Latest Release: {_esc(release_name)}</h2>
            <table class="assets-table">
                <thead><tr><th>File</th><th>Size</th><th></th></tr></thead>
                <tbody>{asset_rows}</tbody>
            </table>
            <p class="release-link">
                <a href="{_esc(release_url)}">View full release notes on GitHub →</a>
            </p>
        </div>
        """
    elif tag:
        downloads_html = f"""
        <div class="card">
            <h2>📦 Latest Release: {_esc(release_name)}</h2>
            <p>This release has no downloadable assets.</p>
            <p><a href="{_esc(release_url)}">View release on GitHub →</a></p>
        </div>
        """
    else:
        downloads_html = """
        <div class="card">
            <h2>📦 Downloads</h2>
            <p>No releases published yet. Downloads will appear here when the maintainer publishes a release.</p>
        </div>
        """

    report_url = f"{server_url}/{repository}/issues/new?title=Repo+Squatting+Alert&labels=security&template=repo-squatting.md"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verified Downloads - {_esc(repository)}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px; margin: 0 auto; padding: 2rem;
            background: #f6f8fa; color: #24292f; line-height: 1.6;
        }}
        .header {{ text-align: center; padding: 2rem; background: white;
            border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        .status {{ display: inline-block; padding: 0.5rem 1.5rem; border-radius: 6px;
            font-weight: 600; font-size: 1.1rem; color: white; margin: 0.75rem 0; }}
        .status.verified {{ background: #2ea44f; }}
        .status.warning {{ background: #d73a49; }}
        .status.checking {{ background: #6e7681; }}
        .status.info {{ background: #bf8700; }}
        .card {{ background: white; padding: 1.5rem 2rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }}
        .card h2 {{ font-size: 1.2rem; margin-bottom: 1rem; color: #24292f; }}
        .alert {{ padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem; }}
        .alert.danger {{ background: #ffebe9; border: 1px solid #d73a49; }}
        .alert.success {{ background: #dafbe1; border: 1px solid #2ea44f; }}
        .alert.warn {{ background: #fff8c5; border: 1px solid #bf8700; }}
        .alert h3 {{ margin-bottom: 0.5rem; }}
        .assets-table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        .assets-table th {{ text-align: left; padding: 0.5rem; border-bottom: 2px solid #d0d7de;
            font-size: 0.85rem; color: #57606a; }}
        .assets-table td {{ padding: 0.75rem 0.5rem; border-bottom: 1px solid #d0d7de; }}
        .asset-name {{ font-family: monospace; font-size: 0.95rem; word-break: break-all; }}
        .asset-size {{ color: #57606a; white-space: nowrap; }}
        .download-btn {{ display: inline-block; padding: 0.4rem 1rem; background: #2ea44f;
            color: white; border-radius: 6px; text-decoration: none; font-weight: 600;
            font-size: 0.9rem; }}
        .download-btn:hover {{ background: #2c974b; }}
        .release-link {{ margin-top: 1rem; font-size: 0.9rem; }}
        a {{ color: #0969da; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ background: #f6f8fa; padding: 0.15rem 0.4rem; border-radius: 4px;
            font-size: 0.9rem; word-break: break-all; }}
        .footer {{ text-align: center; color: #57606a; font-size: 0.85rem; margin-top: 2rem; }}
        .spinner {{ display: inline-block; width: 18px; height: 18px; border: 2px solid #fff;
            border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite;
            vertical-align: middle; margin-right: 6px; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .report-btn {{ display: inline-block; margin-top: 1rem; padding: 0.5rem 1rem;
            background: #cf222e; color: white; border-radius: 6px; text-decoration: none;
            font-weight: 600; font-size: 0.9rem; }}
        .report-btn:hover {{ background: #a40e26; text-decoration: none; }}
        .referrer-info {{ font-size: 0.8rem; color: #57606a; margin-top: 1rem;
            padding-top: 0.75rem; border-top: 1px solid #d0d7de; }}
        #verification-result {{ min-height: 60px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 {_esc(repository)}</h1>
        <p>Verified download page</p>
        <div id="status-badge" class="status checking">
            <span class="spinner"></span> Checking...
        </div>
    </div>

    <div id="verification-result"></div>

    {downloads_html}

    <div class="card">
        <h2>About This Page</h2>
        <p>
            This page is hosted on <strong>{_esc(owner)}.github.io</strong>, which can only
            be deployed by the owner of the <a href="{server_url}/{_esc(repository)}">{_esc(repository)}</a> repository.
            Attackers who fork the repository cannot modify this page.
        </p>
        <p style="margin-top: 0.75rem;">
            Downloads on this page link directly to official
            <a href="{server_url}/{_esc(repository)}/releases">GitHub Release</a> assets.
        </p>
    </div>

    <div class="footer">
        <p>Protected by <a href="https://github.com/repo-trust/repo-trust">Repo Trust</a></p>
    </div>

    <script>
    (function() {{
        const REPO_OWNER = '{owner}';
        const REPO_NAME = '{repo_name}';
        const FULL_REPO = '{repository}';
        const OFFICIAL_REPO_URL = '{server_url}/{repository}';
        const REPORT_URL = '{report_url}';

        const statusBadge = document.getElementById('status-badge');
        const resultDiv = document.getElementById('verification-result');
        const referrer = document.referrer || '';

        function esc(text) {{
            const d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        }}

        function extractCommit(url) {{
            const patterns = [
                /\\/tree\\/([a-f0-9]{{7,40}})/i,
                /\\/commit\\/([a-f0-9]{{7,40}})/i,
                /\\/blob\\/([a-f0-9]{{7,40}})\\//i,
            ];
            for (const p of patterns) {{
                const m = url.match(p);
                if (m) return m[1];
            }}
            return null;
        }}

        function isExpectedRepo(url) {{
            if (!url) return false;
            const patterns = [
                new RegExp(`github\\.com\\/${{REPO_OWNER}}\\/${{REPO_NAME}}(\\/|$|\\?|#)`, 'i'),
                new RegExp(`${{REPO_OWNER}}\\.github\\.io\\/${{REPO_NAME}}(\\/|$|\\?|#)`, 'i'),
            ];
            return patterns.some(p => p.test(url));
        }}

        async function checkCommit(sha) {{
            try {{
                const repoRes = await fetch(
                    `https://api.github.com/repos/${{FULL_REPO}}`,
                    {{ headers: {{ 'Accept': 'application/vnd.github.v3+json' }} }}
                );
                if (!repoRes.ok) return {{ error: true }};
                const repoData = await repoRes.json();
                const branch = repoData.default_branch;

                const cmpRes = await fetch(
                    `https://api.github.com/repos/${{FULL_REPO}}/compare/${{sha}}...${{branch}}`,
                    {{ headers: {{ 'Accept': 'application/vnd.github.v3+json' }} }}
                );

                if (cmpRes.status === 404) return {{ inBranch: false }};
                if (!cmpRes.ok) return {{ error: true }};

                const cmpData = await cmpRes.json();
                return {{
                    inBranch: ['ahead', 'identical', 'behind'].includes(cmpData.status),
                    branch: branch,
                }};
            }} catch (e) {{
                return {{ error: true }};
            }}
        }}

        function showVerified(msg, detail) {{
            statusBadge.className = 'status verified';
            statusBadge.innerHTML = '✅ Official Repository';
            resultDiv.innerHTML = `
                <div class="alert success">
                    <h3>✅ ${{msg}}</h3>
                    ${{detail ? `<p>${{detail}}</p>` : ''}}
                </div>
            ` + (referrer ? `<div class="referrer-info">Arrived from: <code>${{esc(referrer)}}</code></div>` : '');
        }}

        function showWarning(msg, detail) {{
            statusBadge.className = 'status warning';
            statusBadge.innerHTML = '⚠️ WARNING';

            const reportParams = new URLSearchParams({{
                title: 'Repo Squatting Alert',
                labels: 'security',
                body: `## Repo Squatting Report\\n\\n`
                    + `**Suspicious URL:** ${{referrer}}\\n`
                    + `**Detection:** ${{msg}}\\n`
                    + `**Time:** ${{new Date().toISOString()}}\\n\\n`
                    + `This report was generated by the Repo Trust verification page.`,
            }});
            const issueUrl = `${{OFFICIAL_REPO_URL}}/issues/new?${{reportParams.toString()}}`;

            resultDiv.innerHTML = `
                <div class="alert danger">
                    <h3>⚠️ ${{msg}}</h3>
                    ${{detail ? `<p>${{detail}}</p>` : ''}}
                    <p style="margin-top:1rem"><strong>Do not download</strong> files from the page you came from.
                    Use the official downloads below instead.</p>
                    <a href="${{issueUrl}}" class="report-btn" target="_blank">Report this to the maintainer</a>
                </div>
            ` + (referrer ? `<div class="referrer-info">Suspicious referrer: <code>${{esc(referrer)}}</code></div>` : '');
        }}

        function showInfo(msg) {{
            statusBadge.className = 'status info';
            statusBadge.innerHTML = '🔒 Verified Page';
            resultDiv.innerHTML = `
                <div class="alert warn">
                    <h3>Manual Verification</h3>
                    <p>${{msg}}</p>
                    <p style="margin-top:0.75rem">Downloads below are from the official
                    <a href="${{OFFICIAL_REPO_URL}}">${{FULL_REPO}}</a> repository.</p>
                </div>
            `;
        }}

        async function verify() {{
            // No referrer — privacy settings or direct navigation
            if (!referrer) {{
                showInfo(
                    'Your browser did not send referrer information (privacy settings or direct navigation). '
                    + 'This page is hosted on <strong>' + REPO_OWNER + '.github.io</strong>, which is controlled by the repository owner.'
                );
                return;
            }}

            // Referrer from a different repo
            if (!isExpectedRepo(referrer)) {{
                if (referrer.includes('github.com/')) {{
                    showWarning(
                        'You came from a different repository than expected.',
                        `Expected: <code>github.com/${{FULL_REPO}}</code><br>Actual: <code>${{esc(referrer)}}</code>`
                    );
                }} else {{
                    showInfo('You arrived from an external site. Downloads below are from the official repository.');
                }}
                return;
            }}

            // Referrer has a commit hash — check if it's legitimate
            const commit = extractCommit(referrer);
            if (commit) {{
                statusBadge.innerHTML = '<span class="spinner"></span> Verifying commit...';
                const result = await checkCommit(commit);

                if (result.error) {{
                    showInfo(
                        'Unable to verify the commit due to an API error. '
                        + 'Downloads below are from the official repository.'
                    );
                    return;
                }}

                if (!result.inBranch) {{
                    showWarning(
                        'Possible Repo Squatting Detected',
                        `The commit <code>${{commit}}</code> is <strong>not</strong> in the official branch history. `
                        + `This is a strong indicator that the page you came from is a fork-based impersonation.`
                    );
                    return;
                }}

                showVerified(
                    'Official Repository Confirmed',
                    `Commit <code>${{commit.substring(0, 7)}}</code> is in the <code>${{result.branch}}</code> branch.`
                );
                return;
            }}

            // Normal referrer from expected repo, no commit hash
            showVerified(
                'Official Repository Confirmed',
                'You came from the official repository page.'
            );
        }}

        verify();
    }})();
    </script>
</body>
</html>"""


def _esc(text):
    """Escape text for HTML embedding."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def publish():
    """Publish the badge and download page to GitHub Pages."""
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")

    if not repository or not token:
        print("[repo-trust] ERROR: GITHUB_REPOSITORY and GITHUB_TOKEN required")
        return

    owner = repository.split("/")[0]
    repo_name = repository.split("/")[1]

    # Load release data
    release_data = {}
    if os.path.exists("release-data.json"):
        with open("release-data.json") as f:
            release_data = json.load(f)

    badge_url = f"https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/badge.svg"
    page_url = f"https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/"

    print(f"[repo-trust] Publishing to GitHub Pages")

    with tempfile.TemporaryDirectory() as tmpdir:
        pages_dir = Path(tmpdir) / "pages"
        pages_dir.mkdir()

        # Init git
        run_git("init", cwd=str(pages_dir))
        run_git("config", "user.name", "repo-trust-bot", cwd=str(pages_dir))
        run_git("config", "user.email", "repo-trust@users.noreply.github.com", cwd=str(pages_dir))

        # Set up remote
        remote_host = server_url.replace("https://", "").replace("http://", "")
        remote_url = f"https://x-access-token:{token}@{remote_host}/{repository}.git"
        run_git("remote", "add", "origin", remote_url, cwd=str(pages_dir))

        # Fetch or create gh-pages
        gh_pages_exists = branch_exists("gh-pages", str(pages_dir))

        if gh_pages_exists:
            print("[repo-trust] Found existing gh-pages branch")
            run_git("fetch", "origin", "gh-pages", cwd=str(pages_dir))
            run_git("checkout", "-b", "gh-pages", "origin/gh-pages", cwd=str(pages_dir))
        else:
            print("[repo-trust] Creating new gh-pages branch")
            run_git("checkout", "--orphan", "gh-pages", cwd=str(pages_dir))
            (pages_dir / ".nojekyll").touch()
            run_git("add", ".nojekyll", cwd=str(pages_dir))

        # Create repo-trust directory
        rt_dir = pages_dir / REPO_TRUST_PATH
        rt_dir.mkdir(exist_ok=True)

        # Write badge
        badge_content = render_badge(repository)
        (rt_dir / "badge.svg").write_text(badge_content)
        print("[repo-trust] Generated badge")

        # Write download page
        page_content = generate_download_page(repository, release_data)
        (rt_dir / "index.html").write_text(page_content)
        print("[repo-trust] Generated verified download page")

        # Stage, commit, push
        run_git("add", REPO_TRUST_PATH, cwd=str(pages_dir))

        status = run_git("status", "--porcelain", cwd=str(pages_dir), capture_output=True)
        if not status.stdout.strip():
            print("[repo-trust] No changes to commit (already up to date)")
            return page_url

        run_git("commit", "-m", "Update Repo Trust verified download page", cwd=str(pages_dir))

        try:
            run_git("push", "origin", "gh-pages", cwd=str(pages_dir))
        except RuntimeError:
            print("[repo-trust] Push failed, attempting pull and retry...")
            run_git("pull", "--rebase", "origin", "gh-pages", cwd=str(pages_dir))
            run_git("push", "origin", "gh-pages", cwd=str(pages_dir))

        print(f"[repo-trust] Published successfully")
        return page_url


def main():
    """Publish the verified download page to GitHub Pages."""
    page_url = publish()

    if page_url:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        owner = repository.split("/")[0]
        repo_name = repository.split("/")[1]
        badge_url = f"https://{owner}.github.io/{repo_name}/{REPO_TRUST_PATH}/badge.svg"

        print("")
        print("[repo-trust] Add this to your README:")
        print(f"    [![Repo Trust]({badge_url})]({page_url})")
        print("")


if __name__ == "__main__":
    main()
