#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "[repo-trust] Starting Repo Trust v1.0.0"
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

if [ -z "${GITHUB_REF_NAME:-}" ]; then
    echo "[repo-trust] ERROR: GITHUB_REF_NAME is required (release tag)"
    exit 1
fi

if [ -z "${REPO_TRUST_SIGNING_KEY:-}" ]; then
    echo "[repo-trust] ERROR: REPO_TRUST_SIGNING_KEY is required"
    exit 1
fi

# Set up GitHub API URL (supports GitHub Enterprise Server)
# For GHES, set GITHUB_API_URL and GITHUB_SERVER_URL in your workflow
export GITHUB_API_URL="${GITHUB_API_URL:-https://api.github.com}"
export GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"

echo "[repo-trust] Repository: ${GITHUB_REPOSITORY}"
echo "[repo-trust] Release tag: ${GITHUB_REF_NAME}"
echo "[repo-trust] API URL: ${GITHUB_API_URL}"

# Write signing key to disk with secure permissions
KEY_PATH="/tmp/repo-trust-signing-key"
echo "${REPO_TRUST_SIGNING_KEY}" > "${KEY_PATH}"
chmod 600 "${KEY_PATH}"
export REPO_TRUST_KEY_PATH="${KEY_PATH}"

# Handle public key - either from input or from repository
PUBLIC_KEY_PATH="/tmp/repo-trust-public-key.pub"
if [ -n "${REPO_TRUST_PUBLIC_KEY:-}" ]; then
    echo "[repo-trust] Using public key from input"
    echo "${REPO_TRUST_PUBLIC_KEY}" > "${PUBLIC_KEY_PATH}"
elif [ -f "${GITHUB_WORKSPACE}/public_key.pub" ]; then
    echo "[repo-trust] Using public key from repository"
    cp "${GITHUB_WORKSPACE}/public_key.pub" "${PUBLIC_KEY_PATH}"
else
    echo "[repo-trust] Deriving public key from signing key"
    ssh-keygen -y -f "${KEY_PATH}" > "${PUBLIC_KEY_PATH}"
fi
chmod 644 "${PUBLIC_KEY_PATH}"
export REPO_TRUST_PUBLIC_KEY_PATH="${PUBLIC_KEY_PATH}"

# Create allowed signers file for verification
ALLOWED_SIGNERS_PATH="/tmp/repo-trust-allowed-signers"
echo "repo-trust $(cat ${PUBLIC_KEY_PATH})" > "${ALLOWED_SIGNERS_PATH}"
export REPO_TRUST_ALLOWED_SIGNERS="${ALLOWED_SIGNERS_PATH}"

# Create working directory
WORK_DIR="/tmp/repo-trust-work"
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

echo ""
echo "[repo-trust] Step 1/4: Generating manifest..."
python -m repo_trust.manifest

echo ""
echo "[repo-trust] Step 2/4: Verifying manifest..."
python -m repo_trust.verify

echo ""
echo "[repo-trust] Step 3/4: Uploading manifest to release..."
python -m repo_trust.upload

echo ""
echo "[repo-trust] Step 4/4: Publishing trust badge..."
python -m repo_trust.pages

echo ""
echo "=============================================="
echo "[repo-trust] Completed successfully!"
echo "=============================================="
echo ""
echo "Badge URL: https://${GITHUB_REPOSITORY%%/*}.github.io/${GITHUB_REPOSITORY##*/}/repo-trust/distribution.svg"
echo ""
