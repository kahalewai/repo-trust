#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "[repo-trust] Starting Repo Trust v2.0.0"
echo "=============================================="

# Validate required environment variables
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "[repo-trust] ERROR: GITHUB_TOKEN is required"
    exit 1
fi

if [ -z "${GITHUB_REPOSITORY:-}" ]; then
    echo "[repo-trust] ERROR: GITHUB_REPOSITORY is required"
    exit 1
fi

# Set up GitHub API URL (supports GitHub Enterprise Server)
export GITHUB_API_URL="${GITHUB_API_URL:-https://api.github.com}"
export GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"

echo "[repo-trust] Repository: ${GITHUB_REPOSITORY}"
echo "[repo-trust] API URL: ${GITHUB_API_URL}"

# Create working directory
WORK_DIR="/tmp/repo-trust-work"
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

echo ""
echo "[repo-trust] Step 1/2: Fetching release data..."
python -m repo_trust.releases

echo ""
echo "[repo-trust] Step 2/2: Publishing verified download page..."
python -m repo_trust.pages

echo ""
echo "=============================================="
echo "[repo-trust] Completed successfully!"
echo "=============================================="
echo ""
echo "Verified download page: https://${GITHUB_REPOSITORY%%/*}.github.io/${GITHUB_REPOSITORY##*/}/repo-trust/"
echo "Badge URL: https://${GITHUB_REPOSITORY%%/*}.github.io/${GITHUB_REPOSITORY##*/}/repo-trust/badge.svg"
echo ""
