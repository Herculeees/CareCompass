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
            cursor.execute("SELECT COUNT(*) FROM hospitals;")
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
            cms_facility_id,
            name,
            cms_city,
            overall_rating,
            emergency_services
        FROM hospitals
    """
    conditions = []
    params = []

    if zip_code is not None:
        conditions.append("cms_zip = %s")
        params.append(zip_code.strip())

    if city is not None:
        conditions.append("LOWER(cms_city) = LOWER(%s)")
        params.append(city.strip())

    if emergency_services is not None:
        conditions.append("emergency_services = %s")
        params.append(emergency_services)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY cms_facility_id LIMIT 5;"

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            hospitals = cursor.fetchall()

    return {"hospitals": hospitals}
