import unittest

from app.performance import MEASURES, performance_response
from scripts.import_hcai_performance import (
    distance_km, match_locations, parse_number, prepare_source,
)


def source_row(**changes):
    row = {
        "Year": "2023", "OSHPDID": "106301279", "Hospital": "Example Hospital",
        "Type of Report": "IMI", "Performance Measure": "Heart Failure",
        "Hospital Ratings": "As Expected", "# of Cases": "100",
        "# of Adverse Events": "0", "Risk-adjusted Rate": "0",
        "Latitude": "33.78712", "Longitude": "-117.888",
    }
    row.update(changes)
    return row


def location(**changes):
    value = {"location_id": "CMS:050000", "california_facid": "001",
             "latitude": 33.78712, "longitude": -117.888, "overall_rating": None}
    value.update(changes)
    return value


CROSSWALK = [{"FACID": "001", "HCAI_ID": "106301279"}]


class SourceTests(unittest.TestCase):
    def test_seven_distinct_measures(self):
        self.assertEqual(len(MEASURES), 7)
        self.assertEqual(len({m["code"] for m in MEASURES}), 7)

    def test_zero_and_blank_are_distinct(self):
        self.assertEqual(parse_number("0", integer=True), 0)
        self.assertIsNone(parse_number(""))
        _, rows = prepare_source([source_row()])
        self.assertEqual(rows[0]["adverse_events"], 0)
        self.assertEqual(rows[0]["source_rate"], 0)

    def test_blank_rating_is_not_as_expected(self):
        _, rows = prepare_source([source_row(**{"Hospital Ratings": "", "# of Cases": "", "# of Adverse Events": "", "Risk-adjusted Rate": ""})])
        self.assertIsNone(rows[0]["rating"])
        self.assertIsNone(rows[0]["case_count"])

    def test_pediatric_sepsis_not_imported_as_adult(self):
        _, rows = prepare_source([source_row(**{"Type of Report": "PDI", "Performance Measure": "Postop Sepsis"})])
        self.assertEqual(rows, [])

    def test_duplicate_and_invalid_data_rejected(self):
        with self.assertRaises(ValueError):
            prepare_source([source_row(), source_row()])
        for changes in ({"Year": "2022"}, {"Hospital Ratings": "Excellent"},
                        {"# of Cases": "1", "# of Adverse Events": "2"},
                        {"Risk-adjusted Rate": "NaN"}, {"OSHPDID": "123"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                prepare_source([source_row(**changes)])


class MatchingTests(unittest.TestCase):
    def test_exact_crosswalk_matches(self):
        result = match_locations([location()], CROSSWALK, [source_row()])[0]
        self.assertEqual(result["match_status"], "matched")
        self.assertEqual(result["oshpd_id"], "106301279")

    def test_similar_name_does_not_override_missing_id(self):
        result = match_locations([location(california_facid="new")], CROSSWALK, [source_row()])[0]
        self.assertEqual(result["match_status"], "no_hcai_id")
        self.assertIsNone(result["oshpd_id"])

    def test_missing_year_facility(self):
        result = match_locations([location()], CROSSWALK, [])[0]
        self.assertEqual(result["match_status"], "not_in_source")

    def test_distant_or_invalid_coordinates_withhold_results(self):
        for changes in ({"Latitude": "34"}, {"Latitude": ""}, {"Latitude": "NaN"}):
            result = match_locations([location()], CROSSWALK, [source_row(**changes)])[0]
            self.assertEqual(result["match_status"], "review_required")
            self.assertIsNone(result["oshpd_id"])

    def test_multiple_campuses_cannot_share_result(self):
        locations = [location(), location(location_id="CA:other")]
        results = match_locations(locations, CROSSWALK, [source_row()])
        self.assertTrue(all(r["match_status"] == "review_required" for r in results))

    def test_conflicting_crosswalk_is_held(self):
        crosswalk = CROSSWALK + [{"FACID": "001", "HCAI_ID": "106999999"}]
        result = match_locations([location()], crosswalk, [source_row()])[0]
        self.assertEqual(result["match_status"], "review_required")

    def test_distance_known_and_zero(self):
        self.assertAlmostEqual(distance_km(0, 0, 0, 1), 111.1949, places=3)
        self.assertEqual(distance_km(1, 2, 1, 2), 0)


class ResponseTests(unittest.TestCase):
    def test_seven_unavailable_results_without_match(self):
        data = performance_response()
        self.assertEqual(len(data["measures"]), 7)
        self.assertTrue(all(m["rating"] is None for m in data["measures"]))

    def test_reviewed_location_cannot_leak_rating(self):
        data = performance_response({"match_status": "review_required"},
                                    [{"measure_code": "heart_failure", "rating": "Better", "case_count": 20}])
        self.assertTrue(all(m["rating"] is None for m in data["measures"]))



if __name__ == "__main__":
    unittest.main()
