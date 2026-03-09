# Adding a New Language

This guide explains how to add a new language to the Local Weather Forecast integration.
The integration currently supports: **German (de), English (en), Greek (gr), Italian (it), Slovak (sk)**.

All forecast texts are stored as positional tuples — each language occupies one fixed index position.
Adding a new language means appending a new element to every tuple in the codebase.

---

## Overview of Changes

| File | What to do |
|---|---|
| `custom_components/local_weather_forecast/const.py` | Register the language code |
| `custom_components/local_weather_forecast/language.py` | Map the language code to its index |
| `custom_components/local_weather_forecast/forecast_data.py` | Add translations for all forecast texts |
| `custom_components/local_weather_forecast/translations/xx.json` | Add UI translations (options form labels) |

---

## Step-by-Step

### Step 1 — Register the language in `const.py`

Open `custom_components/local_weather_forecast/const.py`.

Add your language to `LANGUAGES` (displayed in the UI dropdown):

```python
LANGUAGES: Final = {
    "de": "Deutsch (German)",
    "en": "English",
    "gr": "Ελληνικά (Greek)",
    "it": "Italiano (Italian)",
    "sk": "Slovenčina (Slovak)",
    "fr": "Français (French)",   # ← add your language here
}
```

Add the index to `LANGUAGE_INDEX` — use the **next available integer**:

```python
LANGUAGE_INDEX: Final = {
    "de": 0,
    "en": 1,
    "gr": 2,
    "it": 3,
    "sk": 4,
    "fr": 5,   # ← your index (current max + 1)
}
```

---

### Step 2 — Map the code in `language.py`

Open `custom_components/local_weather_forecast/language.py`.

Add your language code to `LANGUAGE_MAP`:

```python
LANGUAGE_MAP = {
    "de": 0,
    "en": 1,
    "el": 2,   # HA uses 'el' for Greek
    "gr": 2,   # integration uses 'gr'
    "it": 3,
    "sk": 4,
    "fr": 5,   # ← add here
}
```

> **Note:** If Home Assistant uses a different ISO 639-1 code for your language than what you registered in `const.py`, add both mappings (like Greek above uses both `el` and `gr`). Check your HA system language code at **Settings → System → General → Language**.

Update the debug log string at the bottom of `get_language_index()`:

```python
_LOGGER.debug(
    f"Language detection: HA system language={ha_language} → index={lang_index} "
    f"(0=de, 1=en, 2=el, 3=it, 4=sk, 5=fr)"   # ← add your language
)
```

Also update the same string inside the config_entry lookup block a few lines above it.

---

### Step 3 — Add translations in `forecast_data.py`

This is the **main translation work**. Open `custom_components/local_weather_forecast/forecast_data.py`.

Every tuple currently has the format:

```
(German, English, Greek, Italian, Slovak)
```

You need to append your translation at the end of **every** tuple, making it:

```
(German, English, Greek, Italian, Slovak, French)
```

#### Sections to translate (~77 strings total)

| Section | Count | Description |
|---|---|---|
| `CONDITIONS` | 6 | Weather condition names (stormy, rainy, cloudy, etc.) |
| `PRESSURE_SYSTEMS` | 3 | Low / Normal / High pressure system names |
| `FORECAST_TEXTS` | 26 | Main Zambretti forecast texts (Settled Fine … Stormy, Much Rain) |
| `WIND_TYPES` | 13 | Beaufort 0–12 (Calm, Light air, … Hurricane) |
| `VISIBILITY_ESTIMATES` | 4 | Reduced / Possibly reduced / Good / Very good |
| `COMFORT_LEVELS` | 7 | Very cold … Very hot |
| `FOG_RISK_LEVELS` | 5 | None / Low / Medium / High / Critical fog risk |
| `ATMOSPHERE_STABILITY` | 5 | Stable / Moderate / Unstable / Very unstable / Unknown |
| `ADJUSTMENT_TEMPLATES` | 8 | Templates with `{value}` placeholder — keep `{value}` and `°C` exactly as-is |

