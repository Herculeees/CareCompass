-- Apply through scripts/import_hcai_performance.py --write in one transaction.
-- Requires the existing hospital_search view. Does not alter source hospitals.
CREATE TABLE IF NOT EXISTS hcai_facilities (
    source_year SMALLINT NOT NULL CHECK (source_year = 2023),
    oshpd_id TEXT NOT NULL CHECK (oshpd_id ~ '^[0-9]{9}$'),
    source_name TEXT NOT NULL,
    PRIMARY KEY (source_year, oshpd_id)
);

CREATE TABLE IF NOT EXISTS hcai_performance (
    source_year SMALLINT NOT NULL,
    oshpd_id TEXT NOT NULL,
    measure_code TEXT NOT NULL CHECK (measure_code IN (
        'heart_attack', 'heart_failure', 'pneumonia', 'hip_fracture',
        'gi_bleeding', 'cabg', 'postoperative_sepsis'
    )),
    report_type TEXT NOT NULL CHECK (report_type IN ('IMI', 'CABG', 'PSI')),
    source_measure TEXT NOT NULL,
    rating TEXT CHECK (rating IN ('Better', 'As Expected', 'Worse')),
    case_count INTEGER CHECK (case_count >= 0),
    adverse_events INTEGER CHECK (adverse_events >= 0),
    -- Preserve the numeric source rate. Units/methodology must be verified
    -- before the API displays rates or compares values across report types.
    source_rate NUMERIC CHECK (source_rate >= 0),
    source_url TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_year, oshpd_id, measure_code),
    FOREIGN KEY (source_year, oshpd_id)
        REFERENCES hcai_facilities (source_year, oshpd_id),
    CHECK (adverse_events <= case_count),
    CHECK (rating IS NULL OR (case_count IS NOT NULL AND source_rate IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS hcai_location_matches (
    source_year SMALLINT NOT NULL CHECK (source_year = 2023),
    location_id TEXT NOT NULL,
    california_facid TEXT NOT NULL,
    oshpd_id TEXT,
    candidate_oshpd_id TEXT,
    match_status TEXT NOT NULL CHECK (match_status IN (
        'matched', 'no_hcai_id', 'not_in_source', 'review_required'
    )),
    reason TEXT NOT NULL,
    location_latitude DOUBLE PRECISION NOT NULL,
    location_longitude DOUBLE PRECISION NOT NULL,
    max_source_distance_km DOUBLE PRECISION,
    crosswalk_sha256 TEXT NOT NULL,
    PRIMARY KEY (source_year, location_id),
    FOREIGN KEY (source_year, oshpd_id)
        REFERENCES hcai_facilities (source_year, oshpd_id),
    CHECK ((match_status = 'matched') = (oshpd_id IS NOT NULL))
);

-- A source facility cannot silently donate its outcomes to two campuses.
CREATE UNIQUE INDEX IF NOT EXISTS hcai_one_location_per_facility
    ON hcai_location_matches (source_year, oshpd_id)
    WHERE match_status = 'matched';
