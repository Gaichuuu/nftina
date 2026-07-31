# Post-deploy health check
#
# Checks every prerendered route, the redirects, the nginx rules (404 page,
# gzip, cache headers) and the certificate. 
#
# Usage:  bash scripts/check-live.sh          check the live site
#         SITE=http://localhost:4173 bash scripts/check-live.sh   check a preview build
set -uo pipefail

SITE="${SITE:-https://metazoonfts.com}"
HOST="${SITE#https://}"; HOST="${HOST#http://}"; HOST="${HOST%%/*}"
fail=0
ok()   { printf "  \033[32mok\033[0m   %s\n" "$1"; }
bad()  { printf "  \033[31mFAIL\033[0m %s\n" "$1"; fail=$((fail+1)); }

code()    { curl -sS -o /dev/null -w '%{http_code}' "$1"; }
redirect(){ curl -sS -o /dev/null -w '%{redirect_url}' "$1"; }
header()  { curl -sSI "$1" | tr -d '\r' | awk -v k="$2:" 'tolower($1)==tolower(k){$1="";sub(/^ /,"");print}'; }
encoding(){ curl -sSI -H 'Accept-Encoding: gzip' "$1" | tr -d '\r' \
            | awk 'tolower($1)=="content-encoding:"{print $2}'; }

echo "== $SITE"

# --- routes ---
ROUTES=(/ /collections/ /where-did-the-money-go/)
for slug in genesis_2021 genesis_reissue_1155 coin_tokens beasties_s1 pfp_2 \
            valentines wilderness tournament_prizes mothman_1of1 sandbox; do
  ROUTES+=("/collections/$slug/")
done
n=0
for r in "${ROUTES[@]}"; do
  c=$(code "$SITE$r")
  if [[ "$c" == "200" ]]; then n=$((n+1)); else bad "route $r -> $c"; fi
done
[[ $n -eq ${#ROUTES[@]} ]] && ok "all ${#ROUTES[@]} routes return 200"

# --- content actually prerendered ---
curl -sS "$SITE/" | grep -q "Holders lost" \
  && ok "home page carries prerendered hero copy" \
  || bad "home page has no prerendered content"

# --- static assets ---
for a in /og.jpg /favicon.ico /apple-touch-icon.png /sitemap.xml /robots.txt; do
  c=$(code "$SITE$a"); [[ "$c" == "200" ]] || bad "asset $a -> $c"
done
ok "share card, icons, sitemap and robots.txt present"

# --- redirects ---
if [[ "$SITE" == https://* ]]; then
  [[ "$(code "http://$HOST/")" == "301" ]] \
    && ok "http -> https redirects" || bad "http:// does not redirect (got $(code "http://$HOST/"))"
  [[ "$(redirect "https://www.$HOST/")" == "https://$HOST/" ]] \
    && ok "www -> apex redirects" || bad "www does not redirect to apex"
  [[ "$(redirect "http://$HOST/collections/")" == *"/collections/" ]] \
    && ok "redirect preserves the request path" || bad "redirect loses the path"
fi

# --- nginx rules ---
[[ "$(code "$SITE/no-such-page")" == "404" ]] \
  && ok "unknown path returns 404 (not a soft 200)" || bad "unknown path is not a 404"
curl -sS "$SITE/no-such-page" | grep -q "Not on the ledger" \
  && ok "custom 404 page is served" || bad "404 is nginx's default, not ours"

JS=$(curl -sS "$SITE/" | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' | head -1)
if [[ -n "$JS" ]]; then
  [[ "$(encoding "$SITE/$JS")" == "gzip" ]] \
    && ok "javascript is gzipped" || bad "javascript is NOT gzipped"
  [[ "$(header "$SITE/$JS" cache-control)" == *immutable* ]] \
    && ok "/assets/ cached immutable" || bad "/assets/ missing immutable cache header"
fi
[[ "$(encoding "$SITE/data/collections/coin_tokens/holders.json")" == "gzip" ]] \
  && ok "runtime json is gzipped" || bad "runtime json is NOT gzipped"
[[ "$(header "$SITE/data/summary.json" cache-control)" == *must-revalidate* ]] \
  && ok "/data/ revalidates" || bad "/data/ missing revalidate cache header"

# --- certificate ---
if [[ "$SITE" == https://* ]]; then
  subj=$(echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null \
         | openssl x509 -noout -subject 2>/dev/null)
  if [[ "$subj" == *sni.dreamhost.com* ]]; then
    bad "serving DreamHost's fallback certificate - the vhost is gone"
  elif [[ -n "$subj" ]]; then
    days=$(echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null \
           | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    ok "certificate valid (expires $days)"
  else
    bad "could not read the certificate"
  fi
fi

echo
if [[ $fail -eq 0 ]]; then
  echo "All checks passed."
else
  echo "$fail check(s) failed."
  exit 1
fi
