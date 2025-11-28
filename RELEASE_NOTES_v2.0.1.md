# Release v2.0.1 - HACS Download Hotfix

## 🐛 Bug Fix

### Fixed HACS Download Error

**Issue:** HACS failed to download integration with error:
```
Got status code 404 when trying to download 
https://github.com/wajo666/homeassistant-local-weather-forecast/releases/download/2.0.0/local_weather_forecast
```

**Cause:** `hacs.json` had `"zip_release": true`, which tells HACS to download a ZIP file attached to the release. Since we're using git-based distribution, this should be `false`.

**Fix:** Changed `"zip_release": true` → `"zip_release": false` in `hacs.json`

---

## 📦 Changes

### hacs.json
```diff
{
  "name": "Local Weather Forecast",
  "content_in_root": false,
  "filename": "local_weather_forecast",
  "render_readme": true,
  "homeassistant": "2024.1.0",
- "zip_release": true,
+ "zip_release": false,
  "hide_default_branch": false
}
```

---

## 🔧 What This Means

- **Before:** HACS tried to download a ZIP file from GitHub releases (which doesn't exist)
- **After:** HACS clones the repository directly from git (correct method)

---

## 📥 Installation

HACS will now correctly download the integration:

1. HACS → Integrations → ⋮ → Custom repositories
2. Add: `wajo666/homeassistant-local-weather-forecast`
3. Category: Integration
4. Click "Download"
5. Select version `2.0.1`
6. Restart Home Assistant

---

## ✅ No Code Changes

This is a **configuration-only fix**. No Python code was modified. All features from v2.0.0 remain the same:

- ✅ UI configuration
- ✅ Multi-language support (5 languages)
- ✅ Pressure type selection
- ✅ Historical data fallback
- ✅ State restoration
- ✅ 7 sensors with proper device classes

---

## 🔄 Upgrading from v2.0.0

If you manually installed v2.0.0:
1. HACS → Local Weather Forecast → ⋮ → Reinstall
2. Select v2.0.1
3. Restart Home Assistant

No configuration changes needed.

---

## 📖 Full v2.0.0 Release Notes

See [RELEASE_NOTES_v2.0.0.md](RELEASE_NOTES_v2.0.0.md) for complete changelog of the major v2.0.0 release.

---

**Version:** 2.0.1  
**Date:** 2025-01-28  
**Type:** Hotfix  
**Breaking Changes:** No

