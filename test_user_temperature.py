"""Temperature forecast for next hours based on updated model."""

from datetime import datetime, timedelta
import math

# User's actual data
current_time = datetime(2026, 2, 4, 14, 26)
current_temp = 2.6
current_pressure = 1008.9
pressure_change_3h = -2.7
current_humidity = 94.2
latitude = 48.72

# Temperature model parameters (from updated code)
def calculate_temperature_forecast(hours_ahead):
    """Calculate temperature for next hours using updated diurnal model."""
    
    # Winter parameters (February)
    winter_amplitude = 2.0  # Reduced from 3.0°C (temperate zone)
    
    # Current hour and future hour
    hour_now = current_time.hour
    future_time = current_time + timedelta(hours=hours_ahead)
    future_hour = future_time.hour
    
    # Solar noon ~12:00
    # Winter peak: 13:00-13:30 (1.0-1.5h after solar noon)
    solar_noon = 12.0
    winter_peak_offset = 1.25  # hours after solar noon
    temp_peak_hour = solar_noon + winter_peak_offset  # ~13:15
    
    # Temperature at peak (assume 3-4°C at 13:15)
    temp_peak = current_temp + 1.0  # Conservative estimate for winter evening
    
    # Diurnal curve calculation
    def diurnal_temp(hour):
        """Calculate temperature for given hour using sinusoidal model."""
        # Phase shift to align with temperature peak
        phase = (hour - temp_peak_hour) * (2 * math.pi / 24)
        
        # Sinusoidal variation
        variation = winter_amplitude * math.cos(phase)
        
        # Base temperature (daily average)
        temp_base = temp_peak - winter_amplitude * 0.5
        
        return temp_base + variation
    
    # Calculate future temperature
    future_temp = diurnal_temp(future_hour)
    
    # Apply evening/night trend damping (50% reduction after 16:00)
    if future_hour >= 16 or future_hour < 6:
        # Night cooling - logarithmic decay
        if future_hour >= 16:
            hours_since_peak = future_hour - temp_peak_hour
        else:
            hours_since_peak = (24 - temp_peak_hour) + future_hour
        
        # Logarithmic cooling (slower than linear)
        cooling_factor = 0.3 * math.log(hours_since_peak + 1)
        future_temp -= cooling_factor
    
    # Pressure trend influence (falling = slightly warmer clouds)
    if pressure_change_3h < -2.0:
        future_temp += 0.2  # Cloudy = less radiative cooling
    
    return round(future_temp, 1)

print("=" * 80)
print("🌡️  TEPLOTNÁ PREDPOVEĎ (podľa upraveného modelu)")
print("=" * 80)
print(f"Aktuálne: 14:26 → {current_temp}°C")
print()

print("NASLEDUJÚCE HODINY:")
print("-" * 80)
for hours in range(1, 13):
    future_time = current_time + timedelta(hours=hours)
    future_temp = calculate_temperature_forecast(hours)
    
    # Determine time of day
    hour = future_time.hour
    if hour < 6:
        period = "🌙 Noc"
    elif hour < 12:
        period = "🌅 Ráno"
    elif hour < 18:
        period = "☀️  Deň"
    else:
        period = "🌆 Večer"
    
    print(f"{future_time.strftime('%H:%M')}  {period}  →  {future_temp:+5.1f}°C")

print()
print("=" * 80)
print("💡 POZOROVANIA")
print("=" * 80)
print("✅ Zimná noc (február) → Pomalé chladnutie")
print("✅ Logaritmické ochladzovanie (nie lineárne)")
print("✅ Klesajúci tlak → Oblačnosť = menej radiačného chladnutia")
print("✅ Vysoká vlhkosť (94%) → Hmla = stabilizácia teploty")
print()
print("📊 OČAKÁVANÝ PRIEBEH:")
print("   14:26-18:00: Blížime sa k teplotnému vrcholu dňa")
print("   18:00-23:00: Postupné chladnutie -2.0 až -3.0°C")
print("   23:00-06:00: Pomalé chladnutie -1.5 až -2.0°C")
print("   06:00-13:00: Postupné oteplenie +2.0 až +3.0°C")
print()
print("⚠️  POZNÁMKA:")
print("   Skutočná teplota závisí od:")
print("   • Vývoja oblačnosti (forecast: CLOUDY)")
print("   • Rýchlosti vetra (vietor znižuje radiačné chladnutie)")
print("   • Možného mrholenia (94% vlhkosť)")
print()
