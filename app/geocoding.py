import math
from functools import lru_cache

import pgeocode


@lru_cache(maxsize=1)
def get_zip_lookup():
    return pgeocode.Nominatim("us")


def coordinates_for_zip(zip_code: str) -> tuple[float, float]:
    normalized_zip = zip_code.strip()

    if len(normalized_zip) != 5 or not normalized_zip.isascii() or not normalized_zip.isdigit():
        raise ValueError("Enter a five-digit ZIP code.")

    result = get_zip_lookup().query_postal_code(normalized_zip)

    latitude = float(result.latitude)
    longitude = float(result.longitude)

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Coordinates are unavailable for this ZIP code.")

    return latitude, longitude