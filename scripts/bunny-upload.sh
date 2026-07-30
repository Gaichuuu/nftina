#!/usr/bin/env bash
#
# bunny-upload.sh — push Nftina token/acquisition art to the Bunny CDN storage
# zone that serves https://gaichu.b-cdn.net
#
#   local:  data/media/tokens/coin_tokens/1.png
#   remote: <zone>/nftina/tokens/coin_tokens/1.png
#   url:    https://gaichu.b-cdn.net/nftina/tokens/coin_tokens/1.png
#
# Usage:
#   scripts/bunny-upload.sh media
#         sync data/media/tokens/<slug>/ -> nftina/tokens/<slug>/
#         and  data/media/acquisitions/  -> nftina/acquisitions/
#         and  data/media/collections/   -> nftina/collections/
#         and  data/media/sandbox3d/     -> nftina/sandbox3d/
#         and  data/media/overview/      -> nftina/overview/
#   scripts/bunny-upload.sh audit                               # read-only: diff
#         local data/media trees vs the CDN's nftina/ prefix (orphans, missing)
#   scripts/bunny-upload.sh list   <remote-dir>                 # list a CDN dir
#   scripts/bunny-upload.sh upload <local-file> <remote-path>   # one file
#   scripts/bunny-upload.sh sync   <local-dir>  <remote-dir>    # a dir (flat)
#   scripts/bunny-upload.sh delete <remote-path>                # one file/dir
#
# sync/media SKIP files already on the CDN with a matching basename+size (one
# listing request per dir)
#
# Same-size in-place content changes are not detected; set FORCE_UPLOAD=1 to
# re-PUT everything.
#
# Set DRY_RUN=1 to print what would happen without calling Bunny.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.deploy.env"

REMOTE_PREFIX="${REMOTE_PREFIX:-nftina}"
DRY_RUN="${DRY_RUN:-0}"

if [[ "$DRY_RUN" != "1" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "error: $ENV_FILE not found (needs BUNNY_STORAGE_* vars). Use DRY_RUN=1 to test without it." >&2
    exit 1
  fi
  set -a; source "$ENV_FILE"; set +a
  : "${BUNNY_STORAGE_ZONE:?missing BUNNY_STORAGE_ZONE in .deploy.env}"
  : "${BUNNY_STORAGE_KEY:?missing BUNNY_STORAGE_KEY in .deploy.env}"
fi

BUNNY_STORAGE_HOST="${BUNNY_STORAGE_HOST:-storage.bunnycdn.com}"
BASE="https://${BUNNY_STORAGE_HOST}/${BUNNY_STORAGE_ZONE:-ZONE}"

clean() { echo "${1#/}" | sed 's:/*$::'; }

content_type() {
  case "$1" in
    *.pdf)         echo "application/pdf" ;;
    *.jpg|*.jpeg)  echo "image/jpeg" ;;
    *.png)         echo "image/png" ;;
    *.gif)         echo "image/gif" ;;
    *.webp)        echo "image/webp" ;;
    *.avif)        echo "image/avif" ;;
    *.svg)         echo "image/svg+xml" ;;
    *.mp4)         echo "video/mp4" ;;
    *.mov)         echo "video/quicktime" ;;
    *.webm)        echo "video/webm" ;;
    *.m4a)         echo "audio/mp4" ;;
    *.mp3)         echo "audio/mpeg" ;;
    *)             echo "application/octet-stream" ;;
  esac
}

do_list() {
  local remote; remote="$(clean "${1:?usage: list <remote-dir>}")"
  curl -fsS --max-time 60 -H "AccessKey: ${BUNNY_STORAGE_KEY}" -H 'Accept: application/json' \
    "${BASE}/${remote}/" \
    | tr ',' '\n' | grep -E '"(ObjectName|Length|IsDirectory)"' || true
}

