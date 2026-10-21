import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE)


def get_connection():
    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="carecompass",
        user="carecompass",
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )