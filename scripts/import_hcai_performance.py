"""Validate without writing by default; --write adds HCAI tables and imports one atomic snapshot.

Run from any directory with the project virtual-environment Python.
Uses .env through app.database; never stores or prints credentials.
"""

import argparse
import csv
import hashlib
import math
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import get_connection
from app.performance import MEASURES, SOURCE_URL, SOURCE_YEAR

SOURCE_FILE = ROOT / "data/raw/hcai/hospital-performance-ratings-2023.csv"
CROSSWALK_FILE = ROOT / "data/raw/health_facility_locations.csv"
MIGRATION = ROOT / "database/migrations/004_hcai_performance.sql"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def parse_number(value, integer=False):
    if not value.strip():
        return None
    number = Decimal(value)
    if not number.is_finite() or number < 0:
        raise ValueError(f"Invalid nonnegative number: {value!r}")
    if integer and number != number.to_integral_value():
        raise ValueError(f"Not an integer: {value!r}")
    return int(number) if integer else number


def distance_km(lat1, lon1, lat2, lon2):
    values = list(map(float, (lat1, lon1, lat2, lon2)))
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite coordinates")
    if not all(-90 <= v <= 90 for v in values[::2]) or not all(-180 <= v <= 180 for v in values[1::2]):
        raise ValueError("Coordinates outside geographic range")
    a, b, c, d = map(math.radians, values)
    h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1, math.sqrt(h)))


def prepare_source(rows):
    definitions = {(m["report"], m["source_measure"]): m for m in MEASURES}
    facilities = {}
    records = []
    seen = set()
    for row in rows:
        if row["Year"].strip() != str(SOURCE_YEAR):
            raise ValueError("Input must contain 2023 rows only")
        source_id = row["OSHPDID"].strip()
        if len(source_id) != 9 or not source_id.isdigit():
            raise ValueError(f"Invalid source ID: {source_id!r}")
        name = row["Hospital"].strip()
        if not name or (source_id in facilities and facilities[source_id] != name):
            raise ValueError(f"Conflicting source names for {source_id}")
        facilities[source_id] = name
        definition = definitions.get((row["Type of Report"], row["Performance Measure"]))
        if definition is None:
            continue
        key = (source_id, definition["code"])
        if key in seen:
            raise ValueError(f"Duplicate facility/measure: {key}")
        seen.add(key)
        rating = row["Hospital Ratings"].strip() or None
        if rating not in (None, "Better", "As Expected", "Worse"):
            raise ValueError(f"Unexpected rating: {rating!r}")
        cases = parse_number(row["# of Cases"], integer=True)
        events = parse_number(row["# of Adverse Events"], integer=True)
        rate = parse_number(row["Risk-adjusted Rate"])
        if cases is not None and events is not None and events > cases:
            raise ValueError(f"Events exceed cases: {key}")
        if rating is not None and (cases is None or rate is None):
            raise ValueError(f"Rated result missing numeric evidence: {key}")
        records.append({
            "source_year": SOURCE_YEAR, "oshpd_id": source_id,
            "measure_code": definition["code"], "report_type": row["Type of Report"],
            "source_measure": row["Performance Measure"], "rating": rating,
            "case_count": cases, "adverse_events": events, "source_rate": rate,
        })
    return facilities, records


