"""Tests for calculations module."""
import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from custom_components.local_weather_forecast.calculations import (
    calculate_dewpoint,
    calculate_heat_index,
    calculate_wind_chill,
    calculate_apparent_temperature,
    get_comfort_level,
    get_fog_risk,
    calculate_rain_probability_enhanced,
    interpolate_forecast,
    calculate_visibility_from_humidity,
    calculate_uv_index_from_solar_radiation,
    calculate_solar_radiation_from_uv_index,
    get_snow_risk,
    get_frost_risk,
    get_uv_protection_level,
    estimate_solar_radiation_from_time_and_clouds,
    get_uv_risk_category,
)


class TestCalculateDewpoint:
    """Tests for calculate_dewpoint function."""

    def test_normal_conditions(self):
        """Test dewpoint calculation under normal conditions."""
        # At 20°C and 60% humidity, dewpoint should be around 12°C
        result = calculate_dewpoint(20.0, 60.0)
        assert result is not None
        assert 11.0 <= result <= 13.0

    def test_saturated_air(self):
        """Test dewpoint when air is saturated (100% humidity)."""
        # When humidity is 100%, dewpoint equals temperature
        result = calculate_dewpoint(15.0, 100.0)
        assert result is not None
        assert abs(result - 15.0) < 0.5

    def test_very_dry(self):
        """Test dewpoint with very low humidity."""
        result = calculate_dewpoint(25.0, 20.0)
        assert result is not None
        assert result < 5.0

    def test_invalid_humidity_zero(self):
        """Test that zero humidity returns None."""
        assert calculate_dewpoint(20.0, 0.0) is None

    def test_invalid_humidity_over_100(self):
        """Test that humidity over 100% returns None."""
        assert calculate_dewpoint(20.0, 101.0) is None

    def test_negative_temperature(self):
        """Test dewpoint with negative temperature."""
        result = calculate_dewpoint(-5.0, 80.0)
        assert result is not None
        assert result < -5.0


class TestCalculateHeatIndex:
    """Tests for calculate_heat_index function."""

    def test_hot_humid_conditions(self):
        """Test heat index in hot and humid conditions."""
        # 35°C with 70% humidity should feel much hotter
        result = calculate_heat_index(35.0, 70.0)
        assert result is not None
        assert result > 35.0

    def test_not_applicable_low_temp(self):
        """Test that heat index is not calculated for temperatures below 27°C."""
        assert calculate_heat_index(25.0, 80.0) is None

    def test_not_applicable_low_humidity(self):
        """Test that heat index is not calculated for very low humidity."""
        assert calculate_heat_index(35.0, 0.0) is None

    def test_extreme_conditions(self):
        """Test heat index under extreme conditions."""
        result = calculate_heat_index(40.0, 90.0)
        assert result is not None
        assert result > 50.0  # Should feel dangerously hot


class TestCalculateWindChill:
    """Tests for calculate_wind_chill function."""

    def test_cold_windy_conditions(self):
        """Test wind chill in cold and windy conditions."""
        # 0°C with 30 km/h wind should feel colder
        result = calculate_wind_chill(0.0, 30.0)
        assert result is not None
        assert result < 0.0

    def test_not_applicable_warm_temp(self):
        """Test that wind chill is not calculated for temperatures >= 10°C."""
        assert calculate_wind_chill(15.0, 20.0) is None

    def test_very_cold_strong_wind(self):
        """Test wind chill with very cold temperature and strong wind."""
        result = calculate_wind_chill(-10.0, 50.0)
        assert result is not None
        assert result < -15.0


