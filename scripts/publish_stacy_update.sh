#!/usr/bin/env bash
set -euo pipefail

if [ "${GITHUB_REF:-}" != "refs/heads/main" ]; then
  echo "STACY update channel skipped outside main."
  exit 0
fi

test -n "${STACY_KEYSTORE_BASE64:-}"
test -n "${STACY_UPDATES_TOKEN:-}"

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
VC="$(printf '%s\n' "$BADGING" | sed -n "s/.*versionCode='\\([^']*\\)'.*/\\1/p")"
VN="$(printf '%s\n' "$BADGING" | sed -n "s/.*versionName='\\([^']*\\)'.*/\\1/p")"
PKG="$(printf '%s\n' "$BADGING" | sed -n "s/package: name='\\([^']*\\)'.*/\\1/p")"
SHA="$(sha256sum "$APK" | awk '{print $1}')"
CERT="$("$APKSIGNER" verify --print-certs "$APK" | sed -n 's/.*certificate SHA-256 digest: //p' | head -1 | tr -d ':')"

test "$PKG" = "com.mrmorning.stacy"
test -n "$VC" -a -n "$VN" -a -n "$SHA" -a -n "$CERT"

API="https://api.github.com"
REPO="MrMorningw/STACY--UPDATES-DEFINITIVO"
AUTH="Authorization: Bearer $STACY_UPDATES_TOKEN"
ACCEPT="Accept: application/vnd.github+json"
VERSION="X-GitHub-Api-Version: 2026-03-10"

put_file() {
  local local_file="$1"
  local remote_path="$2"
  local message="$3"
  local sha=""
  local payload="$RUNNER_TEMP/payload.json"

  sha="$(curl -fsS -H "$ACCEPT" -H "$AUTH" -H "$VERSION" "$API/repos/$REPO/contents/$remote_path" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("sha",""))' || true)"
  export PUT_LOCAL_FILE="$local_file" PUT_VERSION="$VN" PUT_MESSAGE="$message" PUT_SHA="$sha" PUT_REMOTE_PATH="$remote_path"

  python3 > "$payload" <<'PY'
import base64,json,os
with open(os.environ["PUT_LOCAL_FILE"],"rb") as f:
    content=base64.b64encode(f.read()).decode()
p={"message":os.environ["PUT_MESSAGE"],"content":content,"branch":"main"}
if os.environ.get("PUT_SHA"):
    p["sha"]=os.environ["PUT_SHA"]
print(json.dumps(p))
PY

  curl -fsS -X PUT -H "$ACCEPT" -H "$AUTH" -H "$VERSION" --data-binary "@$payload" "$API/repos/$REPO/contents/$remote_path" >/dev/null
}

put_file "$APK" "releases/STACY-$VN.apk" "release: STACY $VN APK"

cat > "$RUNNER_TEMP/update.json" <<EOF
{"versionCode":$VC,"versionName":"$VN","packageName":"com.mrmorning.stacy","minAndroid":26,"sha256":"$SHA","signingCertificateSha256":"$CERT","assets":[{"name":"STACY-$VN.apk","version_code":$VC,"digest":"sha256:$SHA","browser_download_url":"https://raw.githubusercontent.com/MrMorningw/STACY--UPDATES-DEFINITIVO/main/releases/STACY-$VN.apk"}]}
EOF

put_file "$RUNNER_TEMP/update.json" "update.json" "release: STACY update metadata"

# The authenticated Contents API is the publication authority. The public raw URL is consumed by the Android updater after propagation.\n