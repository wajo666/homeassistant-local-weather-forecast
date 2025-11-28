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

