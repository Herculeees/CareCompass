# CareCompass

CareCompass is an in-progress California hospital discovery and comparison project. The first release will help users find hospitals and compare distance, published CMS overall quality ratings, emergency-services status, and hospital type.

## Current status

Product scope and an initial visual concept are defined. The current Python exercise provides reusable lookup functions and displays a CMS hospital and all exact-CCN California location candidates. It distinguishes missing hospitals and zero, one, or multiple location candidates. PostgreSQL 17 runs locally through Docker Compose, the hospital table has been created, and Python-to-PostgreSQL connectivity has been verified with `SELECT 1;`. The database import, web application, API, and cloud deployment are not implemented yet.

## Planned first release

- California hospital search by city, ZIP code, or browser location.
- Map and list views, with distance where verified coordinates are available.
- Side-by-side comparison of up to three hospitals.
- An emergency-services filter and links to Google Maps for directions.
- Explicit handling of missing data and unresolved location matches.

Accounts, saved facilities, clinics, insurance, cost estimates, and AI ranking are outside the first release.

## Proposed technology stack

Python/FastAPI, React/TypeScript, and PostgreSQL, with Docker, GitHub Actions, and an AWS deployment planned. Deployment details and the map provider remain to be decided.

## Project layout

```text
CareCompass/
├── scripts/                 # Python utilities and the upcoming import
│   ├── inspect_hospital.py
│   ├── generate_issue_report.py
│   ├── check_database.py
│   └── import_hospitals.py   # Reads California CMS records; no database writes yet
├── database/
│   └── schema.sql           # Initial PostgreSQL table definition
├── data/
│   └── raw/                 # Original downloaded CSVs; ignored by Git
├── reports/                 # Baseline review CSV and generated issue reports
├── docs/                    # Local-only journal and diagrams; ignored by Git
├── .venv/                   # Local Python environment; ignored by Git
├── .env                     # Local password; ignored by Git
├── .env.example             # Shareable environment template
├── .gitignore
├── compose.yaml             # Local PostgreSQL container configuration
├── requirements.txt
└── README.md
```

Run the commands below from the project root, `D:\CareCompass`. The inspection and issue-report scripts locate `data/raw/` relative to the project, rather than the terminal's current directory. Moving source files does not alter the Docker database or its volume.

## Local PostgreSQL setup

Install and start Docker Desktop with Linux containers. From the project directory, copy the environment template on Windows:

```powershell
Copy-Item .env.example .env
```

Do this only if `.env` does not already exist. Set your own local `POSTGRES_PASSWORD` in `.env`; never commit that file or share its contents. Then start PostgreSQL and verify SQL execution inside the container:

```powershell
docker compose up -d
docker compose exec db psql -U carecompass -d carecompass -c "SELECT 1;"
```

PostgreSQL 17 is published at `127.0.0.1:5432` and stores data in the named `postgres_data` volume. The database and initial user are both named `carecompass`. This initial user has administrative privileges; it is for local setup, not a production application role. Initialization settings apply only to an empty data directory; changing `.env` does not change an existing user's password.

To stop the services while keeping the database volume:

```powershell
docker compose down
```

Do not add `--volumes` unless you intend to delete the stored database data. The hospital table has been created locally, but hospital records have not been imported. Generated diagrams and the project journal stay local and are excluded from Git.

### Create the hospital table

For a new database, apply the schema once:

```powershell
docker compose cp database/schema.sql db:/tmp/schema.sql
docker compose exec db psql -U carecompass -d carecompass -v ON_ERROR_STOP=1 -f /tmp/schema.sql
```

Inspect the resulting table:

```powershell
docker compose exec db psql -U carecompass -d carecompass -P pager=off -c "\d hospitals"
```

If the table already exists, do not rerun the creation script or delete the table. This script is the initial schema, not a migration system.

### Verify Python database connectivity

