# Publishing builds

How `.github/workflows/release.yml` turns a `git tag` into downloadable builds,
and what's still missing before those builds are store-ready.

## What the release workflow produces today

Push a tag matching `v*` (e.g. `v0.1.0`) and the workflow builds all four
clients and attaches what it can to a GitHub Release:

| Client | Job | Output | Status |
| --- | --- | --- | --- |
| Windows | `windows` | `VisualPose-Windows-x64.zip` | Unsigned. SmartScreen will warn on first run ("keep anyway"). |
| macOS | `macos` | `VisualPose-macOS.zip` | Unsigned. Gatekeeper blocks it until the user right-clicks → Open once, or runs `xattr -cr VisualPose.app`. |
| Android | `android` | `VisualPose-Android-debug.apk` | Debug-signed (Gradle's auto-generated debug key). Installable directly ("allow unknown sources"), not a Play Store release. |
| iOS | `ios-verify` | *(none)* | Build-only. No signing certificate configured, so CI can prove the app still compiles but cannot produce an installable `.ipa`. |

Windows/macOS both come from `scripts/packaging/visualpose.spec` (one
PyInstaller spec, run on each OS's own runner) — verified locally before this
workflow was written by launching the built `.app` and confirming it starts
clean with no missing-asset errors.

## Blockers to a real store release

### iOS — hard blocker, needs your Apple ID

Apple requires a paid Apple Developer Program membership ($99/yr) plus a
Distribution certificate and provisioning profile to sign anything installable
outside Xcode. None of that exists in this repo or in CI. To get a
downloadable/TestFlight build going:

1. Enroll at [developer.apple.com](https://developer.apple.com/programs/) if
   not already enrolled.
2. Create an App ID for `local.visual.corepose` in the developer portal.
3. Create a Distribution certificate + an App Store (or Ad Hoc, for direct
   `.ipa` download) provisioning profile.
4. Export the certificate as a `.p12`, base64-encode it, and add as repo
   secrets: `IOS_CERT_P12`, `IOS_CERT_PASSWORD`, `IOS_PROVISION_PROFILE`,
   `IOS_TEAM_ID`.
5. Extend the `ios-verify` job to `xcodebuild archive` + `exportArchive` with
   those secrets (fastlane's `match`/`gym` is the common way to keep this
   maintainable once it exists).

Until then, iOS testers need Xcode + a device: `open
clients/ios/VisualPose.xcworkspace`, set your own team in Signing &
Capabilities, run on a connected iPhone.

### Android — soft blocker, needed only for Play Store

The debug APK works for direct install today. Play Store submission needs a
release build signed with a real upload key instead of Gradle's debug key:

1. `keytool -genkey -v -keystore release.keystore -keyalg RSA -keysize 2048 -validity 10000 -alias visualpose`
2. Add a `signingConfigs { release { ... } }` block to
   `clients/android/app/build.gradle.kts` reading the keystore path/passwords
   from env vars (never commit the keystore).
3. Add the keystore (base64) + passwords as repo secrets, wire
   `assembleRelease`/`bundleRelease` into CI, and switch the release workflow
   to upload the signed AAB instead of (or alongside) the debug APK.
4. Play Console: Data Safety form, Target Audience and Content, Content
   Rating questionnaire — flagged earlier as required given the app's
   child-relevant (7-12, 13-17) curriculum tracks.

### Windows/macOS — soft blocker, cosmetic only

Unsigned builds work but trigger OS warnings on first launch. Fixing that
needs a code-signing certificate (Windows: an EV/OV cert from a CA; macOS: an
Apple Developer ID Application certificate + notarization) — optional for a
GitHub Release aimed at testers, worth doing before a public download page.

## Cutting a release

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then watch it: `gh run watch` or the Actions tab. Re-running is just
`workflow_dispatch` (no new tag needed) or pushing a new tag for a real
version bump.
