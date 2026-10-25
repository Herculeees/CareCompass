from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from app.database import get_connection
from app.performance import attach_performance
from fastapi.middleware.cors import CORSMiddleware
from app.geocoding import coordinates_for_zip, coordinates_for_city

app = FastAPI(title="CareCompass API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/hospitals/count")
def hospital_count():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hospital_search;")
            result = cursor.fetchone()

    return {"total": result[0]}


@app.get("/hospitals")
def get_hospitals(
    city: str | None = None,
    emergency_services: bool | None = None,
    zip_code: str | None = None,
    name: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    near_zip: str | None = None,
    near_city: str | None = None,
):
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422,
            detail="Provide both latitude and longitude together.",
        )

    if near_city is not None:
        if (
            near_zip is not None
            or latitude is not None
            or longitude is not None
            or city is not None
            or zip_code is not None
        ):
            raise HTTPException(
                status_code=422,
                detail="Use near_city without another location or exact location filter.",
            )

        try:
            latitude, longitude = coordinates_for_city(near_city)
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error

    if near_zip is not None:
        if latitude is not None or zip_code is not None:
            raise HTTPException(
                status_code=422,
                detail="Use near_zip without coordinates or an exact ZIP filter.",
            )

        try:
            latitude, longitude = coordinates_for_zip(near_zip)
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error

    conditions = []
    params = []

    distance_expression = "NULL::double precision"

    if latitude is not None:
        distance_expression = """
            6371.0 * 0.621371 * ACOS(
                LEAST(1.0, GREATEST(-1.0,
                    SIN(RADIANS(%s)) * SIN(RADIANS(latitude))
                    + COS(RADIANS(%s)) * COS(RADIANS(latitude))
                    * COS(RADIANS(longitude - %s))
                ))
            )
        """
        params.extend([latitude, latitude, longitude])

        # Nearby searches require usable hospital coordinates.
        conditions.append("latitude IS NOT NULL")
        conditions.append("longitude IS NOT NULL")

    query = f"""
        SELECT
            location_id,
            cms_facility_id,
            california_facid,
            name,
            address,
            city,
            state,
            zip_code,
            latitude,
            longitude,
            hospital_type,
            overall_rating,
            emergency_services,
            record_source,
            {distance_expression} AS distance_miles
        FROM hospital_search
    """

    if zip_code is not None:
        conditions.append("zip_code = %s")
        params.append(zip_code.strip())

    if city is not None:
        conditions.append("LOWER(city) = LOWER(%s)")
        params.append(city.strip())

    if emergency_services is not None:
        conditions.append("emergency_services = %s")
        params.append(emergency_services)

    if name is not None:
        conditions.append("name ILIKE %s")
        params.append(f"%{name.strip()}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if latitude is not None:
        query += " ORDER BY distance_miles ASC NULLS LAST, location_id"
    else:
        query += " ORDER BY location_id"

    query += " LIMIT %s OFFSET %s;"
    params.extend([limit, offset])

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            hospitals = cursor.fetchall()
            attach_performance(cursor, hospitals)

    return {"hospitals": hospitals}
