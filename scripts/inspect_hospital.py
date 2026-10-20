import argparse
import csv
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
RAW_DATA_FOLDER = PROJECT_FOLDER / "data" / "raw"
CMS_FILE = RAW_DATA_FOLDER / "Hospital_General_Information.csv"
CALIFORNIA_FILE = RAW_DATA_FOLDER / "health_facility_locations.csv"


def normalize_address(address: str) -> str:
    """Standardize address text for comparison, not location verification."""
    abbreviations = {
        # Street types
        "AVENUE": "AVE",
        "STREET": "ST",
        "BOULEVARD": "BLVD",
        "DRIVE": "DR",
        "ROAD": "RD",
        "LANE": "LN",
        "COURT": "CT",
        "PARKWAY": "PKWY",
        "HIGHWAY": "HWY",
        "EXPRESSWAY": "EXPY",
        "PLACE": "PL",
        "TERRACE": "TER",
        "CIRCLE": "CIR",

        # Directions
        "NORTH": "N",
        "SOUTH": "S",
        "EAST": "E",
        "WEST": "W",
        "NORTHEAST": "NE",
        "NORTHWEST": "NW",
        "SOUTHEAST": "SE",
        "SOUTHWEST": "SW",
    }

    words = address.upper().split()
    normalized_words = []

    for word in words:
        cleaned_word = word.strip(".,")

        if cleaned_word:
            normalized_word = abbreviations.get(
                cleaned_word, cleaned_word
            )
            normalized_words.append(normalized_word)

    return " ".join(normalized_words)


def find_cms_hospital(facility_id: str) -> dict[str, str] | None:
    """Return the CMS row for an ID, or None when it is not found."""
    with CMS_FILE.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for hospital in reader:
            if hospital["Facility ID"].strip() == facility_id.strip():
                return hospital

    return None


def find_location_candidates(facility_id: str) -> list[dict[str, str]]:
    """Return every California row with the same CCN, without selecting a location."""
    candidates = []

    with CALIFORNIA_FILE.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for facility in reader:
            ccn = facility["CCN"].strip()
            if ccn and ccn == facility_id.strip():
                candidates.append(facility)

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a CMS hospital and its California location candidates."
    )
    parser.add_argument(
        "facility_id",
        nargs="?",
        default="050002",
        help="CMS facility ID, including leading zeros (default: 050002).",
    )
    args = parser.parse_args()

    hospital = find_cms_hospital(args.facility_id)
    if hospital is None:
        print(f"CMS hospital not found for ID {args.facility_id!r}.")
        return

    print("ID:", hospital["Facility ID"])
    print("Name:", hospital["Facility Name"])
    print("Address:", hospital["Address"])
    print("Rating:", hospital["Hospital overall rating"])
    print("Emergency services:", hospital["Emergency Services"])

    candidates = find_location_candidates(hospital["Facility ID"])
    print(f"\nCalifornia location candidates: {len(candidates)}")

    if not candidates:
        print("No exact CCN match. Coordinates remain unverified.")
    elif len(candidates) == 1:
        print("One candidate. Verify its address before using the coordinates.")
    else:
        print("Multiple candidates. Review the addresses; no location is selected.")

    for number, facility in enumerate(candidates, start=1):
        print(f"\nCandidate {number}:")
        print("CCN:", facility["CCN"])
        print("Name:", facility["FACNAME"])
        print("Address:", facility["ADDRESS"])
        print("City:", facility["CITY"])
        print("ZIP:", facility["ZIP"])
        print("Facility type:", facility["FAC_TYPE_CODE"])
        print("Main facility flag:", facility["ISFACMAIN"])
        print("Latitude:", facility["LATITUDE"] or "Not available")
        print("Longitude:", facility["LONGITUDE"] or "Not available")


if __name__ == "__main__":
    main()
