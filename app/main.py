from fastapi import FastAPI
from psycopg.rows import dict_row

from app.database import get_connection

app = FastAPI(title="CareCompass API")

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
):
    query = """
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
            record_source
        FROM hospital_search
    """
    conditions = []
    params = []

    if zip_code is not None:
        conditions.append("zip_code = %s")
        params.append(zip_code.strip())

    if city is not None:
        conditions.append("LOWER(city) = LOWER(%s)")
        params.append(city.strip())

    if emergency_services is not None:
        conditions.append("emergency_services = %s")
        params.append(emergency_services)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY location_id LIMIT 5;"

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            hospitals = cursor.fetchall()

    return {"hospitals": hospitals}
