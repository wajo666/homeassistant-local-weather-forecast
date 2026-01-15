"""Forecast text data for all supported languages."""

# Conditions: [German, English, Greek, Italian, Slovak]
CONDITIONS = [
    ("stürmisch", "Stormy", "θυελλώδης", "Tempestoso", "búrlivý"),
    ("regnerisch", "Rainy", "Βροχερός", "Piovoso", "daždivý"),
    ("wechselhaft", "Mixed", "Μεταβλητός", "Variabile", "premenlivý"),
    ("sonnig", "Sunny", "Ηλιόλουστος", "Soleggiato", "slnečný"),
    ("sehr trocken", "Extra Dry", "Πολύ ξηρός", "Molto Secco", "veľmi sucho"),
]

# Pressure systems: [German, English, Greek, Italian, Slovak]
PRESSURE_SYSTEMS = [
    ("Tiefdruckgebiet", "Low Pressure System", "σύστημα χαμηλής πίεσης", "Bassa Pressione", "Nízky tlak"),
    ("Normal", "Normal", "φυσιολογικός", "Normale", "Normálny"),
    ("Hochdruckgebiet", "High Pressure System", "σύστημα υψηλής πίεσης", "Zona Alta Pressione", "Vysoký tlak"),
]

# Forecast texts for Zambretti algorithm: [German, English, Greek, Italian, Slovak]
FORECAST_TEXTS = [
    ("Beständiges Schönwetter!", "Settled Fine", "Σταθερός καλός καιρός!", "Bel tempo stabile", "Stabilne pekné počasie!"),
    ("Schönes Wetter!", "Fine", "Ωραίος καιρός!", "Bello", "Pekné počasie!"),
    ("Es wird schöner.", "Becoming Fine", "Θα καλυτερεύσει.", "Miglioramento", "Zlepšuje sa."),
    ("Schön, wird wechselhaft.", "Fine, Becoming Less Settled", "Μεταβλητός.", "Bello, diventa variabile", "Pekné, stáva sa premenlivé."),
    ("Schön, Regenschauer möglich.", "Fine, Possibly showers", "Πιθανή βροχή.", "Bello, possibili rovesci", "Pekné, možné prehánky."),
    ("Heiter bis wolkig, Besserung zu erwarten.", "Fairly Fine, Improving", "Αίθριος έως νεφελώδης, αναμένεται βελτίωση.", "Abbastanza bello, in miglioramento", "Polooblačno, očakáva sa zlepšenie."),
    ("Heiter bis wolkig, anfangs evtl. Schauer.", "Fairly Fine, Possibly Showers, Early", "Αίθριος έως συννεφιασμένος, πιθανώς βροχές στην αρχή.", "Abbastanza bello, possibili rovesci iniziali", "Polooblačno, na začiatku možné prehánky."),
    ("Heiter bis wolkig, später Regen.", "Fairly Fine, Showery Later", "Αίθριος έως συννεφιασμένος, αργότερα βροχή.", "Abbastanza bello, rovesci più tardi", "Polooblačno, neskôr dážď."),
    ("Anfangs noch Schauer, dann Besserung.", "Showery Early, Improving", "Βροχόπτωση στην αρχή και μετά βελτίωση.", "Rovesci iniziali, poi miglioramento", "Spočiatku prehánky, potom zlepšenie."),
    ("Wechselhaft mit Schauern", "Changeable, Mending", "Εναλλαγή με βροχόπτωση.", "Variabile con rovesci", "Premenlivé s prehánkami"),
    ("Heiter bis wolkig, vereinzelt Regen.", "Fairly Fine, Showers Likely", "Αίθριος έως συννεφιασμένος, κατά διαστήματα βροχή.", "Abbastanza bello, rovesci probabili", "Polooblačno, miestami dážď."),
    ("Unbeständig, später Aufklarung.", "Rather Unsettled, Clearing Later", "Ασταθής, αργότερα καθάρος.", "Piuttosto instabile, schiarite più tardi", "Nestále, neskôr sa vyjasní."),
    ("Unbeständig, evtl. Besserung.", "Unsettled, Probably Improving", "Ασταθής, πιθανώς βελτίωση.", "Instabile, probabilmente in miglioramento", "Nestále, pravdepodobne sa zlepší."),
    ("Regnerisch mit heiteren Phasen.", "Showery, Bright Intervals", "Καθαρός με διαστήματα βροχής.", "Rovesci con schiarite", "Prehánky s jasnými obdobiami."),
    ("Regnerisch, wird unbeständiger.", "Showery, Becoming More Unsettled", "Βροχερό, όλο και πιο ασταθές.", "Rovesci, diventa più instabile", "Prehánky, stáva sa nestálejšie."),
    ("Wechselhaft mit etwas Regen.", "Changeable, Some Rain", "Αλλάζει με λίγη βροχή.", "Variabile con qualche pioggia", "Premenlivé s občasným dažďom."),
    ("Unbeständig mit heiteren Phasen.", "Unsettled, Short Fine Intervals", "Άστατα, μικρά καθαρά διαστήματα", "Instabile con brevi schiarite", "Nestále s krátkymi jasnými intervalmi."),
    ("Unbeständig, später Regen.", "Unsettled, Rain Later", "Άστατη, αργότερα βροχή.", "Instabile, pioggia più tardi", "Nestále, neskôr dážď."),
    ("Unbeständig mit etwas Regen.", "Unsettled, Rain At Times", "Άστατος με λίγη βροχή.", "Instabile con piogge a tratti", "Nestále s občasným dažďom."),
    ("Wechselhaft und regnerisch", "Very Unsettled, Finer At Times", "Μεταβλητός και βροχερός.", "Molto instabile, a tratti migliore", "Veľmi premenlivé a daždivé"),
    ("Gelegentlich Regen, Verschlechterung.", "Rain At Times, Worse Later", "Περιστασιακές βροχές, επιδείνωση.", "Piogge a tratti, peggiora più tardi", "Občasný dážď, neskôr zhoršenie."),
    ("Zuweilen Regen, sehr unbeständig.", "Rain At Times, Becoming Very Unsettled", "Βροχή κατά περιόδους, πολύ ασταθής.", "Piogge a tratti, diventa molto instabile", "Občasný dážď, veľmi nestále."),
    ("Häufiger Regen.", "Rain At Frequent Intervals", "Συχνή βροχή.", "Piogge frequenti", "Častý dážď."),
    ("Regen, sehr unbeständig.", "Very Unsettled, Rain", "Βροχή, πολύ ασταθής.", "Molto instabile, pioggia", "Dážď, veľmi nestále."),
    ("Stürmisch, evtl. Besserung.", "Stormy, Possibly Improving", "Θυελλώδης, πιθανώς βελτίωση.", "Tempestoso, possibile miglioramento", "Búrlivé, možné zlepšenie."),
    ("Stürmisch mit viel Regen.", "Stormy, Much Rain", "Καταιγίδα με πολλές βροχές.", "Tempestoso con molta pioggia", "Búrlivé s veľa dažďom."),
]

