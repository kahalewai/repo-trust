<div align="center">

<img width="409" height="368" alt="repo-trust2" src="https://github.com/user-attachments/assets/1075a104-512f-43cd-bf63-34472693bfa8" />

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
</div>

<br>

Repo Trust is a publisher-side distribution trust system that gives maintainers a verified download page on GitHub Pages, a domain attackers cannot control, and a README badge that safely routes users to that page. Instead of placing download links directly in your README (which attackers can modify in fork commits), Repo Trust moves downloads to a trusted location and optionally warns users if they arrived from a suspicious source.

<br>

## The Problem: Repo Squatting

Attackers don’t need to compromise your repository, they can **impersonate it**.

How the attack works:

1. Attacker forks a popular repo (e.g., `github.com/desktop/desktop`)
2. Attacker modifies the README in their fork to point to malware
3. Due to GitHub’s fork network design, this commit appears at:  
   `github.com/desktop/desktop/tree/<malicious_commit_hash>`
4. Attacker promotes this URL via Google Ads
5. User lands on what *looks like* the official repo — the URL says `github.com/desktop/desktop`
6. User downloads malware thinking it’s legitimate

This attack has been used to distribute malware disguised as GitHub Desktop, Chrome, 1Password, and Bitwarden. As of January 2026, GitHub has acknowledged this issue, but it can still be reproduced.

<br>

### Why traditional defenses fail

- URL checking doesn’t help, the URL *is* the official domain
- Visual inspection doesn’t help, the page looks identical to the real one
- Hashes don’t help, the attackers control both the binary and the displayed hash
- GitHub’s warning banner can be bypassed using anchor links that scroll past it

<br>

## The Root Cause

If your download links are in your README, they are vulnerable.

Attackers can modify README content in fork commits, and those commits appear under your repository’s URL. Every link, badge, and button in your README is under their control in that view.

The fix is a pattern change: serve downloads from a location the attacker cannot modify.

Your GitHub Pages site (`your-org.github.io/your-repo/`) is deployed from your repository’s `gh-pages` branch. Attackers cannot push to it. They cannot deploy to your Pages domain.

Repo Trust makes this pattern change easy.

<br>

## The Solution

Repo Trust is a GitHub Action that deploys two things to your GitHub Pages site:

1. **A verified download page** at  
   `https://your-org.github.io/your-repo/repo-trust/`

   - Lists your latest release assets
   - Hosted on your GitHub Pages domain
   - Cannot be modified by attackers
   - Optionally warns users if they arrived from a suspicious commit

2. **A “Download from Verified Page” badge** for your README

   - Links to the verified download page
   - If attackers keep the badge → users escape to safety
   - If attackers remove it → no download links remain
   - If attackers replace it → it points to a different domain

**Key insight:** the badge is not a verification signal, it is a navigation escape to a trusted location.

<br>

### Bonus: Referer-Based Detection

When a user clicks the badge, their browser sends a `Referer` header containing the page they came from.

The verification page:

1. Extracts any commit hash from the Referer URL
2. Calls the GitHub API
3. Checks whether that commit exists in the official branch history
4. Shows **⚠️ WARNING** if the commit comes from a fork
5. Shows **✅ VERIFIED** if the commit is legitimate (or no hash is present)

If the Referer header is unavailable, the page still functions as a safe download portal. Detection is a bonus layer, not a requirement.

<br>

## What Users See

### Normal visit (official page or direct navigation)

```

✅ Official Repository Confirmed
Downloads below are from the official your-org/your-repo repository.

📦 Latest Release: v2.1.0

* app-linux-x64.tar.gz     [Download]
* app-macos-arm64.dmg     [Download]
* app-windows-x64.exe     [Download]

```

### When arriving from a repo squatting attack

```

⚠️ WARNING - Possible Repo Squatting Detected

You are viewing a commit that is NOT part of the official repository history.
Do not download files from the page you came from.

📦 Official Downloads
→ Go to the official repository: github.com/your-org/your-repo

````

The user is rescued regardless of how they arrived.

<br>

## Quick Start

### Step 1: Add the workflow

Create `.github/workflows/repo-trust.yml`:

```yaml
name: Repo Trust

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Repo Trust
        uses: repo-trust/repo-trust@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
````

<br>

### Step 2: Enable GitHub Pages

1. Go to **Settings → Pages**
2. Set Source to **Deploy from a branch**
3. Select **gh-pages** branch

<br>

### Step 3: Add the badge to your README

```markdown
[![Download from Verified Page](https://YOUR-ORG.github.io/YOUR-REPO/repo-trust/badge.svg)](https://YOUR-ORG.github.io/YOUR-REPO/repo-trust/)
```

<br>

### Step 4: Remove direct download links from your README

This is the most important step.


## Download

Get the latest release from our
[verified download page](https://YOUR-ORG.github.io/YOUR-REPO/repo-trust/).


That’s it! No signing keys, no secrets, no manifests.

<br>

## Security Model

### What Repo Trust Protects Against

| Attack                                     | Protection                           |
| ------------------------------------------ | ------------------------------------ |
| Fork commit impersonation (repo squatting) | ✅ Downloads served from GitHub Pages |
| Attacker keeps badge in modified README    | ✅ User escapes to verified page      |
| Attacker removes badge                     | ⚠️ No download links remain          |
| Attacker replaces badge                    | ⚠️ Links to different domain         |
| Similar-named repositories                 | ✅ Referer mismatch detected          |


<br>

## What Gets Published

The GitHub Pages site contains:

| Path                     | Description            |
| ------------------------ | ---------------------- |
| `/repo-trust/index.html` | Verified download page |
| `/repo-trust/badge.svg`  | README badge           |

No release assets are modified.

<br>

## GitHub Pages Compatibility

Repo Trust coexists safely with existing Pages content:

* Only writes to `/repo-trust/`
* Never force-pushes
* Never deletes existing files

<br>

## Fork Behavior

When someone forks your repository:

* They can copy your workflow and badge markdown
* They **cannot** deploy to your GitHub Pages domain
* Their badge still links to **your** verified page
* If they deploy Pages, the domain will be different

<br>

## Recommendations for Maintainers

> Do not put download links in your README.

Instead, direct users to:

* Your GitHub Pages verified download page
* Your GitHub Releases page
* Your project website

Your README is rendered inside fork commits. Your GitHub Pages site is not.

<br>

## FAQ

### Why not just use GitHub Releases?

Release URLs can still be reached through fork commits. GitHub Pages is the cleanest trust boundary because it requires write access to your repository to deploy.

### What if Referer is blocked?

The page still works as a download portal. The warning is a bonus layer.

### Can attackers link to my verified page?

Yes, and that’s good. If users land on your real page, they’ve escaped the attack.

### Does this work with GitHub Enterprise Server?

Yes. Set:

```yaml
env:
  GITHUB_API_URL: https://github.your-company.com/api/v3
  GITHUB_SERVER_URL: https://github.your-company.com
```

<br>

## Who Should Use Repo Trust

* Open-source maintainers publishing binaries
* CLI tool authors
* Desktop application developers
* Any popular repository at risk of impersonation

If attackers might target your project with fake downloads, **Repo Trust helps users find the real files**.

<br>

## License

Apache 2.0

