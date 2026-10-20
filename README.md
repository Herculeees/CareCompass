# CareCompass

CareCompass is an in-progress California hospital discovery and comparison project. The first release will help users find hospitals and compare distance, published CMS overall quality ratings, emergency-services status, and hospital type.

## Current status

Product scope and an initial visual concept are defined. The current Python exercise provides reusable lookup functions and displays a CMS hospital and all exact-CCN California location candidates. It distinguishes missing hospitals and zero, one, or multiple location candidates. The web application, database, API, and deployment are not implemented yet.

## Planned first release

- California hospital search by city, ZIP code, or browser location.
- Map and list views, with distance where verified coordinates are available.
- Side-by-side comparison of up to three hospitals.
- An emergency-services filter and links to Google Maps for directions.
- Explicit handling of missing data and unresolved location matches.

Accounts, saved facilities, clinics, insurance, cost estimates, and AI ranking are outside the first release.

## Proposed technology stack

Python/FastAPI, React/TypeScript, and PostgreSQL, with Docker, GitHub Actions, and an AWS deployment planned. Deployment details and the map provider remain to be decided.

## Run the current exercise

Use Python 3.11 or later. No third-party Python packages are required for this exercise.

Download the following source files and place them beside `inspect_hospital.py`:

| Source | Local filename | Purpose |
| --- | --- | --- |
| [CMS Hospital General Information](https://data.cms.gov/provider-data/dataset/xubh-q36u) | `Hospital_General_Information.csv` | Hospital identifiers, addresses, ratings, and emergency-services information |
| [CDPH Licensed and Certified Healthcare Facility Listing](https://data.ca.gov/@california-department-of-public-health/licensed-and-certified-healthcare-facility-listing) | `health_facility_locations.csv` | Facility records and location coordinates |

The downloaded CSV files are intentionally excluded from Git. Preserve leading zeros in identifiers and ZIP codes. Retain source attribution; the California listing identifies its license as Creative Commons Attribution.

From the project directory on Windows:

```powershell
py inspect_hospital.py
```

An optional hospital ID can be supplied without editing the script:

```powershell
py inspect_hospital.py 050007
```

Examples in the current local snapshots: `050002` has one candidate, `050007` has multiple candidates, and `050551` has no exact CCN candidate. `NOT-A-REAL-ID` demonstrates the hospital-not-found message. Candidates are not verified coordinate matches, even when only one is returned.

On systems with Python available as `python3`:

```sh
python3 inspect_hospital.py
```

## Matching and interpretation

CMS `Facility ID` is matched against California `CCN`, followed by address verification. Multiple candidate locations and unmatched identifiers need review; the current exercise does not implement a general matching pipeline.

Initial inspection of the downloaded snapshots found 377 California CMS hospital records, of which 354 had exact identifier matches in the California file. Of those, 97 had multiple candidate records. These counts describe identifier coverage, not validated coordinate accuracy, and may change with source updates.

Missing ratings are not zero. Distances will be labeled as straight-line estimates. Reported emergency services do not establish current opening status, capacity, or wait times. Overall hospital ratings are not specialty-specific ratings.

## Development approach

Development proceeds in small, explained steps: data validation, database and API design, backend implementation, frontend implementation, testing, and deployment. The developer leads implementation and reviews major architectural decisions before adopting them.