class TestCalculateApparentTemperature:
    """Tests for calculate_apparent_temperature function."""

    def test_temperature_only(self):
        """Test apparent temperature with only temperature provided."""
        result = calculate_apparent_temperature(20.0)
        assert result == 20.0

    def test_with_humidity(self):
        """Test apparent temperature with humidity."""
        result = calculate_apparent_temperature(25.0, humidity=80.0)
        assert result is not None
        assert result != 25.0  # Should be adjusted

    def test_with_wind(self):
        """Test apparent temperature with wind speed."""
        result = calculate_apparent_temperature(10.0, wind_speed=20.0)
        assert result is not None
        assert result < 10.0  # Wind should make it feel colder

    def test_with_solar_radiation(self):
        """Test apparent temperature with solar radiation."""
        result = calculate_apparent_temperature(20.0, solar_radiation=800.0)
        assert result is not None
        assert result > 20.0  # Sun should make it feel warmer

    def test_all_factors(self):
        """Test apparent temperature with all factors."""
        result = calculate_apparent_temperature(
            temperature=22.0,
            humidity=60.0,
            wind_speed=15.0,
            solar_radiation=600.0
        )
        assert result is not None


class TestGetComfortLevel:
    """Tests for get_comfort_level function."""

    def test_very_cold(self):
        """Test very cold comfort level."""
        assert get_comfort_level(-15.0) == "very_cold"

    def test_cold(self):
        """Test cold comfort level."""
        assert get_comfort_level(0.0) == "cold"

    def test_cool(self):
        """Test cool comfort level."""
        assert get_comfort_level(10.0) == "cool"

    def test_comfortable(self):
        """Test comfortable level."""
        assert get_comfort_level(20.0) == "comfortable"

    def test_warm(self):
        """Test warm comfort level."""
        assert get_comfort_level(27.0) == "warm"

    def test_hot(self):
        """Test hot comfort level."""
        assert get_comfort_level(32.0) == "hot"

    def test_very_hot(self):
        """Test very hot comfort level."""
        assert get_comfort_level(38.0) == "very_hot"


class TestGetFogRisk:
    """Tests for get_fog_risk function."""

    def test_no_fog_risk(self):
        """Test no fog risk with large temperature-dewpoint spread."""
        assert get_fog_risk(20.0, 10.0) == "none"  # spread = 10.0
        assert get_fog_risk(20.0, 10.0, 50.0) == "none"  # with humidity

    def test_low_fog_risk(self):
        """Test low fog risk."""
        # Without humidity - conservative spread-only estimate
        assert get_fog_risk(20.0, 17.0) == "low"  # spread = 3.0
        # With humidity but too dry for fog
        assert get_fog_risk(20.0, 17.0, 50.0) == "none"  # spread = 3.0, RH too low
        # With humidity in mist range
        assert get_fog_risk(20.0, 17.0, 80.0) == "low"  # spread = 3.0, RH 80%

    def test_medium_fog_risk(self):
        """Test medium fog risk."""
        # Without humidity - conservative estimate
        assert get_fog_risk(10.0, 8.0) == "medium"  # spread = 2.0
        # With humidity - WMO mist conditions
        assert get_fog_risk(10.0, 8.0, 88.0) == "medium"  # spread = 2.0, RH 88% (mist)

    def test_high_fog_risk(self):
        """Test high fog risk with small spread."""
        # Without humidity
        assert get_fog_risk(8.0, 7.0) == "high"  # spread = 1.0
        # With high humidity - WMO fog conditions (spread < 1.0°C, RH > 90%)
        assert get_fog_risk(8.0, 7.2, 92.0) == "high"  # spread = 0.8, RH 92% (< 1.0)

    def test_critical_fog_conditions(self):
        """Test critical fog conditions (spread < 1°C)."""
        # Without humidity
        assert get_fog_risk(5.0, 4.5) == "high"  # spread = 0.5
        # With humidity - WMO dense fog
        assert get_fog_risk(5.0, 4.5, 96.0) == "high"  # spread = 0.5, RH 96%

    def test_wmo_compliant_thresholds(self):
        """Test WMO compliant fog detection with humidity."""
        # WMO Code 12: Dense fog (spread < 0.5°C, RH > 95%)
        assert get_fog_risk(10.0, 9.6, 96.0) == "high"  # spread = 0.4, RH 96%
        
        # WMO Code 11: Fog (spread < 1.0°C, RH > 90%)
        assert get_fog_risk(10.0, 9.2, 91.0) == "high"  # spread = 0.8, RH 91%
        
        # WMO Code 10: Light fog (spread < 1.5°C, RH > 90%)
        assert get_fog_risk(10.0, 8.8, 91.0) == "medium"  # spread = 1.2, RH 91%
        
        # WMO Code 30: Mist (spread < 2.5°C, RH > 85%)
        assert get_fog_risk(10.0, 8.0, 87.0) == "medium"  # spread = 2.0, RH 87%
        
        # Dry air - no fog despite small spread
        assert get_fog_risk(10.0, 9.0, 70.0) == "none"  # spread = 1.0, RH too low


