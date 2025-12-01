# Architecture Overview - Extended Sensors Feature

## Current Architecture (v3.0.3)

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Local Weather Forecast Integration             │
│                                                             │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Config Flow   │  │  __init__.py │  │   sensor.py     │ │
│  │  - Setup      │  │  - Platform  │  │  - Main Sensor  │ │
│  │  - Options    │  │    loading   │  │  - Pressure     │ │
│  └───────────────┘  └──────────────┘  │  - Temperature  │ │
│                                       │  - Changes      │ │
│  ┌───────────────┐  ┌──────────────┐  │  - Details      │ │
│  │   const.py    │  │forecast_data │  └─────────────────┘ │
│  │  - Constants  │  │  - Texts     │                      │
│  └───────────────┘  └──────────────┘  ┌─────────────────┐ │
│                                       │  zambretti.py   │ │
│                                       │  - Algorithm    │ │
│                                       └─────────────────┘ │
│                                       ┌─────────────────┐ │
│                                       │negretti_zambra  │ │
│                                       │  - Algorithm    │ │
│                                       └─────────────────┘ │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │         Input Sensors (Required)     │
        │  - sensor.pressure                   │
        │  - sensor.temperature                │
        │  - sensor.wind_direction (optional)  │
        │  - sensor.wind_speed (optional)      │
        └──────────────────────────────────────┘
```

## New Architecture (v3.1.0) - Extended Sensors

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          Home Assistant Core                               │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                   Local Weather Forecast Integration                       │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────────────┐    │
│  │  Config Flow     │  │ __init__.py  │  │      sensor.py             │    │
│  │  - Basic Setup   │  │ - Platform   │  │  ┌──────────────────────┐  │    │
│  │  - Advanced      │  │   loading    │  │  │  Existing Sensors:   │  │    │
│  │    Sensors ✨    │  │ - Weather    │  │  │  - Main              │  │   │
│  │  - Features ✨   │  │   setup ✨   │  │  │  - Pressure          │  │  │
│  └──────────────────┘  └──────────────┘   │  │  - Temperature      │  │  │
│                                           │  │  - Changes          │  │  │
│  ┌──────────────────┐  ┌──────────────┐   │  │  - Details          │  │  │
│  │    const.py      │  │forecast_data │   │  └─────────────────────┘  │  │
│  │  - Constants     │  │  - Texts     │   │                            │  │
│  │  - Extended ✨   │  └──────────────┘   │  ┌─────────────────────┐  │  │
│  └──────────────────┘                     │  │  New Sensors: ✨    │  │  │
│                                           │  │  - Comfort Index    │  │  │
│  ┌──────────────────┐  ┌──────────────┐   │  │  - Dew Point        │  │  │
│  │ calculations.py ✨│  │zambretti.py  │  │  │  - Fog Risk         │  │  │
│  │  - Dew Point     │  │  - Algorithm │  │  │  - Rain Prob Enh.    │  │  │
│  │  - Heat Index    │  └──────────────┘  │  │  - Condition         │  │  │
│  │  - Wind Chill    │                    │  │  - Trend             │  │  │
│  │  - Comfort       │  ┌──────────────┐  │  └──────────────────────┘  │  │
│  │  - Fog Risk      │  │negretti_     │  └────────────────────────────┘  │
│  │  - Rain Enhanced │  │  zambra.py   │                                  │
│  │  - Interpolation │  │  - Algorithm │   ┌───────────────────────────┐  │
│  └──────────────────┘  └──────────────┘   │      weather.py ✨        │  │
│                                           │  - LocalWeatherForecast   │   │
│                                           │  - Current conditions     │   │
│                                           │  - Forecast generation    │   │
│                                           │  - get_forecasts()        │   │
│                                           └────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴────────────────────────────┐
        │                                                        │
        ▼                                                        ▼
┌──────────────────────┐                          ┌──────────────────────────┐
│  Required Sensors    │                          │  Optional Sensors ✨     │
│  - pressure          │                          │  - humidity              │
│  - temperature       │                          │  - dewpoint              │
│  - wind_direction    │                          │  - cloud_coverage        │
│  - wind_speed        │                          │  - uv_index              │
└──────────────────────┘                          │  - visibility            │
                                                  │  - wind_gust             │
                                                  │  - rain_rate             │
                                                  │  - precipitation         │
                                                  └──────────────────────────┘
```