do_upload() {
  local file="${1:?usage: upload <local-file> <remote-path>}"
  local remote; remote="$(clean "${2:?usage: upload <local-file> <remote-path>}")"
  [[ -f "$file" ]] || { echo "error: local file not found: $file" >&2; return 1; }
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY ↑ $file -> ${BUNNY_CDN_HOST:-CDN}/${remote}"
    return 0
  fi
  echo "↑ $file -> ${BUNNY_CDN_HOST:-CDN}/${remote}"
  local attempt=0 max=4
  while :; do
    attempt=$((attempt + 1))
    if curl -fsS --max-time 300 -H "AccessKey: ${BUNNY_STORAGE_KEY}" \
        -H "Content-Type: $(content_type "$file")" \
        --data-binary "@${file}" -X PUT "${BASE}/${remote}" >/dev/null 2>&1; then
      echo "  ✓ uploaded"
      return 0
    fi
    if [[ "$attempt" -ge "$max" ]]; then
      echo "  ✗ failed after ${attempt} attempts" >&2
      return 1
    fi
    sleep "$attempt"
  done
}

do_sync() {
  local dir="${1:?usage: sync <local-dir> <remote-dir>}"
  local remote; remote="$(clean "${2:?usage: sync <local-dir> <remote-dir>}")"
  [[ -d "$dir" ]] || { echo "error: local dir not found: $dir" >&2; exit 1; }
  local total; total=$(find "$dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
  [[ "$total" -eq 0 ]] && { echo "Synced 0 file(s) (0 skipped, 0 failed) to ${BUNNY_CDN_HOST:-CDN}/${remote}/"; return 0; }

  if [[ "$DRY_RUN" == "1" ]]; then
    find "$dir" -maxdepth 1 -type f -print0 | while IFS= read -r -d '' f; do
      echo "DRY ↑ $f -> ${BUNNY_CDN_HOST:-CDN}/${remote}/$(basename "$f")"
    done
    echo "Synced $total file(s) (0 skipped, 0 failed) to ${BUNNY_CDN_HOST:-CDN}/${remote}/"
    return 0
  fi

  local index_file pending_list
  index_file=$(mktemp) ; pending_list=$(mktemp)
  if [[ "${FORCE_UPLOAD:-0}" != "1" ]]; then
    local raw_listing http_code
    raw_listing=$(mktemp)
    http_code=$(curl -sS --max-time 120 -H "AccessKey: ${BUNNY_STORAGE_KEY}" \
      -H 'Accept: application/json' -o "$raw_listing" -w "%{http_code}" \
      "${BASE}/${remote}/" 2>/dev/null || echo 000)
    if [[ "$http_code" == "200" ]]; then
      if ! python3 -c '
import json, sys
with open(sys.argv[1]) as fh:
    objs = json.load(fh)
for o in objs:
    if not o.get("IsDirectory"):
        print(o.get("ObjectName"), o.get("Length"), sep="\t")' "$raw_listing" > "$index_file"; then
        echo "error: could not parse CDN listing for ${remote}/ — refusing to blind re-upload (retry, or FORCE_UPLOAD=1)" >&2
        rm -f "$raw_listing" "$index_file" "$pending_list"
        return 1
      fi
    elif [[ "$http_code" != "404" ]]; then
      echo "error: CDN listing for ${remote}/ failed (HTTP ${http_code}) — refusing to blind re-upload (retry, or FORCE_UPLOAD=1)" >&2
      rm -f "$raw_listing" "$index_file" "$pending_list"
      return 1
    fi
    rm -f "$raw_listing"
  fi
  find "$dir" -maxdepth 1 -type f -print0 \
    | python3 -c '
import os, sys
index = {}
with open(sys.argv[1]) as fh:
    for line in fh:
        name, _, size = line.rstrip("\n").partition("\t")
        if name:
            index[name] = size
out = sys.stdout.buffer
for p in sys.stdin.buffer.read().split(b"\0"):
    if not p:
        continue
    path = p.decode()
    if index.get(os.path.basename(path)) == str(os.path.getsize(path)):
        continue                                  # already on CDN, same size
    out.write(p + b"\0")' "$index_file" > "$pending_list"
  local pending
  pending=$(python3 -c 'import sys; print(sum(1 for c in open(sys.argv[1],"rb").read().split(b"\0") if c))' "$pending_list")
  local skipped=$((total - pending))
  rm -f "$index_file"

  if [[ "$pending" -eq 0 ]]; then
    rm -f "$pending_list"
    echo "Synced 0 file(s) ($skipped skipped, 0 failed) to ${BUNNY_CDN_HOST:-CDN}/${remote}/"
    return 0
  fi

  local workers="${UPLOAD_WORKERS:-16}"
  export BASE BUNNY_STORAGE_KEY
  local failed
  failed=$(xargs -0 -P "$workers" -I {} bash -c '
        f="$1"; rem="$2"
        case "$f" in
          *.png) ct=image/png ;; *.jpg|*.jpeg) ct=image/jpeg ;;
          *.gif) ct=image/gif ;; *.webp) ct=image/webp ;;
          *.svg) ct=image/svg+xml ;; *.avif) ct=image/avif ;;
          *) ct=application/octet-stream ;;
        esac
        for a in 1 2 3 4; do
          curl -fsS --max-time 300 -H "AccessKey: $BUNNY_STORAGE_KEY" \
               -H "Content-Type: $ct" --data-binary "@$f" \
               -X PUT "$BASE/$rem/$(basename "$f")" >/dev/null 2>&1 && exit 0
          sleep "$a"
        done
        echo F >&2
      ' _ {} "$remote" < "$pending_list" 2>&1 | /usr/bin/grep -c "^F" || true)
  failed=${failed:-0}
  rm -f "$pending_list"
  echo "Synced $((pending - failed)) file(s) ($skipped skipped, $failed failed) to ${BUNNY_CDN_HOST:-CDN}/${remote}/"
  [[ "$failed" -eq 0 ]]
}

