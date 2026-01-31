# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Repo Trust, please report it responsibly:

1. **Do NOT open a public issue**
2. Email security concerns to the maintainers privately, or
3. Use GitHub's private vulnerability reporting feature

We will respond within 48 hours and work with you to understand and address the issue.

---

## Threat Model

### What Repo Trust Protects Against

| Threat | Protection | Mechanism |
|--------|------------|-----------|
| **Repo squatting (fork commits)** | ✅ Strong | Referer contains commit hash; GitHub API verifies ancestry |
| **Different repo with copied badge** | ✅ Strong | Referer shows different repo; verification detects mismatch |
| **Typosquatting repos** | ✅ Strong | Referer shows typosquatted URL; verification detects |
| **Badge image copying** | ✅ Mitigated | Badge is just a link; real verification happens on click |
| **Manifest forgery** | ✅ Strong | Cryptographic signature verification |

### What Repo Trust Does NOT Protect Against

| Threat | Why | Mitigation |
|--------|-----|------------|
| **Compromised maintainer** | They have legitimate access | Limit secret access; monitor commits |
| **Stolen signing key** | Valid signatures can be produced | Rotate keys; use hardware keys |
| **Malicious code in official commits** | Repo Trust verifies origin, not safety | Code review; security scanning |
| **Users who don't click verify** | Requires user action | Education; prominent badge placement |
| **Referer stripped by privacy settings** | Browser may not send Referer | Manual verification guidance shown |

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER-CONTROLLED                        │
│                    (Cannot be faked by attacker)             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Referer Header                           │   │
│  │  Contains full URL including /tree/<commit_hash>      │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERIFICATION PAGE                         │
│                    (On owner's GitHub Pages)                 │
│                                                              │
│  1. Extract commit hash from Referer                         │
│  2. Call GitHub API to check commit ancestry                 │
│  3. If commit not in default branch → WARNING                │
│  4. If commit in default branch → VERIFIED                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB API                                │
│                    (Source of truth for commit history)      │
│                                                              │
│  GET /repos/{owner}/{repo}/compare/{commit}...{default}      │
│  → Returns whether commit is ancestor of default branch      │
└─────────────────────────────────────────────────────────────┘
```

**Attack Scenario Analysis:**

```
Attacker: Creates fork → Modifies README → Commits as abc123
                              ↓
User visits: github.com/official/repo/tree/abc123
                              ↓
User clicks: "Repo Trust - Click to Verify" badge
                              ↓
Browser sends: Referer: https://github.com/official/repo/tree/abc123
                              ↓
Verification page extracts: commit hash = abc123
                              ↓
API call: GET /compare/abc123...main
                              ↓
Result: commit abc123 NOT in main branch ancestry
                              ↓
Display: ⚠️ WARNING - Possible Repo Squatting Detected
```

---

## Security Design Decisions

### Why SSH Signing (Not GPG)?

- Simpler key management
- Native GitHub support
- Easier secret storage (single file)
- Ed25519 is modern and secure

### Why GitHub Pages (Not External Service)?

- No additional trust dependencies
- Namespace bound to repository owner
- No API keys or accounts needed
- Survives if external services go down

### Why Embedded Repo Name in Badge?

- Prevents copying a "generic" verified badge
- Users can visually verify badge matches page
- Similar to how TLS certificates contain domain names

---

## Key Compromise Response

If you believe your signing key has been compromised:

### Immediate Actions

1. **Delete the `REPO_TRUST_SIGNING_KEY` secret** immediately
2. **Revoke/rotate any related credentials**
3. **Notify your users** via GitHub Security Advisory

### Recovery Steps

1. Generate a new signing key pair
2. Update `public_key.pub` in your repository
3. Add the new private key as a secret
4. Publish a new release to update the badge
5. Consider publishing a security advisory listing affected versions

### User Guidance

Tell your users:
- Which release versions may be affected
- How to verify they have a legitimate release
- Where to download verified releases

---

## Security Best Practices for Adopters

### Repository Settings

- [ ] Enable branch protection on `main`
- [ ] Require PR reviews for workflow changes
- [ ] Limit who can access repository secrets
- [ ] Enable GitHub audit logging

### Key Management

- [ ] Use Ed25519 keys (not RSA)
- [ ] Never commit private keys
- [ ] Rotate keys annually
- [ ] Consider using GitHub Environments with required reviewers

### Monitoring

- [ ] Watch for unexpected releases
- [ ] Monitor Actions workflow runs
- [ ] Set up alerts for secret access
- [ ] Review audit logs periodically

---

## Known Limitations

1. **Single key**: Currently supports one signing key per repository
2. **No revocation list**: Compromised keys require manual user notification
3. **No timestamp authority**: Signatures don't prove *when* signing occurred
4. **Badge caching**: GitHub/CDN may cache old badge states briefly

---

## Future Security Enhancements (Phase 2)

- [ ] Sigstore integration for keyless signing
- [ ] Rekor transparency log for audit trail
- [ ] Timestamping via RFC 3161
- [ ] Multi-signature support
- [ ] Automated key rotation

---

## Contact

For security issues, please use GitHub's private vulnerability reporting or contact the maintainers directly.