## Data Flow - Forecast Generation

### Current (v3.0.3):
```
Input Sensors
     │
     ├─→ Pressure ──────┐
     ├─→ Temperature ───┤
     ├─→ Wind Dir ──────┤
     └─→ Wind Speed ────┤
                        │
                        ▼
                  ┌──────────┐
                  │ History  │
                  │ Tracking │
                  └──────────┘
                        │
                        ▼
            ┌─────────────────────┐
            │   Trend Analysis    │
            │  - Pressure trend   │
            │  - Temp trend       │
            └─────────────────────┘
                        │
                        ▼
            ┌─────────────────────┐
            │  Zambretti Forecast │
            └─────────────────────┘
                        │
                        ▼
            ┌─────────────────────┐
            │ Negretti-Z Forecast │
            └─────────────────────┘
                        │
                        ▼
            ┌─────────────────────┐
            │   Main Sensor       │
            │  - State: "12hr..."│
            │  - Attributes       │
            └─────────────────────┘
```

### New (v3.1.0):
```
Required Sensors          Optional Sensors ✨
     │                         │
     ├─→ Pressure ─────────┐   ├─→ Humidity ────────┐
     ├─→ Temperature ──────┤   ├─→ Dew Point ───────┤
     ├─→ Wind Dir ─────────┤   ├─→ Cloud Coverage ──┤
     └─→ Wind Speed ───────┤   ├─→ UV Index ─────────┤
                           │   ├─→ Visibility ───────┤
                           │   ├─→ Wind Gust ────────┤
                           │   └─→ Rain Rate ────────┤
                           │                         │
                           ▼                         ▼
                      ┌────────────────────────────────┐
                      │       History Tracking         │
                      │  - Pressure history            │
                      │  - Temperature history         │
                      │  - Humidity history ✨         │
                      └────────────────────────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────────┐
                      │      Trend Analysis            │
                      │  - Pressure trend              │
                      │  - Temperature trend           │
                      │  - Humidity trend ✨           │
                      └────────────────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                    ▼                                ▼
        ┌────────────────────┐         ┌────────────────────────┐
        │ Zambretti Forecast │         │  Negretti-Z Forecast   │
        └────────────────────┘         └────────────────────────┘
                    │                                │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │    calculations.py ✨           │
                    │  - Dew point calc               │
                    │  - Apparent temp                │
                    │  - Fog risk                     │
                    │  - Enhanced rain prob           │
                    │  - Comfort level                │
                    └─────────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────────┐
    │  Sensor Entities    │         │   Weather Entity ✨     │
    │  - Main             │         │  - current_condition    │
    │  - Pressure         │         │  - temperature          │
    │  - Temperature      │         │  - humidity             │
    │  - Changes          │         │  - pressure             │
    │  - Details          │         │  - dew_point            │
    │  - Comfort ✨       │         │  - forecast:            │
    │  - Dew Point ✨     │         │    * 1h intervals       │
    │  - Fog Risk ✨      │         │    * 3h intervals       │
    │  - Rain Prob ✨     │         │    * Daily              │
    │  - Condition ✨     │         └─────────────────────────┘
    │  - Trend ✨         │
    └─────────────────────┘
```

## Module Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                        __init__.py                          │
│  - async_setup_entry()                                      │
│  - async_unload_entry()                                     │
│  - Platform loading                                         │
└─────────────────────────────────────────────────────────────┘
                             │
                             │ loads
                             │
            ┌────────────────┴────────────────┐
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌──────────────────────────┐
│     sensor.py         │         │      weather.py ✨       │
│                       │         │                          │
│  Imports:             │         │  Imports:                │
│  - const              │         │  - const                 │
│  - forecast_data      │         │  - calculations ✨       │
│  - zambretti          │         │  - zambretti             │
│  - negretti_zambra    │         │  - negretti_zambra       │
│  - calculations ✨    │         │  - forecast_data         │
└───────────────────────┘         └──────────────────────────┘
            │                                 │
            └────────────────┬────────────────┘
                             │ both use
                             │
            ┌────────────────┴────────────────┐
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌──────────────────────────┐
│   zambretti.py        │         │  negretti_zambra.py      │
│  - Algorithm logic    │         │  - Algorithm logic       │
│  - Pressure-based     │         │  - Dual algorithm        │
└───────────────────────┘         └──────────────────────────┘
            │                                 │
            └────────────────┬────────────────┘
                             │ both use
                             │
                             ▼
            ┌────────────────────────────────┐
            │       forecast_data.py         │
            │  - FORECAST_TEXTS              │
            │  - PRESSURE_SYSTEMS            │
            │  - CONDITIONS                  │
            └────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────┐
