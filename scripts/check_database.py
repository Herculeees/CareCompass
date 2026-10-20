from getpass import getpass

import psycopg


password = getpass("Database password: ")

with psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="carecompass",
    user="carecompass",
    password=password,
    connect_timeout=5,
) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        print("Database returned:", result[0])