class TestCalculateRainProbabilityEnhanced:
    """Tests for calculate_rain_probability_enhanced function."""

    def test_base_probability_only(self):
        """Test with only base probabilities."""
        prob, conf = calculate_rain_probability_enhanced(55, 55)
        assert 0 <= prob <= 100
        assert conf == "low"

    def test_with_high_humidity(self):
        """Test rain probability with high humidity."""
        prob, conf = calculate_rain_probability_enhanced(
            50, 0, humidity=90.0
        )
        assert prob > 50
        assert conf in ["medium", "high", "very_high"]

    def test_with_low_dewpoint_spread(self):
        """Test rain probability with low dewpoint spread (saturation)."""
        prob, conf = calculate_rain_probability_enhanced(
            40, 0, dewpoint_spread=1.0
        )
        assert prob > 40

    def test_low_base_probability_scaling(self):
        """Test that low base probability limits adjustments."""
        prob, conf = calculate_rain_probability_enhanced(
            10, 0, humidity=95.0, dewpoint_spread=0.5
        )
        # Even with high humidity and saturation, low base prob shouldn't spike too much
        # However, critical conditions (95% humidity + 0.5°C spread) should add significant probability
        assert prob <= 30  # Adjusted to reflect realistic critical conditions

    def test_high_base_probability_scaling(self):
        """Test that high base probability boosts adjustments."""
        prob, conf = calculate_rain_probability_enhanced(
            70, 0, humidity=90.0, dewpoint_spread=1.0
        )
        assert prob > 70

    def test_dry_conditions(self):
        """Test that dry conditions reduce probability."""
        prob, conf = calculate_rain_probability_enhanced(
            50, 0, humidity=30.0, dewpoint_spread=10.0
        )
        assert prob < 50

    def test_critical_saturation_with_low_base(self):
        """Test that critical saturation (spread <1°C) uses higher scale factor."""
        # Low base (0%) + critical saturation (0.4°C) + high humidity (80%)
        # Should use scale=0.8 instead of 0.3
        prob, conf = calculate_rain_probability_enhanced(
            0, 0, humidity=80.6, dewpoint_spread=0.4, temperature=0.0
        )
        # With scale=0.8: (10 + 15) × 0.8 = 20% (instead of ~7.5% with scale=0.3)
        assert prob >= 18, f"Expected ≥18%, got {prob}%"
        assert prob <= 22, f"Expected ≤22%, got {prob}%"

    def test_cold_weather_humidity_threshold(self):
        """Test that cold weather (≤0°C) uses lower humidity threshold (75% vs 85%)."""
        # At 0°C, 80% humidity should trigger +10 adjustment (threshold=75%)
        prob1, _ = calculate_rain_probability_enhanced(
            0, 0, humidity=80.0, temperature=0.0, dewpoint_spread=0.5
        )
        # At 10°C, 80% humidity should NOT trigger +10 (threshold=85%)
        prob2, _ = calculate_rain_probability_enhanced(
            0, 0, humidity=80.0, temperature=10.0, dewpoint_spread=0.5
        )
        # Cold weather should have higher probability due to lower threshold
        assert prob1 > prob2, f"Cold weather ({prob1}%) should have higher prob than warm ({prob2}%)"

    def test_snowing_conditions_realistic(self):
        """Test realistic snowing conditions: 0°C, 80.6% humidity, 0.4°C spread."""
        # This is the reported scenario from the user
        prob, conf = calculate_rain_probability_enhanced(
            0, 0,  # Zambretti/Negretti say "Settled Fine" (0%)
            humidity=80.6,
            dewpoint_spread=0.4,
            temperature=0.0
        )
        # Expected:
        # - Humidity 80.6% > 75% (cold threshold) → +10
        # - Dewpoint 0.4°C < 1.0°C → +15 + scale=0.8
        # - Total: (10 + 15) × 0.8 = 20%
        assert prob >= 18, f"Snowing conditions should show ≥18%, got {prob}%"
        assert prob <= 22, f"Snowing conditions should show ≤22%, got {prob}%"


