import csv
from pathlib import Path

project_folder = Path(__file__).resolve().parent
cms_file = project_folder / "Hospital_General_Information.csv"

with cms_file.open(encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for hospital in reader:
        if hospital["Facility ID"].strip() == "050002":
            print("ID:", hospital["Facility ID"])
            print("Name:", hospital["Facility Name"])
            print("Address:", hospital["Address"])
            print("Rating:", hospital["Hospital overall rating"])
            break
    else:
        print("Hospital not found.")
        
california_file = project_folder / "health_facility_locations.csv"

with california_file.open(encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for facility in reader:
        if facility["CCN"].strip() == "050002":
            print("\nCalifornia record:")
            print("CCN:", facility["CCN"])
            print("Name:", facility["FACNAME"])
            print("Address:", facility["ADDRESS"])
            print("Latitude:", facility["LATITUDE"])
            print("Longitude:", facility["LONGITUDE"])