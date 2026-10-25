import math
from functools import lru_cache
import re
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

def coordinates_for_city(city: str) -> tuple[float, float]:
    normalized_city = city.strip()

    if not normalized_city:
        raise ValueError("Enter a California city name.")

    pattern = rf"^{re.escape(normalized_city)}$"
    results = get_zip_lookup().query_location(pattern, top_k=1000)

    matches = results.loc[results["state_code"] == "CA"]

    coordinates = [
        (float(row.latitude), float(row.longitude))
        for row in matches.itertuples()
        if math.isfinite(float(row.latitude))
        and math.isfinite(float(row.longitude))
    ]

    if not coordinates:
        raise ValueError("No location found for this California city.")

    latitude = sum(pair[0] for pair in coordinates) / len(coordinates)
    longitude = sum(pair[1] for pair in coordinates) / len(coordinates)

    return latitude, longitude