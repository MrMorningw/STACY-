#!/usr/bin/env bash
# Run Android instrumentation from the Android Gradle root and always print reports.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/android"

gradle connectedDebugAndroidTest --stacktrace
test_status=$?

echo "===== ANDROID INSTRUMENTATION XML REPORTS ====="
if [ -d app/build/outputs/androidTest-results/connected ]; then
  find app/build/outputs/androidTest-results/connected -type f -name '*.xml' -print -exec cat {} \; || true
else
  echo "No XML test report directory was created."
fi

echo "===== ANDROID INSTRUMENTATION HTML REPORT ====="
if [ -f app/build/reports/androidTests/connected/debug/index.html ]; then
  echo "HTML report: app/build/reports/androidTests/connected/debug/index.html"
else
  echo "No HTML report was created."
fi

echo "===== END ANDROID INSTRUMENTATION REPORTS ====="
exit "$test_status"