class TestInterpolateForecast:
    """Tests for interpolate_forecast function."""

    def test_zero_hours(self):
        """Test interpolation at current time."""
        result = interpolate_forecast(20.0, 30.0, 0, 12)
        assert result == 20.0

    def test_half_time(self):
        """Test interpolation at halfway point."""
        result = interpolate_forecast(20.0, 30.0, 6, 12)
        assert result == 25.0

    def test_full_time(self):
        """Test interpolation at forecast time."""
        result = interpolate_forecast(20.0, 30.0, 12, 12)
        assert result == 30.0

    def test_beyond_forecast_time(self):
        """Test interpolation beyond forecast time."""
        result = interpolate_forecast(20.0, 30.0, 15, 12)
        assert result == 30.0


class TestCalculateVisibilityFromHumidity:
    """Tests for calculate_visibility_from_humidity function."""

    def test_very_high_humidity(self):
        """Test visibility in very high humidity (fog conditions, RH > 95%)."""
        result = calculate_visibility_from_humidity(98.0, 10.0)
        assert result is not None
        # WMO: RH > 95% = fog conditions, visibility < 1 km
        assert result == 0.5  # 500m (will be further reduced by fog adjustments)

    def test_high_humidity(self):
        """Test visibility in high humidity (mist, RH 85-90%)."""
        result = calculate_visibility_from_humidity(87.0, 20.0)
        assert result is not None
        # WMO: RH 85-90% = mist, visibility 1-5 km
        assert result == 1.5  # 1.5km (middle of mist range)

    def test_moderate_humidity(self):
        """Test visibility in moderate humidity (RH 70-80%)."""
        result = calculate_visibility_from_humidity(75.0, 15.0)
        assert result is not None
        # WMO: RH 70-80% = moderate visibility, 4-10 km
        assert result == 7.0  # 7km (moderate visibility)

    def test_low_humidity(self):
        """Test visibility in low humidity (very good visibility, RH < 50%)."""
        result = calculate_visibility_from_humidity(50.0, 25.0)
        assert result is not None
        # WMO: RH < 50% = excellent visibility, > 40 km
        assert result == 50.0  # 50km (excellent visibility)

    def test_fog_conditions(self):
        """Test visibility in dense fog (RH > 95%)."""
        result = calculate_visibility_from_humidity(96.0, 5.0)
        assert result == 0.5  # 500m (fog)

    def test_light_fog_mist(self):
        """Test visibility in light fog/heavy mist (RH 90-95%)."""
        result = calculate_visibility_from_humidity(92.0, 10.0)
        assert result == 0.8  # 800m (borderline fog/mist)

    def test_poor_visibility(self):
        """Test visibility in poor conditions (RH 80-85%)."""
        result = calculate_visibility_from_humidity(82.0, 15.0)
        assert result == 3.0  # 3km (poor visibility)

    def test_good_visibility(self):
        """Test visibility in good conditions (RH 60-70%)."""
        result = calculate_visibility_from_humidity(65.0, 20.0)
        assert result == 15.0  # 15km (good visibility)

    def test_very_good_visibility(self):
        """Test visibility in very good conditions (RH 50-60%)."""
        result = calculate_visibility_from_humidity(55.0, 25.0)
        assert result == 30.0  # 30km (very good visibility)

    def test_excellent_visibility(self):
        """Test visibility in excellent conditions (RH < 50%)."""
        result = calculate_visibility_from_humidity(40.0, 30.0)
        assert result == 50.0  # 50km (excellent visibility)

    def test_invalid_humidity(self):
        """Test with invalid humidity values."""
        assert calculate_visibility_from_humidity(0.0, 20.0) is None
        assert calculate_visibility_from_humidity(101.0, 20.0) is None


