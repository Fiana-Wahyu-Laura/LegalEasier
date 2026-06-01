# Frontend Deployment & Signing

This document describes the recommended steps to prepare Android signing and CI release for the Flutter frontend.

1) Generate Android release keystore (locally):

```bash
keytool -genkey -v -keystore release-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias <KEY_ALIAS>
```

2) Create `key.properties` in `frontend/android/` (or configure via CI):

```
storePassword=<KEYSTORE_PASSWORD>
keyPassword=<KEY_PASSWORD>
keyAlias=<KEY_ALIAS>
storeFile=release-keystore.jks
```

3) Add keystore & secrets to GitHub (recommended pattern):
- Encode keystore as base64 and save to secret `ANDROID_KEYSTORE_BASE64`.
- Add secrets: `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`.

Linux/macOS encode:

```bash
base64 release-keystore.jks > keystore.b64
# copy keystore.b64 contents into GitHub secret ANDROID_KEYSTORE_BASE64
```

Windows encode (PowerShell):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('release-keystore.jks')) | clip
# paste into GitHub secret
```

4) Example workflow snippet to restore keystore (use in GitHub Actions):

```yaml
- name: Restore keystore
  run: |
    echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 --decode > frontend/android/app/release-keystore.jks
```

Then ensure `key.properties` points to `frontend/android/app/release-keystore.jks` or adjust `storeFile` path accordingly.

5) Play Store / Internal Release
- For automatic Play Store uploads, create a Google Play Service Account and add its JSON as GitHub secret `PLAYSTORE_SERVICE_ACCOUNT_JSON`.
- Use Fastlane or `google-play-publisher` actions in CI to upload. Do not commit service account JSON to repo.

6) Notes
- The provided `.github/workflows/flutter-release.yml` builds an unsigned AAB by default; to sign automatically in CI follow step 3 & 4 above and add restore/decode step before building.
- Keep all secrets in GitHub repository or organization secrets and never commit them to the repo.
