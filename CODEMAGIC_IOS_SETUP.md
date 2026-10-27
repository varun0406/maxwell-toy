# Codemagic iOS CI/CD Setup & Unsigned IPA Guide

## Overview
This repository has been configured to build **Maxwell Accounting** for iOS using **Capacitor 8** and **Codemagic CI/CD**.

Codemagic runs on macOS cloud builders (Apple Silicon M2) with Xcode installed. It compiles the web code, syncs the native iOS Capacitor project, disables code signing, packages the compiled binary into a standard **unsigned `.ipa`** (`MaxwellAccounting-unsigned.ipa`), and uploads it as a downloadable build artifact.

---

## What Was Added & Configured

1. **Capacitor iOS Platform (`@capacitor/ios@8.5.1`)**:
   - Installed and synced in `frontend/package.json`.
   - Added `frontend/ios/` native Xcode SPM project.
   - Configured `frontend/capacitor.config.ts` with iOS-specific options (`contentInset`, `preferredContentMode`, `scheme`).
   - Added npm commands in `frontend/package.json`:
     - `npm run ios:sync` (builds web assets + syncs iOS native project)
     - `npm run ios:open` (opens in Xcode on macOS)

2. **iOS App Configuration (`frontend/ios/App/App/Info.plist`)**:
   - `NSAppTransportSecurity` (`NSAllowsArbitraryLoads: true`) enabled for API and development network requests.
   - Document sharing enabled (`UIFileSharingEnabled` & `LSSupportsOpeningDocumentsInPlace`) so exported invoices and PDFs are accessible in the iOS Files app.

3. **Shared Xcode Scheme**:
   - Created `frontend/ios/App/App.xcodeproj/xcshareddata/xcschemes/App.xcscheme`.
   - Xcode requires a shared scheme to compile headless on CI machines without an interactive GUI.

4. **Unsigned IPA Build Script (`scripts/build-unsigned-ipa.sh`)**:
   - Compiles web assets with Vite.
   - Syncs assets and Swift Package Manager (SPM) plugins to iOS project.
   - Executes `xcodebuild` with:
     ```bash
     CODE_SIGNING_ALLOWED=NO \
     CODE_SIGNING_REQUIRED=NO \
     CODE_SIGN_IDENTITY="" \
     CODE_SIGN_STYLE=Manual \
     AD_HOC_CODE_SIGNING_ALLOWED=NO
     ```
   - Bundles the resulting `App.app` into a `Payload/` folder and creates `build/ios/ipa/MaxwellAccounting-unsigned.ipa`.

5. **Codemagic Pipeline Configuration (`codemagic.yaml`)**:
   - Two workflows configured:
     - `ios-unsigned-ipa` (macOS M2 runner, Node 22, latest Xcode)
     - `android-apk` (Linux runner for Android debug APKs)
   - Triggers on `push` to `main` branch or manual trigger from the Codemagic dashboard.
   - Captures `build/ios/ipa/*.ipa` as downloadable artifacts.

---

## How to Get Your Unsigned `.ipa` from Codemagic

### Step 1: Push Your Changes to GitHub
Commit and push the newly added files to your repository:
```bash
git add .
git commit -m "Add Capacitor iOS support and Codemagic CI/CD for unsigned IPA"
git push origin main
```

### Step 2: Set Up Codemagic (First Time Only)
1. Go to [codemagic.io](https://codemagic.io/) and log in with your GitHub account (`varun0406`).
2. Click **"Add application"**.
3. Select your repository: `varun0406/maxwell-toy` (or `maxwellMobAcc`).
4. Select **"Codemagic configuration file"** (it will automatically find `codemagic.yaml`).
5. Click **"Finish setup"**.

### Step 3: Trigger Build & Download `.ipa`
1. In Codemagic, select the **"Maxwell Accounting iOS (Unsigned IPA)"** workflow.
2. Click **"Start new build"** (or simply push to `main` to trigger automatically).
3. Codemagic will boot a macOS M2 runner, compile everything, and generate the IPA in ~3–5 minutes.
4. When the build finishes, open the build page and click on **Artifacts** on the right side.
5. Download **`MaxwellAccounting-unsigned.ipa`**!

---

## Sideloading / Installing the Unsigned IPA

Because this IPA is unsigned, you can install it on any iOS device (iPhone or iPad) using any of the following tools:

- **AltStore / AltServer**: Free on macOS/Windows, signs with your personal Apple ID (7-day renewable).
- **Sideloadly**: Free on macOS/Windows, drag-and-drop the `.ipa`, enter Apple ID, and it signs and installs directly.
- **TrollStore**: Permanent signing (for compatible iOS versions).
- **Custom Certificate / Enterprise Resigner**: Use tools like `ios-signer-service`, `fastlane resign`, or Apple Developer enterprise profiles.
