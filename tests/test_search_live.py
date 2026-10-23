"""Optional live regression checks: set CARECOMPASS_LIVE_TESTS=1 first.

Requires the existing populated database and running FastAPI server.
"""
import json
import math
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(path="/hospitals", origin=None, **params):
    url = "http://127.0.0.1:8000" + path + "?" + urlencode(params)
    req = Request(url, headers={"Origin": origin} if origin else {})
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, json.load(response), response.headers
    except HTTPError as error:
        return error.code, json.load(error), error.headers


@unittest.skipUnless(os.environ.get("CARECOMPASS_LIVE_TESTS") == "1", "Live API checks are opt-in")
class SearchRegressionTests(unittest.TestCase):
    def rows(self, **params):
        status, body, _ = request(**params)
        self.assertEqual(status, 200)
        return body["hospitals"]

    def test_health_and_coverage(self):
        self.assertEqual(request("/health")[1], {"status": "ok"})
        self.assertEqual(request("/hospitals/count")[1], {"total": 320})

    def test_all_pages_have_unique_ids_and_seven_measures(self):
        rows = sum((self.rows(limit=100, offset=offset) for offset in range(0, 400, 100)), [])
        self.assertEqual(len(rows), 320)
        self.assertEqual(len({r["location_id"] for r in rows}), 320)
        for row in rows:
            p = row["hcai_performance"]
            self.assertEqual(p["year"], 2023)
            self.assertEqual(len(p["measures"]), 7)
        rated = [r for r in rows if any(m["rating"] is not None for m in r["hcai_performance"]["measures"])]
        self.assertEqual(len(rated), 221)
        self.assertEqual(sum(r["overall_rating"] is not None for r in rows), 189)
        self.assertEqual(sum(r["overall_rating"] is None for r in rated), 35)

    def test_pagination_and_regular_distance(self):
        first, second = self.rows(limit=3), self.rows(limit=3, offset=3)
        self.assertEqual(first + second, self.rows(limit=6))
        self.assertTrue(all(r["distance_miles"] is None for r in first))
        self.assertEqual(self.rows(offset=10000), [])

    def test_combined_filters_and_name_case(self):
        params = dict(city=" Irvine ", zip_code="92612", name="UCI", emergency_services="true")
        rows = self.rows(**params)
        self.assertTrue(rows)
        self.assertTrue(all(r["city"].lower() == "irvine" and r["zip_code"] == "92612" and r["emergency_services"] is True for r in rows))
        self.assertEqual(self.rows(name="Irvine"), self.rows(name="irvine"))
        self.assertEqual(self.rows(name="zzzzz' OR 1=1 --"), [])

    def test_emergency_false_excludes_unknown(self):
        rows = self.rows(emergency_services="false", limit=100)
        self.assertTrue(rows)
        self.assertTrue(all(r["emergency_services"] is False for r in rows))

    def test_nearby_with_independent_distance(self):
        lat, lon = 33.6846, -117.8265
        rows = self.rows(latitude=lat, longitude=lon, limit=100)
        distances = [r["distance_miles"] for r in rows]
        self.assertEqual(distances, sorted(distances))
        for row in rows:
            a, b = math.radians(lat), math.radians(row["latitude"])
            h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(row["longitude"]-lon)/2)**2
            expected = 6371 * .621371 * 2 * math.asin(min(1, math.sqrt(h)))
            self.assertAlmostEqual(row["distance_miles"], expected, delta=.0001)

    def test_invalid_inputs(self):
        for params in (dict(limit=0), dict(limit=101), dict(limit="abc"), dict(offset=-1),
                       dict(latitude=1), dict(longitude=1), dict(latitude=91, longitude=0),
                       dict(latitude=0, longitude=-181), dict(latitude="nan", longitude=0),
                       dict(latitude="inf", longitude=0), dict(emergency_services="maybe")):
            with self.subTest(params=params):
                self.assertEqual(request(**params)[0], 422)

    def test_cors(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            self.assertEqual(request(origin=origin, limit=1)[2].get("Access-Control-Allow-Origin"), origin)
        self.assertIsNone(request(origin="http://unapproved.example", limit=1)[2].get("Access-Control-Allow-Origin"))

    def test_uci_source_results_and_irvine_is_not_borrowed(self):
        from app.database import get_connection
        # Orange's existing unresolved location is not silently approved by this import.
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT measure_code, rating FROM hcai_performance WHERE oshpd_id = %s AND source_year = 2023", ['106301279'])
                ratings = dict(cursor.fetchall())
        self.assertEqual(ratings["gi_bleeding"], "Better")
        self.assertEqual(ratings["postoperative_sepsis"], "Better")
        fountain = self.rows(name="Fountain Valley")
        uci = next(r for r in fountain if r["location_id"] == "CMS:050570")
        self.assertEqual(next(m['rating'] for m in uci['hcai_performance']['measures'] if m['code'] == 'heart_failure'), 'Worse')
        irvine = next(r for r in self.rows(city="Irvine") if r["location_id"] == "CA:630028504")
        self.assertTrue(all(m["rating"] is None for m in irvine["hcai_performance"]["measures"]))

    def test_coordinate_discrepancy_withholds_results(self):
        row = next(r for r in self.rows(name="PALOMAR UCSD") if r["location_id"] == "CA:630013873")
        self.assertEqual(row["hcai_performance"]["match_status"], "review_required")
        self.assertTrue(all(m["rating"] is None for m in row["hcai_performance"]["measures"]))


if __name__ == "__main__":
    unittest.main()