# Zambretti letter codes
ZAMBRETTI_LETTERS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"
]

# Beaufort wind types (0-12): [German, English, Greek, Italian, Slovak]
WIND_TYPES = [
    ("Windstille", "Calm", "Νηνεμία", "Calmo", "Ticho"),                                      # 0
    ("Leiser Zug", "Light air", "Ελαφρύ αεράκι", "Bava di vento", "Slabý vánok"),          # 1
    ("Leichte Brise", "Light breeze", "Αεράκι", "Brezza leggera", "Vánok"),                # 2
    ("Schwache Brise", "Gentle breeze", "Απαλή αύρα", "Brezza tesa", "Slabý vietor"),      # 3
    ("Mäßige Brise", "Moderate breeze", "Σχεδόν μέτρια αύρα", "Vento moderato", "Mierny vietor"),  # 4
    ("Frische Brise", "Fresh breeze", "Μέτρια αύρα", "Vento teso", "Čerstvý vietor"),      # 5
    ("Starker Wind", "Strong breeze", "Δυνατή αύρα", "Vento fresco", "Silný vietor"),      # 6
    ("Steifer Wind", "High wind", "Σχεδόν θύελλα", "Vento forte", "Prudký vietor"),        # 7
    ("Stürmischer Wind", "Gale", "Θύελλα", "Burrasca", "Búrka"),                           # 8
    ("Sturm", "Strong gale", "Δυνατή θύελλα", "Burrasca forte", "Silná búrka"),           # 9
    ("Schwerer Sturm", "Storm", "Καταιγίδα", "Tempesta", "Veľká búrka"),                  # 10
    ("Orkanartiger Sturm", "Violent storm", "Σφοδρή καταιγίδα", "Tempesta violenta", "Orkán"),  # 11
    ("Orkan", "Hurricane", "Τυφώνας", "Uragano", "Hurikán"),                               # 12
]

# Visibility estimates based on fog risk: [German, English, Greek, Italian, Slovak]
VISIBILITY_ESTIMATES = {
    "high": ("Reduzierte Sicht (<1 km)", "Reduced visibility (<1 km)", "Μειωμένη ορατότητα (<1 km)", "Visibilità ridotta (<1 km)", "Znížená viditeľnosť (<1 km)"),
    "medium": ("Möglicherweise reduzierte Sicht (1-5 km)", "Possibly reduced visibility (1-5 km)", "Πιθανώς μειωμένη ορατότητα (1-5 km)", "Possibile visibilità ridotta (1-5 km)", "Možná znížená viditeľnosť (1-5 km)"),
    "low": ("Gute Sicht (5-10 km)", "Good visibility (5-10 km)", "Καλή ορατότητα (5-10 km)", "Buona visibilità (5-10 km)", "Dobrá viditeľnosť (5-10 km)"),
    "none": ("Sehr gute Sicht (>10 km)", "Very good visibility (>10 km)", "Πολύ καλή ορατότητα (>10 km)", "Visibilità molto buona (>10 km)", "Veľmi dobrá viditeľnosť (>10 km)"),
}

