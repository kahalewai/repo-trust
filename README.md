# Repo Trust

[![Repo Trust](https://img.shields.io/badge/Repo%20Trust-VERIFIED-brightgreen)](https://github.com/kahalewai/repo-trust)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Repo Trust is a publisher-side distribution trust system for GitHub repositories. It lets maintainers cryptographically prove that downloadable artifacts were published by the official repository, and lets users see that proof instantly, without installing anything.

<br>

## The Problem

Repo Squatters don't compromise repositories, they impersonate them.

Attackers:
- Fork popular repos
- Replace download links in the README
- Promote fake installers via search ads
- Rely on visual similarity and trust confusion

Hashes don't help when attackers control both the binary and the hash.

This technique, called repo squatting, has been used to distribute malware disguised as legitimate software like GitHub Desktop, Chrome, 1Password, and Bitwarden.

<br>

## The Solution

Repo Trust flips the security model:

> Publishers prove authenticity. Users just look.

When you install Repo Trust:

1. On every release, a signed manifest is generated listing all artifacts with their cryptographic hashes
2. The manifest is signed with your private key
3. A visual trust badge is published to GitHub Pages
4. Forks and impersonators fail automatically - they can't forge your signature

<br>

## What Users See

| Badge | Meaning |
|-------|---------|
| 🟢 **VERIFIED** | Official release, signed by the repository owner |
| 🔴 **UNVERIFIED** | Missing, invalid, or impersonated distribution |

**If the badge isn't green, it isn't official.**

Users don't install anything. They don't verify hashes. They just look at the badge.

<br>

## Quick Start

### Step 1: Generate a signing key

```bash
ssh-keygen -t ed25519 -f repo-trust-key -N "" -C "repo-trust"
```

This creates:
- `repo-trust-key` — **Private key** (keep this secret!)
- `repo-trust-key.pub` — **Public key** (commit this to your repo)

### Step 2: Add the public key to your repository

```bash
cp repo-trust-key.pub public_key.pub
git add public_key.pub
git commit -m "Add Repo Trust public key"
git push
```

### Step 3: Add the private key as a GitHub Secret

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `REPO_TRUST_SIGNING_KEY`
4. Value: Paste the entire contents of `repo-trust-key`

### Step 4: Add the workflow

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
      - uses: actions/checkout@v4
      
      - name: Repo Trust
        uses: repo-trust/action@v1
        with:
          signing_key: ${{ secrets.REPO_TRUST_SIGNING_KEY }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Step 5: Enable GitHub Pages

1. Go to **Settings → Pages**
2. Set Source to **Deploy from a branch**
3. Select **gh-pages** branch

### Step 6: Add the badge to your README

```markdown
![Repo Trust](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/distribution.svg)
```

<br>

## What Gets Published

Each release will contain:

| File | Description |
|------|-------------|
| `repo-trust-manifest.json` | Signed manifest with artifact hashes |
| `repo-trust-manifest.json.sig` | SSH signature of the manifest |

The GitHub Pages site will contain:

| URL | Description |
|-----|-------------|
| `/<repo>/repo-trust/distribution.svg` | Trust badge |
| `/<repo>/repo-trust/index.html` | Verification info page |

<br>

## Security Model

### What Repo Trust Guarantees

✅ **Publisher authenticity** — Only the key holder can sign manifests  
✅ **Fork resistance** — Forks cannot access your signing secret  
✅ **Artifact integrity** — Hashes are bound to the signature  
✅ **Visual trust signal** — Users see verification status at a glance  

### What Repo Trust Does NOT Do

❌ Scan code for vulnerabilities  
❌ Judge software safety  
❌ Prevent malicious commits  
❌ Replace code signing certificates  

Repo Trust answers one question only:

> Was this distribution published by the real repository owner?

<br>

## GitHub Pages Compatibility

Repo Trust is designed to coexist safely with existing GitHub Pages content.

### If you don't have GitHub Pages yet

- Repo Trust creates the `gh-pages` branch
- Publishes only to `/repo-trust/`
- Leaves room for you to add docs, a landing page, etc.

### If you already have GitHub Pages

- Repo Trust never force-pushes
- Repo Trust never deletes existing content
- Repo Trust only writes to `/repo-trust/`
- Your existing site remains untouched

<br>

## Key Management

### Rotating Keys

1. Generate a new key pair
2. Update `public_key.pub` in your repository
3. Update the `REPO_TRUST_SIGNING_KEY` secret
4. Publish a new release

### Multiple Maintainers

Option A: Share the signing key securely among maintainers  
Option B: Rotate keys when maintainer access changes

### Revoking Trust

1. Delete the `REPO_TRUST_SIGNING_KEY` secret
2. The badge will show **UNVERIFIED** on future releases

<br>

## Fork Behavior

When someone forks your repository:

- They can copy your workflow files
- They can copy your badge markdown
- They cannot access your signing secret
- They cannot generate valid signatures
- Their badge will show **UNVERIFIED**

The badge URL points to **your** GitHub Pages, not theirs.

<br>

## Manifest Schema

```json
{
  "repo_trust_version": "1.0",
  "repository": {
    "owner": "your-username",
    "name": "your-repo",
    "full_name": "your-username/your-repo",
    "git_url": "https://github.com/your-username/your-repo"
  },
  "release": {
    "tag": "v1.0.0",
    "commit": "abc123...",
    "published_at": "2025-01-30T12:00:00Z",
    "release_id": 123456
  },
  "artifacts": [
    {
      "filename": "myapp-linux-amd64.tar.gz",
      "sha256": "abc123...",
      "size_bytes": 12345678,
      "download_url": "https://github.com/.../myapp-linux-amd64.tar.gz"
    }
  ],
  "generated_at": "2025-01-30T12:00:00Z",
  "generator": {
    "name": "repo-trust",
    "version": "1.0.0"
  }
}
```

<br>

## Roadmap

### Phase 1 (Current)
- ✅ SSH-based signing
- ✅ GitHub-only hosting
- ✅ Visual badge system

### Phase 2 (Planned)
- ⬜ Sigstore/OIDC keyless signing
- ⬜ Transparency log integration
- ⬜ Multi-forge support (GitLab, Bitbucket)
- ⬜ External verification service

The manifest format is forward-compatible - existing installations will work with Phase 2.

<br>

## Who Should Use Repo Trust

- Open-source maintainers publishing binaries
- CLI tool authors
- Desktop application developers
- Anyone whose users download files from their repo

If users download things from your repository, **Repo Trust applies**.

<br>

## License

Apache 2.0

<br>

## The Key Insight

> Attackers can fake artifacts, but they can't fake identity when verification is opinionated and centralized.

Repo Trust doesn't prevent attackers from uploading malware. It makes legitimacy expensive to fake.

When your official repository shows a green badge and a fork shows red (or nothing), users know what's real.

<br>

## Acknowledgments

Repo Trust was designed to address real-world attacks like the GitHub Desktop repo squatting campaign discovered in late 2025. It draws inspiration from:

- [Sigstore](https://sigstore.dev) — Keyless signing infrastructure
- [SLSA](https://slsa.dev) — Supply chain security framework
- [The Update Framework (TUF)](https://theupdateframework.io) — Secure software updates

<br>

Repo Trust doesn't ask users to be careful. It makes authenticity obvious.
