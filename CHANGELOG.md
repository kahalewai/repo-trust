# Changelog

All notable changes to Repo Trust will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Sigstore/OIDC keyless signing (Phase 2)
- Transparency log integration
- Multi-forge support (GitLab, Bitbucket)

---

## [1.0.0] - 2025-XX-XX

### Added
- Initial release of Repo Trust
- SSH-based cryptographic signing of release manifests
- Automatic manifest generation on GitHub Release publish
- Signature verification with repository identity binding
- SVG badge generation with embedded repository name (anti-impersonation)
- GitHub Pages publishing with non-destructive updates
- Support for existing GitHub Pages content (coexistence)
- Production-grade error handling and logging
- GitHub Actions annotations for errors and warnings
- Retry logic for transient GitHub API failures
- Rate limiting awareness
- Detailed error messages with actionable hints
- GitHub Enterprise Server support
- Graceful handling of:
  - Releases with zero assets
  - Missing GitHub Pages
  - Branch protection conflicts
  - Rate limit exhaustion

### Security
- Signing key stored as GitHub Secret (fork-inaccessible)
- Badge includes repository name to prevent impersonation
- Manifest binds artifacts to repository identity
- Public key committed to repository for verification

### Documentation
- Comprehensive README with quick start guide
- Detailed implementation guide
- Security policy and threat model
- FAQ section
- Contributing guidelines

---

## Version History

### Versioning Policy

- **Major (X.0.0)**: Breaking changes to manifest format or API
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates

### Compatibility

| Version | Manifest Format | GitHub Actions | Status |
|---------|-----------------|----------------|--------|
| 1.x     | 1.0             | v4 compatible  | Current |

---

## Upgrade Guide

### Upgrading to 1.x

If upgrading from a pre-release version:

1. No manifest format changes - existing manifests remain valid
2. Update your workflow to use `repo-trust/action@v1`
3. Regenerate badge by publishing a new release

---

[Unreleased]: https://github.com/repo-trust/action/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/repo-trust/action/releases/tag/v1.0.0
