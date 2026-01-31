# Repo Trust

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Repo Trust detects repo squatting attacks on GitHub.**

It lets users verify with one click that they're viewing the official repository — not a malicious fork commit impersonating it.

---

## 🚨 The Problem: Repo Squatting

Attackers don't need to compromise repositories — they can **impersonate** them.

**How the attack works:**

1. Attacker forks a popular repo (e.g., `github.com/desktop/desktop`)
2. Attacker modifies the README in their fork to point to malware
3. Due to GitHub's fork network design, this commit appears at:  
   `github.com/desktop/desktop/tree/<malicious_commit_hash>`
4. Attacker promotes this URL via Google Ads
5. User lands on what **looks like** the official repo — URL says `github.com/desktop/desktop`
6. User downloads malware thinking it's legitimate

**This attack has been used to distribute malware disguised as GitHub Desktop, Chrome, 1Password, and Bitwarden.** As of January 2026, GitHub has acknowledged this issue but it can still be reproduced.

**Why traditional solutions fail:**

- ✖️ **Hashes don't help** — attacker controls both the binary and the displayed hash
- ✖️ **URL checking doesn't help** — the URL IS the official domain
- ✖️ **Visual inspection doesn't help** — the page looks identical to the real one

---

## ✅ The Solution: Click to Verify

Repo Trust adds a verification badge to your README:

```
[Repo Trust] [your-org/your-repo] [🔒 Click to Verify]
```

**When a user clicks the badge:**

1. Their browser sends the **Referer header** (the page they clicked from)
2. The verification page checks if the URL contains a commit hash
3. If yes, it calls the **GitHub API** to verify that commit is in the official branch
4. **Fork commits are detected** — they're not in the official history
5. User sees clear ✅ VERIFIED or ⚠️ WARNING result

**Why this works:**

- ✅ **Referer is browser-controlled** — attackers cannot fake it
- ✅ **Commit ancestry is verifiable** — we can check if a commit is in `main`
- ✅ **GitHub API is public** — no authentication needed
- ✅ **Works on GitHub Pages** — no external servers required
- ✅ **Fails safely** — if Referer is missing, we prompt manual verification

---

## 🎯 What Users See

### When coming from the official page:
```
✅ VERIFIED - Official Distribution Confirmed
You came from the official your-org/your-repo repository page.
```

### When coming from a repo squatting attack:
```
⚠️ WARNING - Possible Repo Squatting Detected
You are viewing a commit that is NOT part of the official repository history.
This is a strong indicator of a repo squatting attack.

→ Go to the official repository: github.com/your-org/your-repo
```

---

## ⚡ Quick Start

### Step 1: Generate a signing key

```bash
ssh-keygen -t ed25519 -f repo-trust-key -N "" -C "repo-trust"
```