class TestCalculateUVIndexFromSolarRadiation:
    """Tests for calculate_uv_index_from_solar_radiation function."""

    def test_high_solar_radiation(self):
        """Test UV index from high solar radiation."""
        result = calculate_uv_index_from_solar_radiation(1000.0)
        assert result is not None
        # 1000 W/m² * 0.04 = 40, but capped at 15
        assert result == 15.0

    def test_moderate_solar_radiation(self):
        """Test UV index from moderate solar radiation."""
        result = calculate_uv_index_from_solar_radiation(500.0)
        assert result is not None
        # 500 * 0.04 = 20, but capped at 15
        assert result == 15.0

    def test_low_solar_radiation(self):
        """Test UV index from low solar radiation."""
        result = calculate_uv_index_from_solar_radiation(200.0)
        assert result is not None
        # 200 * 0.04 = 8
        assert 7.0 <= result <= 9.0


    def test_capped_at_15(self):
        """Test that UV index is capped at 15."""
        result = calculate_uv_index_from_solar_radiation(10000.0)
        assert result == 15.0

    def test_negative_radiation(self):
        """Test with negative solar radiation."""
        assert calculate_uv_index_from_solar_radiation(-100.0) is None


class TestCalculateSolarRadiationFromUVIndex:
    """Tests for calculate_solar_radiation_from_uv_index function."""

    def test_high_uv_index(self):
        """Test solar radiation from high UV index."""
        result = calculate_solar_radiation_from_uv_index(10.0)
        assert result is not None
        # 10 / 0.04 = 250
        assert 240.0 <= result <= 260.0

    def test_moderate_uv_index(self):
        """Test solar radiation from moderate UV index."""
        result = calculate_solar_radiation_from_uv_index(5.0)
        assert result is not None
        # 5 / 0.04 = 125
        assert 120.0 <= result <= 130.0

    def test_low_uv_index(self):
        """Test solar radiation from low UV index."""
        result = calculate_solar_radiation_from_uv_index(2.0)
        assert result is not None
        # 2 / 0.04 = 50
        assert 45.0 <= result <= 55.0

    def test_roundtrip_conversion(self):
        """Test that UV→Solar→UV conversion is consistent."""
        original_uv = 8.0
        solar = calculate_solar_radiation_from_uv_index(original_uv)
        back_to_uv = calculate_uv_index_from_solar_radiation(solar)
        assert abs(back_to_uv - original_uv) < 0.5

    def test_negative_uv(self):
        """Test with negative UV index."""
        assert calculate_solar_radiation_from_uv_index(-1.0) is None


