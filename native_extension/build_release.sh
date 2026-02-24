#!/bin/bash

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
RELEASE_NAME="One-Click-Youtube-Downloader-Native"
RELEASE_ZIP="${RELEASE_NAME}.zip"
BUILD_DIR="${PROJECT_DIR}/build_tmp"

echo "======================================"
echo " Packaging Release: ${RELEASE_ZIP}"
echo "======================================"

# Clean up previous builds
rm -rf "${BUILD_DIR}"
rm -f "${PROJECT_DIR}/${RELEASE_ZIP}"

# Create staging directory
mkdir -p "${BUILD_DIR}/${RELEASE_NAME}"

# Copy Extension files
echo "[+] Copying Chrome Extension files..."
cp -r "${PROJECT_DIR}/extension" "${BUILD_DIR}/${RELEASE_NAME}/"

# Copy Host files, excluding dev artifacts
echo "[+] Copying Python Native Host files..."
mkdir -p "${BUILD_DIR}/${RELEASE_NAME}/host"
cp "${PROJECT_DIR}/host/"*.py "${BUILD_DIR}/${RELEASE_NAME}/host/"
cp "${PROJECT_DIR}/host/"*.txt "${BUILD_DIR}/${RELEASE_NAME}/host/" 2>/dev/null || true

# Strip any test or dev scripts we created
rm -f "${BUILD_DIR}/${RELEASE_NAME}/host/test_"*
rm -f "${BUILD_DIR}/${RELEASE_NAME}/host/update_"*
rm -f "${BUILD_DIR}/${RELEASE_NAME}/host/mock_"*

# Zip the release package cleanly
echo "[+] Zipping release package..."
cd "${BUILD_DIR}"
zip -qr "${RELEASE_ZIP}" "${RELEASE_NAME}"

# Move to root
mv "${RELEASE_ZIP}" "${PROJECT_DIR}/"

# Clean up
cd "${PROJECT_DIR}"
rm -rf "${BUILD_DIR}"

echo "======================================"
echo "✅ Success! Release package generated:"
echo "   ${PROJECT_DIR}/${RELEASE_ZIP}"
echo "======================================"
