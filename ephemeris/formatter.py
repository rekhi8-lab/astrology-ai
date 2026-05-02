SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def format_position(longitude: float) -> str:
    sign_index = int(longitude // 30)
    degree = longitude % 30

    sign = SIGNS[sign_index]
    return f"{degree:.2f}° {sign}"