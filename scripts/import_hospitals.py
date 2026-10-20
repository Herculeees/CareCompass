import csv

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


if __name__ == "__main__":
    main()