# Comfort levels (for UI display): [German, English, Greek, Italian, Slovak]
COMFORT_LEVELS = {
    "very_cold": ("Sehr kalt", "Very cold", "Πολύ κρύο", "Molto freddo", "Veľmi chladno"),
    "cold": ("Kalt", "Cold", "Κρύο", "Freddo", "Chladno"),
    "cool": ("Kühl", "Cool", "Δροσερό", "Fresco", "Chladnejšie"),
    "comfortable": ("Angenehm", "Comfortable", "Άνετο", "Confortevole", "Príjemne"),
    "warm": ("Warm", "Warm", "Ζεστό", "Caldo", "Teplo"),
    "hot": ("Heiß", "Hot", "Καυτό", "Molto caldo", "Horúco"),
    "very_hot": ("Sehr heiß", "Very hot", "Πολύ καυτό", "Caldissimo", "Veľmi horúco"),
}

# Fog risk levels (for UI display): [German, English, Greek, Italian, Slovak]
FOG_RISK_LEVELS = {
    "none": ("Kein Nebel", "No fog", "Χωρίς ομίχλη", "Nessuna nebbia", "Žiadna hmla"),
    "low": ("Niedriges Nebelrisiko", "Low fog risk", "Χαμηλός κίνδυνος ομίχλης", "Basso rischio nebbia", "Nízke riziko hmly"),
    "medium": ("Mittleres Nebelrisiko", "Medium fog risk", "Μέτριος κίνδυνος ομίχλης", "Medio rischio nebbia", "Stredné riziko hmly"),
    "high": ("Hohes Nebelrisiko", "High fog risk", "Υψηλός κίνδυνος ομίχλης", "Alto rischio nebbia", "Vysoké riziko hmly"),
    "critical": ("Kritisches Nebelrisiko", "Critical fog risk", "Κρίσιμος κίνδυνος ομίχλης", "Rischio nebbia critico", "Kritické riziko hmly"),
}

# Atmosphere stability levels (for UI display): [German, English, Greek, Italian, Slovak]
ATMOSPHERE_STABILITY = {
    "stable": ("Stabil", "Stable", "Σταθερή", "Stabile", "Stabilná"),
    "moderate": ("Mäßig", "Moderate", "Μέτρια", "Moderata", "Mierne nestabilná"),
    "unstable": ("Instabil", "Unstable", "Ασταθής", "Instabile", "Nestabilná"),
    "very_unstable": ("Sehr instabil", "Very unstable", "Πολύ ασταθής", "Molto instabile", "Veľmi nestabilná"),
    "unknown": ("Unbekannt", "Unknown", "Άγνωστο", "Sconosciuto", "Neznáma"),
}

# Adjustment detail text templates: [German, English, Greek, Italian, Slovak]
# Use {value} placeholder for dynamic values
ADJUSTMENT_TEMPLATES = {
    "high_humidity": ("Hohe Luftfeuchtigkeit ({value}%)", "High humidity ({value}%)", "Υψηλή υγρασία ({value}%)", "Alta umidità ({value}%)", "Vysoká vlhkosť ({value}%)"),
    "low_humidity": ("Niedrige Luftfeuchtigkeit ({value}%)", "Low humidity ({value}%)", "Χαμηλή υγρασία ({value}%)", "Bassa umidità ({value}%)", "Nízka vlhkosť ({value}%)"),
    "high_fog_risk": ("Hohes Nebelrisiko (Spread {value}°C)", "High fog risk (spread {value}°C)", "Υψηλός κίνδυνος ομίχλης (διαφορά {value}°C)", "Alto rischio nebbia (differenza {value}°C)", "Vysoké riziko hmly (spread {value}°C)"),
    "medium_fog_risk": ("Mittleres Nebelrisiko (Spread {value}°C)", "Medium fog risk (spread {value}°C)", "Μέτριος κίνδυνος ομίχλης (διαφορά {value}°C)", "Medio rischio nebbia (differenza {value}°C)", "Stredné riziko hmly (spread {value}°C)"),
    "low_fog_risk": ("Niedriges Nebelrisiko (Spread {value}°C)", "Low fog risk (spread {value}°C)", "Χαμηλός κίνδυνος ομίχλης (διαφορά {value}°C)", "Basso rischio nebbia (differenza {value}°C)", "Nízke riziko hmly (spread {value}°C)"),
    "very_unstable": ("Sehr instabile Atmosphäre (Böenverhältnis {value})", "Very unstable atmosphere (gust ratio {value})", "Πολύ ασταθής ατμόσφαιρα (αναλογία ριπών {value})", "Atmosfera molto instabile (rapporto raffiche {value})", "Veľmi nestabilná atmosféra (gust ratio {value})"),
    "unstable": ("Instabile Atmosphäre (Böenverhältnis {value})", "Unstable atmosphere (gust ratio {value})", "Ασταθής ατμόσφαιρα (αναλογία ριπών {value})", "Atmosfera instabile (rapporto raffiche {value})", "Nestabilná atmosféra (gust ratio {value})"),
}

