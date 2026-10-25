"""Definitions shared by the HCAI importer and API; no synthetic quality scores."""

SOURCE_URL = "https://hcai.ca.gov/visualizations/hospital-performance-ratings-summary-report/"
SOURCE_YEAR = 2023
MEASURES = (
    {"code": "heart_attack", "category": "Heart", "label": "Heart-attack mortality", "report": "IMI", "source_measure": "AMI"},
    {"code": "heart_failure", "category": "Heart", "label": "Heart-failure mortality", "report": "IMI", "source_measure": "Heart Failure"},
    {"code": "pneumonia", "category": "Lungs", "label": "Pneumonia mortality", "report": "IMI", "source_measure": "Pneumonia"},
    {"code": "hip_fracture", "category": "Bones", "label": "Hip-fracture mortality", "report": "IMI", "source_measure": "Hip Fracture"},
    {"code": "gi_bleeding", "category": "Digestive system", "label": "Gastrointestinal-bleeding mortality", "report": "IMI", "source_measure": "GI Hemorrhage"},
    {"code": "cabg", "category": "Heart surgery", "label": "Isolated coronary bypass operative mortality", "report": "CABG", "source_measure": "Isolated CABG Operative Mor"},
    {"code": "postoperative_sepsis", "category": "Surgical safety", "label": "Adult postoperative sepsis", "report": "PSI", "source_measure": "Postoperative Sepsis"},
)
MATCH_NOTES = {
    "not_imported": "HCAI results have not been imported for this location.",
    "matched": "Matched by California FACID to HCAI/OSHPD ID with a location consistency check.",
    "no_hcai_id": "No unique HCAI identifier in the California facility crosswalk.",
    "not_in_source": "No facility record with this HCAI identifier in the 2023 source.",
    "review_required": "Facility or campus relationship requires review; results are withheld.",
}


def performance_response(match=None, rows=()):
    status = match["match_status"] if match else "not_imported"
    by_code = {row["measure_code"]: row
               for row in rows} if status == "matched" else {}
    measures = []
    for definition in MEASURES:
        row = by_code.get(definition["code"])
        measures.append({
            "code": definition["code"],
            "category": definition["category"],
            "label": definition["label"],
            "rating": row["rating"] if row else None,
            "case_count": row["case_count"] if row else None,
            "availability": (
                "rated" if row and row["rating"] is not None
                else "not_reported" if row else "no_verified_result"
            ),
        })
    return {
        "year": SOURCE_YEAR,
        "source": "California HCAI",
        "source_url": SOURCE_URL,
        "match_status": status,
        "match_note": MATCH_NOTES[status],
        "source_hospital_name": match.get("source_name") if match and status == "matched" else None,
        "measures": measures,
    }


def attach_performance(cursor, hospitals):
    """Two batch queries per page, never a join that multiplies search rows."""
    if not hospitals:
        return
    location_ids = [hospital["location_id"] for hospital in hospitals]
    cursor.execute("""
        SELECT m.*, f.source_name
        FROM hcai_location_matches m
        LEFT JOIN hcai_facilities f USING (source_year, oshpd_id)
        JOIN hospital_search h ON h.location_id = m.location_id
            AND h.california_facid = m.california_facid
            AND h.latitude = m.location_latitude
            AND h.longitude = m.location_longitude
        WHERE m.source_year = %s AND m.location_id = ANY(%s)
    """, [SOURCE_YEAR, location_ids])
    matches = {row["location_id"]: row for row in cursor.fetchall()}
    cursor.execute("""
        SELECT m.location_id, p.measure_code, p.rating, p.case_count
        FROM hcai_location_matches m
        JOIN hcai_performance p USING (source_year, oshpd_id)
        WHERE m.source_year = %s AND m.location_id = ANY(%s)
            AND m.match_status = 'matched'
    """, [SOURCE_YEAR, location_ids])
    results = {}
    for row in cursor.fetchall():
        results.setdefault(row["location_id"], []).append(row)
    for hospital in hospitals:
        location_id = hospital["location_id"]
        hospital["hcai_performance"] = performance_response(
            matches.get(location_id), results.get(location_id, ()),
        )
