import csv

from inspect_hospital import CMS_FILE


def read_california_hospitals() -> list[dict[str, str]]:
    hospitals = []

    with CMS_FILE.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for hospital in reader:
            if hospital["State"].strip() == "CA":
                hospitals.append(hospital)

    return hospitals


def main() -> None:
    hospitals = read_california_hospitals()

    print("California hospitals found:", len(hospitals))

    for hospital in hospitals[:3]:
        print(
            hospital["Facility ID"],
            hospital["Facility Name"],
            hospital["City/Town"],
        )


if __name__ == "__main__":
    main()