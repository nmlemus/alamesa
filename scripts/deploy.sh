#!/usr/bin/env bash
# Usage: deploy.sh <environment> <image>
# Deploys the given Docker image to the target environment.
# Set DEPLOY_SSH_HOST, DEPLOY_SSH_USER, and DEPLOY_SSH_KEY_FILE in the
# calling environment, or replace this script with your deployment tool.
set -euo pipefail

ENVIRONMENT="${1:?environment required}"
IMAGE="${2:?image required}"

echo "Deploying $IMAGE to $ENVIRONMENT"

SSH_HOST="${DEPLOY_SSH_HOST:?DEPLOY_SSH_HOST not set}"
SSH_USER="${DEPLOY_SSH_USER:?DEPLOY_SSH_USER not set}"
SSH_KEY="${DEPLOY_SSH_KEY_FILE:?DEPLOY_SSH_KEY_FILE not set}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${SSH_HOST}" \
  "docker pull ${IMAGE} && docker stop mesadigital-${ENVIRONMENT} || true && \
   docker run -d --rm --name mesadigital-${ENVIRONMENT} -p 8000:8000 ${IMAGE}"

echo "Deployment to $ENVIRONMENT complete."
