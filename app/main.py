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
def get_hospitals():
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT cms_facility_id, name, cms_city, overall_rating, emergency_services
                FROM hospitals
                ORDER BY cms_facility_id
                LIMIT 5;
            """)
            hospitals = cursor.fetchall()

    return {"hospitals": hospitals}
