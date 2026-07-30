#!/usr/bin/env bash
#
# Run `deploy.sh` to build the site and rsync it to the server root.
#
# Credentials in .deploy.env (gitignored):
#   DEPLOY_USER, DEPLOY_HOST
#   DEPLOY_PATH
#
# Usage:  bash scripts/deploy.sh              build + deploy (site + nginx config)
#         DRY_RUN=1 bash scripts/deploy.sh    show what would transfer, send nothing
#         SKIP_NGINX=1 bash scripts/deploy.sh site only, leave ~/nginx untouched
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/.deploy.env"
WEB="$ROOT/web"

[[ -f "$ENV_FILE" ]] || { echo "error: $ENV_FILE not found (needs DEPLOY_USER/HOST/PATH)" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a

: "${DEPLOY_USER:?set DEPLOY_USER in .deploy.env}"
: "${DEPLOY_HOST:?set DEPLOY_HOST in .deploy.env}"
: "${DEPLOY_PATH:?set DEPLOY_PATH in .deploy.env (web root, e.g. ~/metazoonfts.com/)}"

REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"

[[ -f "$ROOT/site/data/summary.json" ]] || {
  echo "error: site/data/summary.json missing - run 'python -m scripts.build_site_data' first" >&2; exit 1; }

echo "==> Building (data copy + typecheck + client + ssr + prerender)..."
(cd "$WEB" && npm run build)

grep -q "Holders lost" "$WEB/dist/index.html" || {
  echo "error: dist/index.html has no prerendered hero copy - prerender did not run" >&2; exit 1; }

NGINX_CONF="$ROOT/nginx/metazoonfts.com/nginx.conf"
[[ -f "$NGINX_CONF" ]] || {
  echo "error: $NGINX_CONF missing - the live host is nginx, so this is the real config" >&2; exit 1; }

if [[ -n "${DRY_RUN:-}" ]]; then
  echo "==> DRY RUN: would deploy dist/ -> ${REMOTE}"
  rsync -avzn --delete --exclude=".DS_Store" "$WEB/dist/" "$REMOTE"
  echo "==> DRY RUN: would deploy $(basename "$NGINX_CONF") ($(wc -l <"$NGINX_CONF" | tr -d ' ') lines)" \
       "-> ${DEPLOY_USER}@${DEPLOY_HOST}:~/nginx/metazoonfts.com/nginx.conf"
  exit 0
fi

echo "==> Deploying dist/ -> ${REMOTE}"
rsync -avz --delete --exclude=".DS_Store" "$WEB/dist/" "$REMOTE"

if [[ -n "${SKIP_NGINX:-}" ]]; then
  echo "==> SKIP_NGINX set: leaving ~/nginx/metazoonfts.com alone"
else
  echo "==> Deploying nginx config -> ~/nginx/metazoonfts.com/"
  ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "mkdir -p ~/nginx/metazoonfts.com"
  rsync -avz "$NGINX_CONF" "${DEPLOY_USER}@${DEPLOY_HOST}:~/nginx/metazoonfts.com/nginx.conf"
fi

echo "==> Done. https://metazoonfts.com/"
