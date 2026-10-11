#!/usr/bin/env bash
set -euo pipefail

if [ "${GITHUB_REF:-}" != "refs/heads/main" ]; then
  echo "STACY update channel skipped outside main."
  exit 0
fi

: "${STACY_KEYSTORE_BASE64:?Missing STACY_KEYSTORE_BASE64 secret}"
: "${STACY_KEYSTORE_PASSWORD:?Missing STACY_KEYSTORE_PASSWORD secret}"
: "${STACY_KEY_ALIAS:?Missing STACY_KEY_ALIAS secret}"
: "${STACY_KEY_PASSWORD:?Missing STACY_KEY_PASSWORD secret}"
: "${STACY_UPDATES_TOKEN:?Missing STACY_UPDATES_TOKEN secret}"

KEYSTORE_PATH="${RUNNER_TEMP}/stacy-release.jks"
export STACY_KEYSTORE_PATH="$KEYSTORE_PATH"
echo "$STACY_KEYSTORE_BASE64" | base64 --decode > "$KEYSTORE_PATH"
test -s "$KEYSTORE_PATH"

gradle assembleRelease

APK="app/build/outputs/apk/release/app-release.apk"
test -f "$APK"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
APKSIGNER="$(find "$SDK_ROOT/build-tools" -type f -name apksigner -perm -111 | sort -V | tail -1)"
AAPT="$(find "$SDK_ROOT/build-tools" -type f -name aapt -perm -111 | sort -V | tail -1)"
test -n "$APKSIGNER"
test -n "$AAPT"

"$APKSIGNER" verify --verbose "$APK"
BADGING="$("$AAPT" dump badging "$APK")"
# Parse aapt output with Python rather than fragile nested shell/sed escaping.
mapfile -t META < <(printf '%s\n' "$BADGING" | python3 -c '
import re, sys
s = sys.stdin.read()
patterns = [
    r"versionCode=\x27([^\x27]+)\x27",
    r"versionName=\x27([^\x27]+)\x27",
    r"package: name=\x27([^\x27]+)\x27",
]
for pattern in patterns:
    m = re.search(pattern, s)
    print(m.group(1) if m else "")
')
VC="${META[0]:-}"
VN="${META[1]:-}"
PKG="${META[2]:-}"
SHA="$(sha256sum "$APK" | awk '{print $1}')"
CERT="$("$APKSIGNER" verify --print-certs "$APK" | sed -n 's/.*certificate SHA-256 digest: //p' | head -1 | tr -d ':')"

if [ "$PKG" != "com.mrmorning.stacy" ]; then
  echo "Unexpected APK package name: '${PKG:-empty}' (expected com.mrmorning.stacy)"
  exit 1
fi
if [ -z "$VC" ] || [ -z "$VN" ] || [ -z "$SHA" ] || [ -z "$CERT" ]; then
  echo "Could not extract release metadata from the APK."
  echo "versionCode='${VC:-}', versionName='${VN:-}', sha256_present=$([[ -n "$SHA" ]] && echo yes || echo no), certificate_present=$([[ -n "$CERT" ]] && echo yes || echo no)"
  exit 1
fi

API="https://api.github.com"
REPO="MrMorningw/STACY--UPDATES-DEFINITIVO"
AUTH="Authorization: Bearer $STACY_UPDATES_TOKEN"
ACCEPT="Accept: application/vnd.github+json"
VERSION="X-GitHub-Api-Version: 2022-11-28"

put_file() {
  local local_file="$1"
  local remote_path="$2"
  local message="$3"
  local sha=""
  local payload="$RUNNER_TEMP/payload.json"
  local response="$RUNNER_TEMP/github-response.json"

  sha="$(curl -sS -H "$ACCEPT" -H "$AUTH" -H "$VERSION" "$API/repos/$REPO/contents/$remote_path" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("sha",""))' 2>/dev/null || true)"
  export PUT_LOCAL_FILE="$local_file" PUT_MESSAGE="$message" PUT_SHA="$sha"

  python3 > "$payload" <<'PY'
import base64,json,os
with open(os.environ["PUT_LOCAL_FILE"],"rb") as f:
    content=base64.b64encode(f.read()).decode()
p={"message":os.environ["PUT_MESSAGE"],"content":content,"branch":"main"}
if os.environ.get("PUT_SHA"):
    p["sha"]=os.environ["PUT_SHA"]
print(json.dumps(p))
PY

  local status
  status="$(curl -sS -o "$response" -w '%{http_code}' -X PUT -H "$ACCEPT" -H "$AUTH" -H "$VERSION" --data-binary "@$payload" "$API/repos/$REPO/contents/$remote_path")"
  if [[ "$status" != "200" && "$status" != "201" ]]; then
    echo "GitHub Contents API failed for $remote_path (HTTP $status):"
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("message",d))' "$response" 2>/dev/null || cat "$response"
    echo "Check repository $REPO, token access (Contents: Read and write), and the main branch."
    return 1
  fi
  echo "Published $remote_path (HTTP $status)."
}

put_file "$APK" "releases/STACY-$VN.apk" "release: STACY $VN APK"

cat > "$RUNNER_TEMP/update.json" <<EOF
{"versionCode":$VC,"versionName":"$VN","packageName":"com.mrmorning.stacy","minAndroid":26,"sha256":"$SHA","signingCertificateSha256":"$CERT","assets":[{"name":"STACY-$VN.apk","version_code":$VC,"digest":"sha256:$SHA","browser_download_url":"https://raw.githubusercontent.com/MrMorningw/STACY--UPDATES-DEFINITIVO/main/releases/STACY-$VN.apk"}]}
EOF

put_file "$RUNNER_TEMP/update.json" "update.json" "release: STACY update metadata"

echo "STACY update channel published: version $VN (code $VC), SHA-256 $SHA"