do_media() {
  local root="${1:-$REPO_ROOT/data/media}"
  local rc=0
  [[ -d "$root/tokens" ]] || { echo "note: no $root/tokens (run fetch_token_media)"; }
  if [[ -d "$root/tokens" ]]; then
    for d in "$root"/tokens/*/; do
      [[ -d "$d" ]] || continue
      do_sync "$d" "${REMOTE_PREFIX}/tokens/$(basename "$d")" || rc=1
    done
  fi
  if [[ -d "$root/acquisitions" ]]; then
    do_sync "$root/acquisitions" "${REMOTE_PREFIX}/acquisitions" || rc=1
  fi
  if [[ -d "$root/collections" ]]; then
    do_sync "$root/collections" "${REMOTE_PREFIX}/collections" || rc=1
  fi
  if [[ -d "$root/sandbox3d" ]]; then
    do_sync "$root/sandbox3d" "${REMOTE_PREFIX}/sandbox3d" || rc=1
  fi
  if [[ -d "$root/overview" ]]; then
    do_sync "$root/overview" "${REMOTE_PREFIX}/overview" || rc=1
  fi
  if [[ -d "$root/utility_cdn" ]]; then
    do_sync "$root/utility_cdn" "${REMOTE_PREFIX}/utility" || rc=1
  fi
  if [[ -d "$root/wallets" ]]; then
    do_sync "$root/wallets" "${REMOTE_PREFIX}/wallets" || rc=1
  fi
  [[ "$rc" -eq 0 ]] || echo "note: some files failed to upload — re-run 'bunny-upload.sh media' to retry (idempotent)" >&2
  return "$rc"
}

do_audit() {
  local root="${1:-$REPO_ROOT/data/media}"
  BUNNY_ROOT_URL="$BASE" MEDIA_ROOT="$root" REMOTE_PREFIX="$REMOTE_PREFIX" \
  python3 - <<'PY'
import json, os, sys, urllib.request

BASE   = os.environ["BUNNY_ROOT_URL"]
KEY    = os.environ["BUNNY_STORAGE_KEY"]
ROOT   = os.environ["MEDIA_ROOT"]
PREFIX = os.environ["REMOTE_PREFIX"]

def ls(remote):
    req = urllib.request.Request(f"{BASE}/{remote}/",
                                 headers={"AccessKey": KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024

# Shared-zone top level: name what else lives here, touch nothing.
top = ls("")
others = [o["ObjectName"] for o in top if o.get("IsDirectory") and o["ObjectName"] != PREFIX]
print(f"zone top-level dirs (shared zone): {PREFIX}/ (ours) + {len(others)} other: {', '.join(sorted(others))}")
print()

# Local mirror map: remote dir -> local dir
pairs = [("acquisitions", f"{ROOT}/acquisitions"),
         ("acq_collections", f"{ROOT}/acq_collections"),
         ("collections",  f"{ROOT}/collections"),
         ("sandbox3d",    f"{ROOT}/sandbox3d"),
         ("overview",     f"{ROOT}/overview"),
         ("utility",      f"{ROOT}/utility_cdn"),
         ("wallets",      f"{ROOT}/wallets")]
tokens_local = f"{ROOT}/tokens"
remote_token_dirs = []
unexpected = []
for o in ls(PREFIX):
    name = o["ObjectName"]
    if o.get("IsDirectory"):
        if name == "tokens":
            remote_token_dirs = [t["ObjectName"] for t in ls(f"{PREFIX}/tokens") if t.get("IsDirectory")]
        elif name not in {p[0] for p in pairs}:
            unexpected.append(name)
    else:
        unexpected.append(name + " (loose file)")
for slug in remote_token_dirs:
    pairs.append((f"tokens/{slug}", f"{tokens_local}/{slug}"))
# local token dirs with no remote counterpart (never uploaded)
for slug in sorted(os.listdir(tokens_local)) if os.path.isdir(tokens_local) else []:
    if os.path.isdir(f"{tokens_local}/{slug}") and slug not in remote_token_dirs:
        print(f"local-only (never uploaded): tokens/{slug}")

orphan_total, orphan_count = 0, 0
for remote, local in pairs:
    entries = [o for o in ls(f"{PREFIX}/{remote}") if not o.get("IsDirectory")]
    if not os.path.isdir(local):
        # Local copy intentionally pruned (e.g. pfp_2's ~18 GB) — once uploaded,
        # the CDN is authoritative; these are NOT orphans.
        size = sum(o.get("Length", 0) for o in entries)
        print(f"  cdn-only  {remote}: {len(entries)} file(s), {human(size)} "
              f"(local dir absent — pruned; orphan check skipped)")
        continue
    local_files = {f: os.path.getsize(os.path.join(local, f))
                   for f in os.listdir(local)
                   if os.path.isfile(os.path.join(local, f))}
    orphans  = [(o["ObjectName"], o.get("Length", 0)) for o in entries
                if o["ObjectName"] not in local_files]
    size_mismatch = [o["ObjectName"] for o in entries
                     if o["ObjectName"] in local_files
                     and o.get("Length") != local_files[o["ObjectName"]]]
    missing  = sorted(set(local_files) - {o["ObjectName"] for o in entries})
    status = f"{remote}: {len(entries)} on CDN / {len(local_files)} local"
    if not orphans and not missing and not size_mismatch:
        print(f"  ok  {status}")
    else:
        print(f"  !!  {status}")
        for name, length in sorted(orphans):
            print(f"        orphan on CDN ({human(length)}): {PREFIX}/{remote}/{name}")
            orphan_total += length; orphan_count += 1
        for name in size_mismatch:
            print(f"        size mismatch (CDN != local): {PREFIX}/{remote}/{name}")
        for name in missing:
            print(f"        missing from CDN: {name}")
if unexpected:
    print(f"  !!  unexpected under {PREFIX}/: {', '.join(sorted(unexpected))}")
print()
print(f"deletable orphans under {PREFIX}/: {orphan_count} file(s), {human(orphan_total)}")
PY
}

do_delete() {
  local remote; remote="$(clean "${1:?usage: delete <remote-path>}")"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY ✗ ${BUNNY_CDN_HOST:-CDN}/${remote}"
    return 0
  fi
  if curl -fsS --max-time 120 -H "AccessKey: ${BUNNY_STORAGE_KEY}" \
      -X DELETE "${BASE}/${remote}" >/dev/null 2>&1; then
    echo "✗ deleted ${remote}"
  else
    echo "  · not found / already gone: ${remote}" >&2
  fi
}

cmd="${1:-}"; shift || true
case "$cmd" in
  media)      do_media      "$@" ;;
  audit)      do_audit      "$@" ;;
  list)       do_list       "$@" ;;
  upload)     do_upload     "$@" ;;
  sync)       do_sync       "$@" ;;
  delete)     do_delete     "$@" ;;
  *) sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
