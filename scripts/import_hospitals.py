import csv
import math
from datetime import datetime
from pprint import pprint

from inspect_hospital import CMS_FILE, CALIFORNIA_FILE
from generate_issue_report import addresses_match, zips_match


def read_california_hospitals() -> list[dict[str, str]]:
    hospitals = []

    with CMS_FILE.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for hospital in reader:
            if hospital["State"].strip() == "CA":
                hospitals.append(hospital)

    return hospitals


def parse_rating(value: str) -> int | None:
    cleaned_value = value.strip()

    if cleaned_value in ("", "Not Available"):
        return None

    rating = int(cleaned_value)

    if not 1 <= rating <= 5:
        raise ValueError(f"Invalid hospital rating: {value!r}")

    return rating


def parse_emergency_services(value: str) -> bool | None:
    cleaned_value = value.strip().lower()

    if cleaned_value == "yes":
        return True

    if cleaned_value == "no":
        return False

    if cleaned_value in ("", "not available"):
        return None

    raise ValueError(f"Unexpected emergency-services value: {value!r}")


def read_location_candidates() -> dict[str, list[dict[str, str]]]:
    candidates_by_ccn = {}

    with CALIFORNIA_FILE.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for facility in reader:
            ccn = facility["CCN"].strip()

            if not ccn:
                continue

            if ccn not in candidates_by_ccn:
                candidates_by_ccn[ccn] = []

            candidates_by_ccn[ccn].append(facility)

    return candidates_by_ccn


def find_address_matches(
    hospital: dict[str, str],
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    matches = []

    for candidate in candidates:
        if addresses_match(hospital, candidate) and zips_match(
            hospital, candidate
        ):
            matches.append(candidate)

    return matches

def parse_coordinates(
    latitude_text: str,
    longitude_text: str,
) -> tuple[float, float] | None:
    latitude_text = latitude_text.strip()
    longitude_text = longitude_text.strip()

    if not latitude_text or not longitude_text:
        return None

    try:
        latitude = float(latitude_text)
        longitude = float(longitude_text)
    except ValueError:
        return None

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None

    if not -90 <= latitude <= 90:
        return None

    if not -180 <= longitude <= 180:
        return None

    if latitude == 0 and longitude == 0:
        return None

    return latitude, longitude

def parse_source_date(value: str):
    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    return datetime.strptime(cleaned_value, "%m/%d/%Y").date()

def prepare_hospital(
    hospital: dict[str, str],
    candidates: list[dict[str, str]],
) -> dict:
    record = {
        "cms_facility_id": hospital["Facility ID"].strip(),
        "name": hospital["Facility Name"].strip(),
        "hospital_type": hospital["Hospital Type"].strip() or None,
        "phone": hospital["Telephone Number"].strip() or None,
        "cms_address": hospital["Address"].strip() or None,
        "cms_city": hospital["City/Town"].strip() or None,
        "cms_state": hospital["State"].strip(),
        "cms_zip": hospital["ZIP Code"].strip() or None,
        "overall_rating": parse_rating(hospital["Hospital overall rating"]),
        "rating_footnote": (hospital["Hospital overall rating footnote"].strip() or None),
        "emergency_services": parse_emergency_services(hospital["Emergency Services"]),
        "california_facid": None,
        "california_address": None,
        "california_city": None,
        "california_zip": None,
        "latitude": None,
        "longitude": None,
        "california_data_date": None,
        "location_match_status": "review_required",
    }

    if not candidates:
        record["location_match_status"] = "no_id_match"
        return record

    matches = find_address_matches(hospital, candidates)

    if len(matches) != 1:
        return record

    candidate = matches[0]
    coordinates = parse_coordinates(
        candidate["LATITUDE"],
        candidate["LONGITUDE"],
    )

    if coordinates is None:
        return record

    record["california_facid"] = candidate["FACID"].strip()
    record["california_address"] = candidate["ADDRESS"].strip()
    record["california_city"] = candidate["CITY"].strip()
    record["california_zip"] = candidate["ZIP"].strip()
    record["latitude"] = coordinates[0]
    record["longitude"] = coordinates[1]
    record["location_match_status"] = "single_candidate"

    return record

def main() -> None:
    hospitals = read_california_hospitals()

    print("California hospitals found:", len(hospitals))

    for hospital in hospitals[:3]:
        rating = parse_rating(hospital["Hospital overall rating"])
        emergency = parse_emergency_services(
            hospital["Emergency Services"]
        )

        print(
            hospital["Facility ID"],
            hospital["Facility Name"],
            "Rating:", rating,
            "Emergency services:", emergency,
        )

    missing_ratings = 0
    emergency_yes = 0
    emergency_no = 0
    emergency_unknown = 0

    for hospital in hospitals:
        rating = parse_rating(hospital["Hospital overall rating"])
        emergency = parse_emergency_services(
            hospital["Emergency Services"]
        )

        if rating is None:
            missing_ratings += 1

        if emergency is True:
            emergency_yes += 1
        elif emergency is False:
            emergency_no += 1
        else:
            emergency_unknown += 1

    print("\nValidation summary:")
    print("Hospitals checked:", len(hospitals))
    print("Missing ratings:", missing_ratings)
    print("Emergency services — Yes:", emergency_yes)
    print("Emergency services — No:", emergency_no)
    print("Emergency services — Unknown:", emergency_unknown)

    candidates_by_ccn = read_location_candidates()

    print(
        "\nLocation candidates for 050007:",
        len(candidates_by_ccn.get("050007", [])),
    )

    hospital = hospitals[0]
    facility_id = hospital["Facility ID"]

    candidates = candidates_by_ccn.get(facility_id, [])
    matches = find_address_matches(hospital, candidates)

    print(
        "Address-and-ZIP matches for",
        facility_id,
        ":",
        len(matches),
    )

    if len(matches) == 1:
        candidate = matches[0]

        coordinates = parse_coordinates(
            candidate["LATITUDE"],
            candidate["LONGITUDE"],
        )

        print("Candidate coordinates:", coordinates)

    prepared = prepare_hospital(hospital, candidates)
    pprint(prepared)


if __name__ == "__main__":
    main()
