import swisseph as swe

swe.set_ephe_path("ephemeris/sweph")

# Test date
jd = swe.julday(2025, 3, 15)

sun = swe.calc_ut(jd, swe.SUN)
saturn = swe.calc_ut(jd, swe.SATURN)

print("Sun:", sun)
print("Saturn:", saturn)