Create the project environment if `.venv` does not already exist, then install its dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/check_database.py
```

The check prompts for the password configured when PostgreSQL was initialized, without displaying it or storing it in code. It connects to `127.0.0.1:5432` and executes `SELECT 1;`. Expected output: `Database returned: 1`. It does not automatically read `.env`, modify the schema, or insert hospital records. Keep Docker Desktop and the database container running during the check.

## Database schema

The first release uses one main PostgreSQL table, `hospitals`, with one row per CMS hospital. Its definition is in [database/schema.sql](database/schema.sql). Original CMS location fields remain separate from the selected California location so the source of each value can be traced.

### Hospital identity and original CMS location

| Column | PostgreSQL type | Required? | Description |
| --- | --- | --- | --- |
| `cms_facility_id` | `TEXT` | Yes; primary key | Unique CMS hospital identifier. Preserve leading zeros. |
| `name` | `TEXT` | Yes | Hospital name from CMS. |
| `hospital_type` | `TEXT` | No | Hospital category reported by CMS. |
| `phone` | `TEXT` | No | Contact phone number; preserve formatting. |
| `cms_address` | `TEXT` | No | Original CMS street address. |
| `cms_city` | `TEXT` | No | City from CMS. |
| `cms_state` | `TEXT` | Yes | State abbreviation; `CA` for the initial import. |
| `cms_zip` | `TEXT` | No | Original CMS ZIP code; preserve leading zeros. |

### Quality and emergency services

| Column | PostgreSQL type | Required? | Description |
| --- | --- | --- | --- |
| `overall_rating` | `SMALLINT` | No | CMS overall hospital rating, restricted to 1–5 when present. |
| `rating_footnote` | `TEXT` | No | Source footnote explaining the rating or its absence; interpret codes using the CMS data dictionary. |
| `emergency_services` | `BOOLEAN` | No | Reported emergency-services indicator: `TRUE`, `FALSE`, or `NULL` when unknown. Does not indicate live capacity or wait times. |

### Selected California location and import metadata

| Column | PostgreSQL type | Required? | Description |
| --- | --- | --- | --- |
| `california_facid` | `TEXT` | No | Identifier of the selected California facility record; a source ID, not a foreign key in this single-table design. |
| `california_address` | `TEXT` | No | Original street address of the selected California record. |
| `california_city` | `TEXT` | No | City of the selected California record. |
| `california_zip` | `TEXT` | No | ZIP code of the selected California record. |
| `latitude` | `DOUBLE PRECISION` | No | Latitude from the selected record; range −90 to 90. |
| `longitude` | `DOUBLE PRECISION` | No | Longitude from the selected record; range −180 to 180. |
| `location_match_status` | `TEXT` | Yes | Matching/review status, restricted to the values below. |
| `california_data_date` | `DATE` | No | Selected California record's `DATA_DATE`; source extraction date, not import time. |
| `imported_at` | `TIMESTAMPTZ` | Yes | Time the hospital record was imported into PostgreSQL. |

**\* Pending manual review:** In the current source snapshots, **123 hospitals** have unresolved location matches: 54 have multiple address-and-ZIP candidates, 9 have matching addresses but different ZIP codes, 37 have matching IDs but different normalized addresses, and 23 have no exact ID match. These hospitals remain in the planned hospital table with unresolved selected-location fields and coordinates set to `NULL`. Candidate records remain in the [baseline issue report](reports/hospital-issues-baseline.csv) for review. The other 254 hospitals have single address-and-ZIP candidates, not independently verified locations.

### Location match statuses

| Value | Meaning |
| --- | --- |
| `single_candidate` | Exactly one same-ID candidate matches the normalized street address and five-digit ZIP. Coordinates still require basic validation before use. |
| `review_required` | Matching IDs have multiple address-and-ZIP candidates or conflicting address/ZIP information. |
| `no_id_match` | No exact California CCN match was found for the CMS facility ID. |
| `review_approved` | A reviewer approved a particular California facility record. The verification evidence stays in the review record. |

Missing values use SQL `NULL`, not zero or the text `N/A`. Latitude and longitude must either both be present or both be `NULL`. Coordinate range checks do not independently verify the correct campus. Hospital quality ratings belong to the CMS provider record and should not be presented as independently measured ratings for every related campus.

## Run the current exercise

Use Python 3.11 or later. No third-party Python packages are required for this exercise.

Download the following source files and place them in `data/raw/`:

| Source | Local filename | Purpose |
| --- | --- | --- |
| [CMS Hospital General Information](https://data.cms.gov/provider-data/dataset/xubh-q36u) | `Hospital_General_Information.csv` | Hospital identifiers, addresses, ratings, and emergency-services information |
| [CDPH Licensed and Certified Healthcare Facility Listing](https://data.ca.gov/@california-department-of-public-health/licensed-and-certified-healthcare-facility-listing) | `health_facility_locations.csv` | Facility records and location coordinates |

The downloaded CSV files are intentionally excluded from Git. Preserve leading zeros in identifiers and ZIP codes. Retain source attribution; the California listing identifies its license as Creative Commons Attribution.

From the project directory on Windows:

```powershell
py scripts/inspect_hospital.py
```

An optional hospital ID can be supplied without editing the script:

```powershell
py scripts/inspect_hospital.py 050007
```

Examples in the current local snapshots: `050002` has one candidate, `050007` has multiple candidates, and `050551` has no exact CCN candidate. `NOT-A-REAL-ID` demonstrates the hospital-not-found message. Candidates are not verified coordinate matches, even when only one is returned.

On systems with Python available as `python3`:

```sh
python3 scripts/inspect_hospital.py
```

### Preview California records for the upcoming import

```powershell
.\.venv\Scripts\python.exe scripts/import_hospitals.py
```

The current script reads the CMS file, filters to California, and prints the total and the first three hospital IDs, names, and cities. The current snapshot contains 377 California records. Database-value conversions and inserts are not implemented yet; this command does not connect to PostgreSQL or change its data.

## Matching and interpretation

CMS `Facility ID` is matched against California `CCN`, followed by address verification. Multiple candidate locations and unmatched identifiers need review; the current exercise does not implement a general matching pipeline.

Initial inspection of the downloaded snapshots found 377 California CMS hospital records, of which 354 had exact identifier matches in the California file. Of those, 97 had multiple candidate records. These counts describe identifier coverage, not validated coordinate accuracy, and may change with source updates.

Missing ratings are not zero. Distances will be labeled as straight-line estimates. Reported emergency services do not establish current opening status, capacity, or wait times. Overall hospital ratings are not specialty-specific ratings.

## Address review milestone

Address normalization now handles common street types and direction abbreviations. For the current source snapshots, 254 of 377 California CMS hospitals have exactly one same-ID candidate matching the normalized street address and five-digit ZIP. This is a proposed location match, not independently verified coordinate accuracy.

The remaining **123 hospitals require later review**:

| Issue | Hospitals |
| --- | ---: |
| Multiple address-and-ZIP candidates | 54 |
| Address matches but ZIP differs | 9 |
| Same ID but normalized address differs | 37 |
| No exact ID match | 23 |

Run the issue-report generator with the original CSV files available locally:

```powershell
py scripts/generate_issue_report.py
```

Each run creates a timestamped CSV in `reports/`, excluding the 254 single matches. The baseline review snapshot is [reports/hospital-issues-baseline.csv](reports/hospital-issues-baseline.csv). It contains 230 candidate-level rows for 123 hospitals; all decisions are pending. No candidate is automatically approved, and original source files are unchanged. Timestamped reports are excluded from Git to avoid committing duplicate generated outputs.

Detailed exception review is deferred while work proceeds to database design. The planned application will retain unresolved hospitals, displaying unavailable distance and omitting map markers until their locations are resolved.

## Development approach

Development proceeds in small, explained steps: data validation, database and API design, backend implementation, frontend implementation, testing, and deployment. The developer leads implementation and reviews major architectural decisions before adopting them.