This creates `repo-trust-key` (private) and `repo-trust-key.pub` (public).

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
4. Value: Paste contents of `repo-trust-key`

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
[![Repo Trust](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/distribution.svg)](https://YOUR-USERNAME.github.io/YOUR-REPO/repo-trust/)
```

**Important:** The badge must LINK to the verification page, not just display an image.

---

## 🔒 Security Model

### How Verification Works

```
User views README at:
  github.com/desktop/desktop/tree/abc123  (malicious fork commit)
                    ↓
User clicks "Repo Trust - Click to Verify" badge
                    ↓
Browser navigates to:
  desktop.github.io/desktop/repo-trust/
                    ↓
Browser sends Referer header:
  Referer: https://github.com/desktop/desktop/tree/abc123
                    ↓
Verification page extracts commit hash: abc123
                    ↓
Calls GitHub API:
  GET /repos/desktop/desktop/compare/abc123...main
                    ↓
If commit NOT in main branch history:
  ⚠️ WARNING: Repo squatting detected!
                    ↓
If commit IS in main branch history:
  ✅ VERIFIED: Official repository
```

### What Repo Trust Detects

| Attack | Detection |
|--------|-----------|
| Fork commit impersonation (repo squatting) | ✅ Detected via commit ancestry check |
| Different repository with copied badge | ✅ Detected via Referer mismatch |
| Typosquatting (similar repo name) | ✅ Detected via Referer mismatch |
| Modified README in official repo | ❌ Not detected (requires compromised maintainer) |

### What Repo Trust Does NOT Do

- ❌ Scan code for vulnerabilities  
- ❌ Judge software safety  
- ❌ Prevent malicious commits by maintainers  
- ❌ Replace code signing certificates

**Repo Trust answers one question:**
> **Am I viewing the official repository, or a repo squatting attack?**

---

## 📦 What Gets Published

Each release will contain:

| File | Description |
|------|-------------|
| `repo-trust-manifest.json` | Signed manifest with artifact hashes |
| `repo-trust-manifest.json.sig` | SSH signature of the manifest |

The GitHub Pages site will contain:

| URL | Description |
|-----|-------------|
| `/repo-trust/distribution.svg` | Verification badge |
| `/repo-trust/index.html` | Dynamic verification page |

---

## 🔄 GitHub Pages Compatibility

Repo Trust **coexists safely** with existing GitHub Pages content.

- Only writes to `/repo-trust/` subdirectory
- Never force-pushes
- Never deletes existing content

---

## 🛡️ Fork Behavior

When someone forks your repository:

- They **can** copy your workflow files
- They **can** copy your badge markdown  
- They **cannot** access your signing secret
- Their verification page won't exist on your GitHub Pages
- If they create their own, it will show their repo name (not yours)

---

## ❓ FAQ

### Why "Click to Verify" instead of a status badge?

Static badges can be copied. The security comes from the **verification page**, not the badge image. The badge is just a button that takes users to verification.

### What if Referer is blocked by privacy settings?

The verification page will show "Manual Check Required" and guide users to verify they're on the official repository URL.

### Can attackers link their badge to my verification page?

Yes, but the verification page checks the **Referer**. If someone clicks a badge from a different repository, the verification will detect the mismatch.

### Does this work with GitHub Enterprise Server?

Yes. Set these environment variables in your workflow:

```yaml
env:
  GITHUB_API_URL: https://github.your-company.com/api/v3
  GITHUB_SERVER_URL: https://github.your-company.com
```

---

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Referer-based commit verification
- ✅ GitHub API commit ancestry checking
- ✅ SSH-based manifest signing
- ✅ GitHub Pages hosting

### Phase 2 (Planned)
- ⬜ Sigstore/OIDC keyless signing
- ⬜ Browser extension for automatic verification
- ⬜ GitHub Action that comments on suspicious commits

---

## 🤝 Who Should Use Repo Trust

- Open-source maintainers publishing binaries
- CLI tool authors
- Desktop application developers
- **Any popular repository** at risk of being impersonated

If attackers might target your repository with ads or fake downloads, **Repo Trust helps your users verify authenticity**.

---

## 📜 License

Apache 2.0

---

## 💡 The Key Insight

> **The browser's Referer header is the trust anchor.**

Attackers can control what's displayed on a page, but they cannot control what URL the browser reports when a user clicks a link. By checking where users came from — and verifying that commits are in the official history — we can detect repo squatting attacks.

**Repo Trust doesn't ask users to be security experts. It makes verification one click.**

---

## 🙏 Acknowledgments

Repo Trust was designed to address real-world repo squatting attacks like the GitHub Desktop campaign discovered in September 2025 (still reproducible as of January 2026).

Research references:
- [GMO Cybersecurity - Repo Squatting and GPUGate](https://gmo-cybersecurity.com/blog/revisiting-gpugate-repo-squatting-and-opencl-deception-to-deliver-hijackloader/)
- [Arctic Wolf - GPUGate Malware Analysis](https://arcticwolf.com/resources/blog/gpugate-malware-malicious-github-desktop-implants-use-hardware-specific-decryption-abuse-google-ads-target-western-europe/)
