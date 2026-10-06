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
REPO="MrMorningw/STACY--UPDATES"
AUTH="Authorization: Bearer $STACY_UPDATES_TOKEN"
ACCEPT="Accept: application/vnd.github+json"
VERSION="X-GitHub-Api-Version: 2026-03-10"

curl -fsS -H "$ACCEPT" -H "$AUTH" -H "$VERSION" "$API/repos/$REPO" >/dev/null

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
{"versionCode":$VC,"versionName":"$VN","packageName":"com.mrmorning.stacy","minAndroid":26,"sha256":"$SHA","signingCertificateSha256":"$CERT","assets":[{"name":"STACY-$VN.apk","version_code":$VC,"digest":"sha256:$SHA","browser_download_url":"https://raw.githubusercontent.com/MrMorningw/STACY--UPDATES/main/releases/STACY-$VN.apk"}]}
EOF

put_file "$RUNNER_TEMP/update.json" "update.json" "release: STACY update metadata"

# GitHub Contents API is authoritative immediately after publication; raw.githubusercontent.com may lag briefly.
curl -fsS -H "$ACCEPT" -H "$AUTH" -H "$VERSION" "$API/repos/$REPO/contents/update.json?ref=main" > "$RUNNER_TEMP/published-update-api.json"
python3 - "$RUNNER_TEMP/published-update-api.json" "$VN" "$VC" "$SHA" <<'PY'
import base64,json,sys
p=json.load(open(sys.argv[1]))
assert p.get("encoding")=="base64"
open(sys.argv[1]+".decoded","wb").write(base64.b64decode(p["content"]))
PY
for i in $(seq 1 12); do
  if curl -fsS "https://raw.githubusercontent.com/MrMorningw/STACY--UPDATES/main/update.json" > "$RUNNER_TEMP/published-update.json"; then
    break
  fi
  sleep 5
done
test -s "$RUNNER_TEMP/published-update.json"
python3 - "$RUNNER_TEMP/published-update.json" "$VN" "$VC" "$SHA" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p["versionName"]==sys.argv[2]
assert str(p["versionCode"])==sys.argv[3]
assert p["sha256"]==sys.argv[4]
assert p["packageName"]=="com.mrmorning.stacy"
assert p["assets"][0]["browser_download_url"].endswith(".apk")
print("Published update.json validated:", p["versionName"], p["versionCode"])
PY