def match_locations(locations, state_rows, source_rows):
    by_facid = defaultdict(list)
    by_source = defaultdict(list)
    for row in state_rows:
        by_facid[row["FACID"].strip()].append(row)
    for row in source_rows:
        by_source[row["OSHPDID"].strip()].append(row)
    matches = []
    for location in locations:
        crosswalk = by_facid.get(location["california_facid"], [])
        ids = {r["HCAI_ID"].strip() for r in crosswalk if r["HCAI_ID"].strip()}
        result = {
            "source_year": SOURCE_YEAR, "location_id": location["location_id"],
            "california_facid": location["california_facid"], "oshpd_id": None,
            "candidate_oshpd_id": None, "match_status": "no_hcai_id",
            "reason": "No unique HCAI ID in the source FACID crosswalk.",
            "location_latitude": location["latitude"], "location_longitude": location["longitude"],
            "max_source_distance_km": None,
        }
        if len(ids) == 1:
            candidate = next(iter(ids))
            result["candidate_oshpd_id"] = candidate
            source = by_source.get(candidate, [])
            if not source:
                result.update(match_status="not_in_source", reason="HCAI ID absent from the 2023 file.")
            else:
                try:
                    distances = [distance_km(location["latitude"], location["longitude"], r["Latitude"], r["Longitude"]) for r in source]
                    maximum = max(distances)
                    result["max_source_distance_km"] = maximum
                    # Conservative review trigger, not a clinical or statistical threshold.
                    if maximum > 1.0:
                        result.update(match_status="review_required", reason="Exact ID but source coordinates differ by over 1 km.")
                    else:
                        result.update(oshpd_id=candidate, match_status="matched", reason="Exact FACID-to-HCAI crosswalk; all source coordinates within 1 km.")
                except (ValueError, TypeError):
                    result.update(match_status="review_required", reason="Missing or invalid source coordinates.")
        elif len(ids) > 1:
            result.update(match_status="review_required", reason="FACID maps to multiple HCAI IDs.")
        matches.append(result)
    counts = Counter(m["oshpd_id"] for m in matches if m["match_status"] == "matched")
    for match in matches:
        if match["match_status"] == "matched" and counts[match["oshpd_id"]] > 1:
            match.update(oshpd_id=None, match_status="review_required", reason="Same HCAI facility maps to multiple search locations; campus review needed.")
    return matches


def write_snapshot(cursor, facilities, records, matches, source_hash, crosswalk_hash):
    cursor.execute(MIGRATION.read_text(encoding="utf-8"))
    # Replace only our own selected 2023 snapshot, atomically. Other data is untouched.
    cursor.execute("DELETE FROM hcai_location_matches WHERE source_year = %s", [SOURCE_YEAR])
    cursor.execute("DELETE FROM hcai_performance WHERE source_year = %s", [SOURCE_YEAR])
    cursor.executemany("""INSERT INTO hcai_facilities (source_year, oshpd_id, source_name)
        VALUES (%s, %s, %s) ON CONFLICT (source_year, oshpd_id)
        DO UPDATE SET source_name = EXCLUDED.source_name""",
        [(SOURCE_YEAR, source_id, name) for source_id, name in facilities.items()])
    cursor.executemany("""INSERT INTO hcai_performance (
        source_year, oshpd_id, measure_code, report_type, source_measure, rating,
        case_count, adverse_events, source_rate, source_url, source_sha256
    ) VALUES (%(source_year)s, %(oshpd_id)s, %(measure_code)s, %(report_type)s,
        %(source_measure)s, %(rating)s, %(case_count)s, %(adverse_events)s,
        %(source_rate)s, %(source_url)s, %(source_sha256)s)""",
        [dict(record, source_url=SOURCE_URL, source_sha256=source_hash) for record in records])
    cursor.executemany("""INSERT INTO hcai_location_matches (
        source_year, location_id, california_facid, oshpd_id, candidate_oshpd_id,
        match_status, reason, location_latitude, location_longitude,
        max_source_distance_km, crosswalk_sha256
    ) VALUES (%(source_year)s, %(location_id)s, %(california_facid)s, %(oshpd_id)s,
        %(candidate_oshpd_id)s, %(match_status)s, %(reason)s, %(location_latitude)s,
        %(location_longitude)s, %(max_source_distance_km)s, %(crosswalk_sha256)s)""",
        [dict(match, crosswalk_sha256=crosswalk_hash) for match in matches])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Apply migration and import in one transaction.")
    args = parser.parse_args()
    source_rows = read_csv(SOURCE_FILE)
    facilities, records = prepare_source(source_rows)
    state_rows = read_csv(CROSSWALK_FILE)
    from psycopg.rows import dict_row
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM hospital_search ORDER BY location_id")
            locations = cursor.fetchall()
            matches = match_locations(locations, state_rows, source_rows)
            if args.write:
                write_snapshot(cursor, facilities, records, matches,
                    hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest(),
                    hashlib.sha256(CROSSWALK_FILE.read_bytes()).hexdigest())
    print("Source facilities:", len(facilities))
    print("Prepared performance records:", len(records))
    print("Search locations checked:", len(matches))
    print("Import committed." if args.write else "Dry run: database unchanged.")



if __name__ == "__main__":
    main()
