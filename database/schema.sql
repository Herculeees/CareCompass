CREATE TABLE hospitals (
    -- Hospital identity
    cms_facility_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hospital_type TEXT,
    phone TEXT,

    -- Original CMS location
    cms_address TEXT,
    cms_city TEXT,
    cms_state TEXT NOT NULL CHECK (cms_state = 'CA'),
    cms_zip TEXT,

    -- Quality and services
    overall_rating SMALLINT CHECK (overall_rating BETWEEN 1 AND 5),
    rating_footnote TEXT,
    emergency_services BOOLEAN,

    -- Selected California location
    california_facid TEXT,
    california_address TEXT,
    california_city TEXT,
    california_zip TEXT,
    latitude DOUBLE PRECISION CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION CHECK (longitude BETWEEN -180 AND 180),

    location_match_status TEXT NOT NULL CHECK (
        location_match_status IN (
            'single_candidate',
            'review_required',
            'no_id_match',
            'review_approved'
        )
    ),

    -- Import metadata
    california_data_date DATE,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Coordinates must be supplied together or both left empty
    CONSTRAINT coordinates_present_together CHECK (
        (latitude IS NULL AND longitude IS NULL)
        OR
        (latitude IS NOT NULL AND longitude IS NOT NULL)
    )
);