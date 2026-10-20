"""Generate a review CSV, excluding hospitals with one address-and-ZIP match."""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from inspect_hospital import CALIFORNIA_FILE, CMS_FILE, PROJECT_FOLDER, normalize_address


REPORT_COLUMNS = [
    "cms_facility_id", "cms_hospital_name", "issue_type",
    "candidate_california_facid", "decision", "reason",
    "verification_source", "review_date",
    "cms_address", "cms_city", "cms_zip",
    "candidate_name", "candidate_address", "candidate_city", "candidate_zip",
    "candidate_facility_type", "candidate_main_facility_flag",
    "candidate_latitude", "candidate_longitude",
    "normalized_address_matches", "zip_matches",
]


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    """Read text values so leading zeros in identifiers remain intact."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)
        for number, row in enumerate(rows, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path.name}: malformed CSV record near row {number}")
        return rows


def addresses_match(hospital: dict[str, str], candidate: dict[str, str]) -> bool:
    address = normalize_address(hospital["Address"])
    return bool(address) and address == normalize_address(candidate["ADDRESS"])


def zips_match(hospital: dict[str, str], candidate: dict[str, str]) -> bool:
    zip_code = hospital["ZIP Code"].strip()[:5]
    return bool(zip_code) and zip_code == candidate["ZIP"].strip()[:5]


def build_issue_rows(hospitals, facilities):
    """Return candidate-level report rows and hospital-level status counts.

    Multiple report rows can belong to one hospital. All same-ID candidates are
    included for unresolved hospitals; no candidate is automatically approved.
    """
    by_ccn = defaultdict(list)
    for facility in facilities:
        ccn = facility["CCN"].strip()
        if ccn:
            by_ccn[ccn].append(facility)

    report_rows = []
    counts = Counter()

    for hospital in hospitals:
        if hospital["State"].strip() != "CA":
            continue

        candidates = by_ccn[hospital["Facility ID"].strip()]
        address_matches = [row for row in candidates if addresses_match(hospital, row)]
        full_matches = [row for row in address_matches if zips_match(hospital, row)]

        if len(full_matches) == 1:
            counts["ONE_MATCH_EXCLUDED"] += 1
            continue
        if not candidates:
            issue = "NO_ID_MATCH"
            reason = "No exact CCN match; name/address discovery and verification needed."
        elif not address_matches:
            issue = "ADDRESS_MISMATCH"
            reason = "CCN matches, but no candidate has the same normalized street address."
        elif not full_matches:
            issue = "ZIP_MISMATCH"
            reason = "Street address matches, but no address-matching candidate has the same ZIP."
        else:
            issue = "MULTIPLE_MATCHES"
            reason = "Multiple rows match street address and ZIP; review facility details and coordinates."

        counts[issue] += 1
        # One blank-candidate row retains hospitals with no exact ID match.
        for candidate in candidates or [{}]:
            report_rows.append({
                "cms_facility_id": hospital["Facility ID"],
                "cms_hospital_name": hospital["Facility Name"],
                "issue_type": issue,
                "candidate_california_facid": candidate.get("FACID", ""),
                "decision": "pending",
                "reason": reason,
                "verification_source": "",
                "review_date": "",
                "cms_address": hospital["Address"],
                "cms_city": hospital["City/Town"],
                "cms_zip": hospital["ZIP Code"],
                "candidate_name": candidate.get("FACNAME", ""),
                "candidate_address": candidate.get("ADDRESS", ""),
                "candidate_city": candidate.get("CITY", ""),
                "candidate_zip": candidate.get("ZIP", ""),
                "candidate_facility_type": candidate.get("FAC_TYPE_CODE", ""),
                "candidate_main_facility_flag": candidate.get("ISFACMAIN", ""),
                "candidate_latitude": candidate.get("LATITUDE", ""),
                "candidate_longitude": candidate.get("LONGITUDE", ""),
                "normalized_address_matches": str(addresses_match(hospital, candidate)) if candidate else "",
                "zip_matches": str(zips_match(hospital, candidate)) if candidate else "",
            })

    return report_rows, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cms-file", type=Path, default=CMS_FILE)
    parser.add_argument("--california-file", type=Path, default=CALIFORNIA_FILE)
    parser.add_argument("--output", type=Path, help="New CSV path; existing files are never overwritten.")
    args = parser.parse_args()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output = args.output or PROJECT_FOLDER / "reports" / f"hospital-issues-{timestamp}.csv"

    try:
        hospitals = read_csv(args.cms_file, {
            "Facility ID", "Facility Name", "State", "Address", "City/Town", "ZIP Code",
        })
        facilities = read_csv(args.california_file, {
            "CCN", "FACID", "FACNAME", "ADDRESS", "CITY", "ZIP",
            "FAC_TYPE_CODE", "ISFACMAIN", "LATITUDE", "LONGITUDE",
        })
        rows, counts = build_issue_rows(hospitals, facilities)
        if not counts:
            raise ValueError("No California CMS hospitals found; check the input file.")

        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=REPORT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}")
        return 2

    print(f"California CMS hospitals checked: {sum(counts.values())}")
    print(f"Single address-and-ZIP matches excluded: {counts['ONE_MATCH_EXCLUDED']}")
    for issue in ["MULTIPLE_MATCHES", "ZIP_MISMATCH", "ADDRESS_MISMATCH", "NO_ID_MATCH"]:
        print(f"{issue}: {counts[issue]}")
    print(f"Hospitals needing review: {sum(counts.values()) - counts['ONE_MATCH_EXCLUDED']}")
    print(f"Report rows (one per candidate, or one blank candidate): {len(rows)}")
    print(f"Report: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