│                     calculations.py ✨                       │
│                                                             │
│  Standalone module - no internal dependencies               │
│  Used by: sensor.py, weather.py                            │
│                                                             │
│  Exports:                                                   │
│  - calculate_dewpoint()                                     │
│  - calculate_heat_index()                                   │
│  - calculate_wind_chill()                                   │
│  - calculate_apparent_temperature()                         │
│  - get_comfort_level()                                      │
│  - get_fog_risk()                                           │
│  - calculate_rain_probability_enhanced()                    │
│  - interpolate_forecast()                                   │
│  - calculate_visibility_from_humidity()                     │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Flow

### Current (v3.0.3):
```
User initiates setup
        │
        ▼
┌───────────────────┐
│  Step 1: Basic    │
│  - Pressure       │
│  - Temperature    │
│  - Wind Dir       │
│  - Wind Speed     │
│  - Elevation      │
│  - Language       │
│  - Pressure Type  │
└───────────────────┘
        │
        ▼
    Setup Complete
```

### New (v3.1.0):
```
User initiates setup
        │
        ▼
┌───────────────────────┐
│  Step 1: Basic        │
│  - Pressure           │
│  - Temperature        │
│  - Wind Dir           │
│  - Wind Speed         │
│  - Elevation          │
│  - Language           │
│  - Pressure Type      │
└───────────────────────┘
        │
        ▼
┌───────────────────────────┐
│  Step 2: Advanced ✨      │
│  (Optional)               │
│  - Humidity               │
│  - Dew Point              │
│  - Cloud Coverage         │
│  - UV Index               │
│  - Visibility             │
│  - Wind Gust              │
│  - Rain Rate              │
│  - Precipitation          │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│  Step 3: Features ✨      │
│  - Enable Weather Entity  │
│  - Enable Extended Sensors│
│  - Forecast Interval      │
│    (1h / 3h / 6h)         │
└───────────────────────────┘
        │
        ▼
    Setup Complete
```

## Entity Structure

### Current Entities (v3.0.3):
```
sensor.local_forecast                    (Main sensor - 12hr forecast)
sensor.local_forecast_pressure           (Current pressure)
sensor.local_forecast_temperature        (Current temperature)
sensor.local_forecast_pressurechange     (Pressure trend)
sensor.local_forecast_temperaturechange  (Temperature trend)
sensor.local_forecast_zambretti_detail   (Zambretti details)
sensor.local_forecast_neg_zam_detail     (Negretti-Z details)
```

### New Entities (v3.1.0):
```
Existing sensors (unchanged):
  sensor.local_forecast
  sensor.local_forecast_pressure
  sensor.local_forecast_temperature
  sensor.local_forecast_pressurechange
  sensor.local_forecast_temperaturechange
  sensor.local_forecast_zambretti_detail
  sensor.local_forecast_neg_zam_detail

New sensors (if enabled): ✨
  sensor.local_forecast_comfort_index      (Apparent temperature)
  sensor.local_forecast_dewpoint           (Dew point temperature)
  sensor.local_forecast_fog_risk           (Fog risk level)
  sensor.local_forecast_rain_probability   (Enhanced rain %)
  sensor.local_forecast_condition          (HA standard condition)
  sensor.local_forecast_trend              (Overall trend)

Weather entity (if enabled): ✨
  weather.local_forecast                   (Weather platform entity)
```

## Legend

✨ = New in v3.1.0
─ = Data flow
│ = Dependency