class TestGetSnowRisk:
    """Tests for get_snow_risk function."""

    def test_no_snow_warm_temp(self):
        """Test no snow risk when temperature is too warm."""
        assert get_snow_risk(10.0, 80.0, 5.0) == "none"

    def test_high_snow_risk(self):
        """Test high snow risk with ideal conditions."""
        result = get_snow_risk(-2.0, 85.0, -2.5, precipitation_prob=70)
        assert result == "high"

    def test_medium_snow_risk(self):
        """Test medium snow risk."""
        result = get_snow_risk(1.0, 75.0, 0.0, precipitation_prob=45)
        assert result == "medium"

    def test_low_snow_risk(self):
        """Test low snow risk."""
        result = get_snow_risk(3.0, 65.0, 1.0, precipitation_prob=55)
        assert result == "low"

    def test_without_precipitation_probability(self):
        """Test snow risk without precipitation probability - should be LOW (fog/frost, not snow)."""
        result = get_snow_risk(-1.0, 85.0, -1.5)
        assert result == "low"  # High humidity at freezing = FOG/FROST without precipitation

    def test_edge_case_0_degrees(self):
        """Test snow risk at exactly 0°C."""
        result = get_snow_risk(0.0, 82.0, -0.5, precipitation_prob=65)
        assert result == "high"

    def test_user_reported_false_positive(self):
        """
        Test user-reported false positive: HIGH snow risk with low precipitation.

        Scenario: T=0°C, RH=87.15%, dewpoint_spread=1.9°C, precipitation=25%
        Expected: LOW risk (fog/frost conditions, not snow)
        Old behavior: HIGH risk (incorrect)
        New behavior: LOW risk (correct - no precipitation = no snow)
        """
        result = get_snow_risk(0.0, 87.15, -1.9, precipitation_prob=25)
        assert result == "low", "Should be LOW - high humidity without precipitation = fog/frost, not snow"

    def test_high_humidity_low_precip_no_snow(self):
        """
        Test that LOW risk is returned when atmospheric conditions show high humidity
        but precipitation probability is low - this indicates FOG/FROST, not snow.
        """
        # Ideal snow conditions except precipitation is unlikely
        result = get_snow_risk(-2.0, 85.0, -2.5, precipitation_prob=30)
        assert result == "low"  # Fog/frost conditions, not snow


class TestGetFrostRisk:
    """Tests for get_frost_risk function."""

    def test_no_frost_warm_temp(self):
        """Test no frost risk when temperature is too warm."""
        assert get_frost_risk(10.0, 5.0) == "none"

    def test_critical_frost_risk_black_ice(self):
        """Test critical frost risk (black ice conditions)."""
        result = get_frost_risk(-1.0, -1.2, wind_speed=1.0, humidity=95.0)
        assert result == "critical"

    def test_high_frost_risk(self):
        """Test high frost risk."""
        result = get_frost_risk(-5.0, -3.0, wind_speed=1.5)
        assert result == "high"

    def test_medium_frost_risk(self):
        """Test medium frost risk - WMO compliant."""
        # WMO: Both temperature AND dewpoint must be at/below 0°C
        result = get_frost_risk(-1.0, -0.5, wind_speed=2.5)
        assert result == "medium"
        
        # Edge case: dewpoint exactly at 0°C should still be medium risk
        result = get_frost_risk(-1.0, 0.0, wind_speed=2.5)
        assert result == "medium"
        
    def test_medium_frost_risk_wmo_fix(self):
        """Test that dewpoint > 0°C prevents medium frost risk (WMO fix)."""
        # OLD BEHAVIOR (incorrect): dewpoint=1°C (>0°C) → medium risk ❌
        # NEW BEHAVIOR (correct): dewpoint=1°C (>0°C) → low/none ✅
        result = get_frost_risk(-1.0, 1.0, wind_speed=2.5)
        # Should NOT be medium (dewpoint above freezing)
        assert result in ["low", "none"]

    def test_low_frost_risk(self):
        """Test low frost risk."""
        result = get_frost_risk(1.0, -0.5)
        assert result == "low"

    def test_wind_effect_on_frost(self):
        """Test that wind reduces frost risk."""
        calm = get_frost_risk(-3.0, -2.0, wind_speed=1.0)
        windy = get_frost_risk(-3.0, -2.0, wind_speed=5.0)
        # Calm conditions should have higher or equal risk
        frost_levels = ["none", "low", "medium", "high", "critical"]
        assert frost_levels.index(calm) >= frost_levels.index(windy)


