#!/usr/bin/env bash
set -euo pipefail

# Maxwell Accounting - Unsigned iOS IPA Build Script
# This script compiles the web assets, syncs them to the Capacitor iOS project,
# builds the Xcode project without code signing, and packages an unsigned .ipa file.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
IOS_APP_DIR="${FRONTEND_DIR}/ios/App"
OUTPUT_DIR="${PROJECT_ROOT}/build/ios/ipa"

echo "=== [1/4] Building Frontend Web Assets ==="
cd "${FRONTEND_DIR}"
npm run build

echo "=== [2/4] Syncing Capacitor iOS Project ==="
npx cap sync ios

echo "=== [3/4] Compiling iOS Project (Xcode) ==="
cd "${IOS_APP_DIR}"

BUILD_DIR="${IOS_APP_DIR}/DerivedData"
rm -rf "${BUILD_DIR}"

if [ -d "App.xcworkspace" ]; then
  PROJECT_FLAG="-workspace App.xcworkspace"
else
  PROJECT_FLAG="-project App.xcodeproj"
fi

xcodebuild clean build \
  ${PROJECT_FLAG} \
  -scheme App \
  -configuration Release \
  -destination "generic/platform=iOS" \
  -derivedDataPath "${BUILD_DIR}" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGN_STYLE=Manual \
  AD_HOC_CODE_SIGNING_ALLOWED=NO

APP_PATH="${BUILD_DIR}/Build/Products/Release-iphoneos/App.app"

if [ ! -d "${APP_PATH}" ]; then
  echo "Error: Compiled App.app not found at ${APP_PATH}"
  exit 1
fi

echo "=== [4/4] Packaging Unsigned .IPA File ==="
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/Payload"

cp -R "${APP_PATH}" "${OUTPUT_DIR}/Payload/"

cd "${OUTPUT_DIR}"
IPA_NAME="MaxwellAccounting-unsigned.ipa"
zip -qr "${IPA_NAME}" Payload
rm -rf Payload

echo "=========================================================="
echo "SUCCESS! Unsigned IPA created at:"
echo "${OUTPUT_DIR}/${IPA_NAME}"
echo "File size: $(du -h "${OUTPUT_DIR}/${IPA_NAME}" | cut -f1)"
echo "=========================================================="
