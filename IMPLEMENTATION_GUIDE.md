# Repo Trust — Implementation & Installation Guide

This guide provides detailed, step-by-step instructions for installing and configuring Repo Trust on your GitHub repository.

<br>

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
   - [Step 1: Generate Signing Keys](#step-1-generate-signing-keys)
   - [Step 2: Configure Repository](#step-2-configure-repository)
   - [Step 3: Add GitHub Secret](#step-3-add-github-secret)
   - [Step 4: Create Workflow](#step-4-create-workflow)
   - [Step 5: Enable GitHub Pages](#step-5-enable-github-pages)
   - [Step 6: Add Badge to README](#step-6-add-badge-to-readme)
   - [Step 7: Verify Installation](#step-7-verify-installation)
4. [Configuration Options](#configuration-options)
5. [Operational Procedures](#operational-procedures)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)

<br>

## Overview

### What You Are Installing

Repo Trust adds **publisher-side distribution trust** to your GitHub repository.

Once installed:
- Your official releases generate a **cryptographically signed distribution manifest**
- Repo Trust verifies that manifest continuously
- A **visual trust badge** is published via GitHub Pages
- Forks and impersonators **cannot generate a valid badge**
- Users don't install or run anything — they just *see trust*

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR REPOSITORY                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Release   │───▶│ Repo Trust  │───▶│   Signed    │     │
│  │  Published  │    │   Action    │    │  Manifest   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                            │                   │            │
│                            ▼                   ▼            │
│                     ┌─────────────┐    ┌─────────────┐     │
│                     │   Badge     │    │   Release   │     │
│                     │  (Pages)    │    │   Assets    │     │
│                     └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Time to Complete

- Initial setup: **10-15 minutes**
- Per-release: **Automatic** (no manual steps)

<br>

## Prerequisites

Before installing Repo Trust, ensure you have:

| Requirement | Details |
|-------------|---------|
| GitHub Repository | Public or private repository on GitHub.com |
| GitHub Releases | At least one release, or the ability to create releases |
| GitHub Actions | Enabled for your repository |
| SSH/OpenSSL | Installed locally for key generation |
| Repository Admin | Permission to add secrets and enable Pages |

### Checking Prerequisites

```bash
# Verify SSH is available
ssh-keygen --help

# Verify you can create releases
# Go to: https://github.com/YOUR-ORG/YOUR-REPO/releases
```

<br>

## Installation Steps

### Step 1: Generate Signing Keys

Repo Trust uses SSH-based cryptographic signing. You need to generate a key pair.

#### Generate the Key Pair

```bash
# Generate an Ed25519 key pair (recommended)
ssh-keygen -t ed25519 -f repo-trust-key -N "" -C "repo-trust"
```

This creates two files:

| File | Purpose | Security |
|------|---------|----------|
| `repo-trust-key` | Private key for signing | **KEEP SECRET** |
| `repo-trust-key.pub` | Public key for verification | Safe to share |

#### Alternative: RSA Keys (if Ed25519 not available)

```bash
ssh-keygen -t rsa -b 4096 -f repo-trust-key -N "" -C "repo-trust"
```

#### Important Security Notes

- **Never commit the private key** to your repository
- **Store the private key securely** (password manager, vault, etc.)
- **Delete local copies** after adding to GitHub Secrets
- The private key will only be stored as a GitHub Secret

<br>

### Step 2: Configure Repository

#### Add the Public Key

Copy the public key to your repository root:

```bash
# Copy public key to repository
cp repo-trust-key.pub public_key.pub

# Add to git
git add public_key.pub
git commit -m "Add Repo Trust public verification key"
git push
```

#### Verify the Public Key

The file should contain a single line starting with:
- `ssh-ed25519 AAAA...` (for Ed25519 keys)
- `ssh-rsa AAAA...` (for RSA keys)

<br>

### Step 3: Add GitHub Secret

The private signing key must be stored as a GitHub Secret.

#### Navigate to Secrets

1. Go to your repository on GitHub
2. Click **Settings**
3. In the left sidebar, click **Secrets and variables**
4. Click **Actions**

#### Create the Secret

1. Click **New repository secret**
2. Configure:
   - **Name**: `REPO_TRUST_SIGNING_KEY`
   - **Value**: Paste the **entire contents** of `repo-trust-key`
3. Click **Add secret**

#### Verify Secret Contents

The secret value should look like:

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtz
... (multiple lines) ...
-----END OPENSSH PRIVATE KEY-----
```

**Include the BEGIN and END lines!**

#### Security Properties

GitHub Secrets have these security properties:
- Encrypted at rest
- Only accessible during workflow runs
- **Not accessible to forks** (this is critical for security)
- Not visible in logs
- Cannot be retrieved after creation

<br>

### Step 4: Create Workflow

Create the GitHub Actions workflow file.

#### Create the Workflow File

Create `.github/workflows/repo-trust.yml`:

```yaml
name: Repo Trust

on:
  release:
    types: [published]

permissions:
  contents: write

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Generate and publish Repo Trust verification
        uses: repo-trust/action@v1
        with:
          signing_key: ${{ secrets.REPO_TRUST_SIGNING_KEY }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Commit the Workflow

```bash
mkdir -p .github/workflows
# Create the file with content above
git add .github/workflows/repo-trust.yml
git commit -m "Add Repo Trust verification workflow"
git push
```

#### Workflow Explanation

| Section | Purpose |
|---------|---------|
| `on: release` | Triggers only when a release is published |
| `permissions: contents: write` | Allows uploading to releases and pushing to gh-pages |
| `GITHUB_TOKEN` | Automatically provided by GitHub Actions |
| `signing_key` | Your private key from secrets |

<br>

### Step 5: Enable GitHub Pages

Repo Trust publishes the trust badge via GitHub Pages.

#### If You Don't Have GitHub Pages Yet

1. Go to **Settings → Pages**
2. Under "Build and deployment":
   - **Source**: Deploy from a branch
   - **Branch**: `gh-pages` / `/ (root)`
3. Click **Save**

The `gh-pages` branch will be created automatically when Repo Trust runs.

#### If You Already Have GitHub Pages

**No action required!**

Repo Trust will:
- Detect your existing Pages configuration
- Create only the `/repo-trust/` subdirectory
- Never modify other content
- Never force-push

#### Verify Pages Configuration

After your first release with Repo Trust, verify:

1. Go to **Settings → Pages**
2. Confirm the site is published
3. Note the URL: `https://YOUR-USERNAME.github.io/YOUR-REPO/`

<br>

### Step 6: Add Badge to README

Add the trust badge to your README for visibility.

#### Badge Markdown

```markdown
![Repo Trust](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/distribution.svg)
```

#### With Link to Verification Page

```markdown
[![Repo Trust](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/distribution.svg)](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/)
```

#### Example in Context

```markdown
# My Awesome Project

[![Repo Trust](https://myorg.github.io/myproject/repo-trust/distribution.svg)](https://myorg.github.io/myproject/repo-trust/)

Download the latest release from [GitHub Releases](https://github.com/myorg/myproject/releases/latest).

...
```

<br>

### Step 7: Verify Installation

#### Trigger a Release

1. Go to **Releases** → **Draft a new release**
2. Create a tag (e.g., `v1.0.0`)
3. Upload your release artifacts (binaries, installers, etc.)
4. Click **Publish release**

#### Monitor the Workflow

1. Go to **Actions** tab
2. Watch the "Repo Trust" workflow run
3. Verify it completes successfully

#### Verify Outputs

After successful completion:

1. **Release Assets**: Check that `repo-trust-manifest.json` and `repo-trust-manifest.json.sig` were added
2. **GitHub Pages**: Visit `https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/`
3. **Badge**: Verify the badge shows "VERIFIED"

<br>

## Configuration Options

### Workflow Input Parameters

| Input | Required | Description |
|-------|----------|-------------|
| `signing_key` | Yes | SSH private key for signing |
| `public_key` | No | Public key (optional if committed to repo) |

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `GITHUB_TOKEN` | Automatic | GitHub Actions token |
| `GITHUB_REPOSITORY` | Automatic | Owner/repo name |
| `GITHUB_REF_NAME` | Automatic | Release tag |
| `GITHUB_SHA` | Automatic | Commit SHA |

### Advanced: Custom Workflow

```yaml
name: Repo Trust

on:
  release:
    types: [published]
  workflow_dispatch:  # Allow manual trigger

permissions:
  contents: write

jobs:
  verify:
    runs-on: ubuntu-latest
    # Only run on non-fork repositories
    if: github.event.repository.fork == false
    steps:
      - uses: actions/checkout@v4
      
      - name: Repo Trust
        uses: repo-trust/action@v1
        with:
          signing_key: ${{ secrets.REPO_TRUST_SIGNING_KEY }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

<br>

## Operational Procedures

### Key Rotation

To rotate your signing key:

```bash
# 1. Generate new key pair
ssh-keygen -t ed25519 -f repo-trust-key-new -N "" -C "repo-trust"

# 2. Update public key in repository
cp repo-trust-key-new.pub public_key.pub
git add public_key.pub
git commit -m "Rotate Repo Trust signing key"
git push

# 3. Update GitHub Secret
# Go to Settings → Secrets → REPO_TRUST_SIGNING_KEY
# Replace with contents of repo-trust-key-new

# 4. Securely delete old keys
rm repo-trust-key repo-trust-key.pub
rm repo-trust-key-new repo-trust-key-new.pub
```

### Revoking Trust

To stop publishing verified badges:

1. Delete the `REPO_TRUST_SIGNING_KEY` secret
2. Future releases will not have valid signatures
3. The badge will show "UNVERIFIED"

### Multiple Maintainers

**Option A: Shared Key**
- Store the signing key in a team password manager
- All maintainers use the same key

**Option B: Key Rotation**
- Rotate keys when maintainer access changes
- Each maintainer generates their own key

<br>

## Troubleshooting

### Common Issues

#### Workflow Fails: "REPO_TRUST_SIGNING_KEY is required"

**Cause**: Secret not configured properly

**Solution**:
1. Go to Settings → Secrets → Actions
2. Verify `REPO_TRUST_SIGNING_KEY` exists
3. Verify it contains the full private key including headers

#### Badge Shows UNVERIFIED

**Possible causes**:
1. Release hasn't completed yet (wait for workflow)
2. Workflow failed (check Actions tab)
3. GitHub Pages not enabled
4. DNS propagation (wait 5-10 minutes)

#### Signature Verification Failed

**Cause**: Key mismatch

**Solution**:
1. Verify `public_key.pub` matches your signing key
2. Re-derive public key: `ssh-keygen -y -f private_key > public_key.pub`
3. Commit updated public key

#### GitHub Pages Not Working

**Steps**:
1. Go to Settings → Pages
2. Verify source is set to `gh-pages` branch
3. Verify the branch exists (check branches list)
4. Try accessing `https://USERNAME.github.io/REPO/repo-trust/` directly

### Debug Mode

To enable verbose logging, add to your workflow:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  ACTIONS_STEP_DEBUG: true
```

<br>

## Security Considerations

### Threat Model

Repo Trust protects against:

| Threat | Protection |
|--------|------------|
| Fork impersonation | Forks cannot access signing secrets |
| README modification | Badge points to original repo's Pages |
| Release tampering | Signatures bind artifacts to manifest |
| Namespace squatting | Visual verification exposes mismatches |

### What Repo Trust Does NOT Protect Against

| Scenario | Why |
|----------|-----|
| Compromised maintainer | They have the signing key |
| Compromised repository | Attacker could change workflow |
| Malicious initial upload | Repo Trust verifies origin, not safety |

### Security Best Practices

1. **Limit secret access**: Only repository admins should manage secrets
2. **Monitor workflow runs**: Check for unexpected modifications
3. **Use branch protection**: Require reviews for workflow changes
4. **Rotate keys regularly**: Annual rotation is recommended
5. **Audit access logs**: Review who has accessed repository settings

### Incident Response

If you suspect key compromise:

1. **Immediately** delete the `REPO_TRUST_SIGNING_KEY` secret
2. Generate a new key pair
3. Update `public_key.pub` in repository
4. Add new secret
5. Publish a new release to update the badge
6. Notify users to verify they have the latest release

<br>

## Summary Checklist

- [ ] Generated SSH key pair
- [ ] Committed `public_key.pub` to repository
- [ ] Added `REPO_TRUST_SIGNING_KEY` secret
- [ ] Created `.github/workflows/repo-trust.yml`
- [ ] Enabled GitHub Pages (gh-pages branch)
- [ ] Added badge to README
- [ ] Published a test release
- [ ] Verified badge shows VERIFIED
- [ ] Securely deleted local private key

<br>

## Getting Help

- **Documentation**: [Repo Trust README](https://github.com/kahalewai/repo-trust)
- **Issues**: [GitHub Issues](https://github.com/kahalewai/repo-trust/issues)
- **Security**: Report security issues privately via GitHub Security Advisories

<br>

**Repo Trust — Making authenticity obvious.**
