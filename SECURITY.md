# Security Model

## What Repo Trust Protects Against

Repo Trust mitigates repo squatting, an attack where a malicious fork commit appears under the official repository's URL on GitHub, tricking users into downloading malware.

### Trust Anchor

The security of Repo Trust rests on a single property:

> Attackers cannot deploy content to `your-org.github.io`.

GitHub Pages serves content from the `gh-pages` branch of your repository. Only users with write access to your repository can push to this branch. Forking a repository does not grant write access to the original.

By serving downloads from GitHub Pages rather than from README links (which attackers can modify in fork commits), Repo Trust moves the download experience to a domain the attacker cannot control.

### Referer-Based Detection (Secondary Layer)

When a user clicks through to the verified download page, the browser sends a `Referer` header. If the referring URL contains a commit hash, Repo Trust checks whether that commit exists in the official branch history via the GitHub API.

Important caveats about the Referer check:

- GitHub currently sends `referrer-policy: no-referrer-when-downgrade`, which preserves the full URL cross-origin. If GitHub changes this to `strict-origin-when-cross-origin` (the modern default), the Referer will only contain the origin, and commit hash extraction will stop working.
- Browser extensions and privacy settings can strip or modify the Referer header.
- The Referer check is a bonus layer, not the primary defense. The download page works without it.

## What Repo Trust Does NOT Protect Against

- Users who don't click the badge. If a user arrives at a repo squatting page and downloads directly from the modified README without clicking the Repo Trust badge, the verification system is never engaged.
- First-time visitors. Users who have never seen the official repository won't know to expect a Repo Trust badge.
- Compromised maintainer accounts. If an attacker gains write access to the real repository, they can modify the gh-pages branch.
- Code-level vulnerabilities. Repo Trust verifies distribution authenticity, not code safety.

## Reporting Vulnerabilities

If you discover a security vulnerability in Repo Trust itself, please report it responsibly by emailing the maintainers rather than opening a public issue.