#### Example — adding French to a `FORECAST_TEXTS` entry:

```python
# Before
("Beständiges Schönwetter!", "Settled Fine", "Σταθερός καλός καιρός!", "Bel tempo stabile", "Stabilne pekné počasie!"),

# After
("Beständiges Schönwetter!", "Settled Fine", "Σταθερός καλός καιρός!", "Bel tempo stabile", "Stabilne pekné počasie!", "Beau temps stable!"),
```

#### In-line dictionaries in `language.py`

Two more dictionaries are defined **inside functions** in `language.py` — these also need translation:

**`SNOW_RISK_LEVELS`** (inside `get_snow_risk_text()`) — 4 entries:
`none`, `low`, `medium`, `high` snow risk levels

**`FROST_RISK_LEVELS`** (inside `get_frost_risk_text()`) — 5 entries:
`none`, `low`, `medium`, `high`, `critical` frost/ice risk levels

Both use the same tuple format as `forecast_data.py`.

---

### Step 4 — Create the UI translation file

Create `custom_components/local_weather_forecast/translations/fr.json`
(replace `fr` with your language code).

Copy `en.json` as a starting point and translate all values. The most important fields are in the `options.step.init` section since that is where the language selector appears to users.

Pay special attention to:
- `options.step.init.data.language` — label for the language dropdown
- `options.step.init.data_description.language` — hint text explaining the setting

---

## Checklist

Before submitting a Pull Request, verify all boxes are ticked:

- [ ] `const.py` — language code added to both `LANGUAGES` and `LANGUAGE_INDEX`
- [ ] `language.py` — language code added to `LANGUAGE_MAP`
- [ ] `language.py` — both debug log strings updated
- [ ] `forecast_data.py` — new translation appended to every tuple in all 9 sections
- [ ] `language.py` — `SNOW_RISK_LEVELS` and `FROST_RISK_LEVELS` inline dicts updated
- [ ] `translations/xx.json` — new UI translation file created
- [ ] All tests pass: `python -m pytest tests/`
- [ ] No existing tuples accidentally shortened (shifting all indices would break every other language)

---

## Quick Sanity Check

After completing your changes, run this script from the repo root to verify all tuples have consistent lengths:

```python
import sys
sys.path.insert(0, ".")
from custom_components.local_weather_forecast.forecast_data import (
    CONDITIONS, PRESSURE_SYSTEMS, FORECAST_TEXTS, WIND_TYPES,
    COMFORT_LEVELS, FOG_RISK_LEVELS, ATMOSPHERE_STABILITY,
    ADJUSTMENT_TEMPLATES, VISIBILITY_ESTIMATES,
)

EXPECTED = 6  # change to current total number of languages

errors = []

for name, data in [
    ("CONDITIONS", CONDITIONS),
    ("PRESSURE_SYSTEMS", PRESSURE_SYSTEMS),
    ("FORECAST_TEXTS", FORECAST_TEXTS),
    ("WIND_TYPES", WIND_TYPES),
]:
    for i, entry in enumerate(data):
        if len(entry) != EXPECTED:
            errors.append(f"{name}[{i}] has {len(entry)} items, expected {EXPECTED}")

for name, data in [
    ("VISIBILITY_ESTIMATES", VISIBILITY_ESTIMATES),
    ("COMFORT_LEVELS", COMFORT_LEVELS),
    ("FOG_RISK_LEVELS", FOG_RISK_LEVELS),
    ("ATMOSPHERE_STABILITY", ATMOSPHERE_STABILITY),
    ("ADJUSTMENT_TEMPLATES", ADJUSTMENT_TEMPLATES),
]:
    for key, entry in data.items():
        if len(entry) != EXPECTED:
            errors.append(f"{name}['{key}'] has {len(entry)} items, expected {EXPECTED}")

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
else:
    print(f"All tuple lengths OK! ({EXPECTED} languages)")
```

---

## Questions?

Open an issue or discussion on [GitHub](https://github.com/wajo666/homeassistant-local-weather-forecast/issues).