class TestGetUVProtectionLevel:
    """Tests for get_uv_protection_level function."""

    def test_low_uv(self):
        """Test protection level for low UV."""
        result = get_uv_protection_level(2.0)
        assert "Low" in result
        assert "No protection" in result

    def test_moderate_uv(self):
        """Test protection level for moderate UV."""
        result = get_uv_protection_level(4.5)
        assert "Moderate" in result

    def test_high_uv(self):
        """Test protection level for high UV."""
        result = get_uv_protection_level(7.0)
        assert "High" in result

    def test_very_high_uv(self):
        """Test protection level for very high UV."""
        result = get_uv_protection_level(9.5)
        assert "Very High" in result

    def test_extreme_uv(self):
        """Test protection level for extreme UV."""
        result = get_uv_protection_level(13.0)
        assert "Extreme" in result

    def test_invalid_uv(self):
        """Test with negative UV index."""
        result = get_uv_protection_level(-1.0)
        assert result == "Invalid"


class TestEstimateSolarRadiationFromTimeAndClouds:
    """Tests for estimate_solar_radiation_from_time_and_clouds function."""

    def test_solar_noon_clear_sky(self):
        """Test solar radiation at noon with clear sky."""
        # Use June (summer month) for consistent results with location-aware calculation
        result = estimate_solar_radiation_from_time_and_clouds(
            latitude=50.0, hour=12, month=6
        )
        assert result > 500.0

    def test_nighttime(self):
        """Test that nighttime has zero solar radiation."""
        result = estimate_solar_radiation_from_time_and_clouds(
            latitude=50.0, hour=0
        )
        assert result == 0.0

    def test_morning(self):
        """Test solar radiation in morning."""
        result = estimate_solar_radiation_from_time_and_clouds(
            latitude=50.0, hour=9
        )
        assert 0.0 < result < 1000.0

    def test_evening(self):
        """Test solar radiation in evening."""
        result = estimate_solar_radiation_from_time_and_clouds(
            latitude=50.0, hour=18
        )
        assert result >= 0.0

    def test_cloud_reduction(self):
        """Test that clouds reduce solar radiation (placeholder test)."""
        # Cloud coverage sensor has been removed from the integration
        # This test now just validates the function works without cloud data
        result = estimate_solar_radiation_from_time_and_clouds(
            latitude=50.0, hour=12
        )
        assert result > 0.0

    def test_high_latitude(self):
        """Test solar radiation at high latitude."""
        mid_lat = estimate_solar_radiation_from_time_and_clouds(
            latitude=45.0, hour=12
        )
        high_lat = estimate_solar_radiation_from_time_and_clouds(
            latitude=70.0, hour=12
        )
        assert high_lat < mid_lat


class TestGetUVRiskCategory:
    """Tests for get_uv_risk_category function."""

    def test_low_category(self):
        """Test low UV risk category."""
        assert get_uv_risk_category(2.0) == "Low"

    def test_moderate_category(self):
        """Test moderate UV risk category."""
        assert get_uv_risk_category(4.5) == "Moderate"

    def test_high_category(self):
        """Test high UV risk category."""
        assert get_uv_risk_category(7.0) == "High"

    def test_very_high_category(self):
        """Test very high UV risk category."""
        assert get_uv_risk_category(9.5) == "Very High"

    def test_extreme_category(self):
        """Test extreme UV risk category."""
        assert get_uv_risk_category(12.0) == "Extreme"

    def test_boundary_values(self):
        """Test category boundaries."""
        assert get_uv_risk_category(2.9) == "Low"
        assert get_uv_risk_category(3.0) == "Moderate"
        assert get_uv_risk_category(5.9) == "Moderate"
        assert get_uv_risk_category(6.0) == "High"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

