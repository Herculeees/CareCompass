"""Opt-in database regression checks. All test writes are rolled back."""
import os
import unittest

from psycopg import IntegrityError
from psycopg.rows import dict_row

from app.database import get_connection
from app.performance import attach_performance
from scripts.import_hcai_performance import (
    CROSSWALK_FILE, SOURCE_FILE, match_locations, prepare_source, read_csv,
    write_snapshot,
)


@unittest.skipUnless(os.environ.get("CARECOMPASS_LIVE_TESTS") == "1", "Live database checks are opt-in")
class DatabaseRegressionTests(unittest.TestCase):
    def setUp(self):
        self.connection = get_connection()

    def tearDown(self):
        self.connection.rollback()
        self.connection.close()

    def test_constraints_reject_invalid_ratings_and_missing_facilities(self):
        with self.connection.cursor() as cursor:
            for statement, params in (
                ("UPDATE hcai_performance SET rating = %s WHERE oshpd_id = '106301279'", ['Excellent']),
                ("UPDATE hcai_performance SET case_count = %s WHERE oshpd_id = '106301279'", [-1]),
                ("UPDATE hcai_performance SET oshpd_id = %s WHERE oshpd_id = '106301279'", ['999999999']),
            ):
                with self.subTest(statement=statement):
                    with self.assertRaises(IntegrityError):
                        with self.connection.transaction():
                            cursor.execute(statement, params)

    def test_changed_location_snapshot_does_not_expose_old_results(self):
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM hospital_search WHERE location_id = 'CMS:050570'")
            hospital = cursor.fetchone()
            cursor.execute("UPDATE hcai_location_matches SET location_latitude = location_latitude + 1 WHERE location_id = 'CMS:050570'")
            attach_performance(cursor, [hospital])
            self.assertEqual(hospital['hcai_performance']['match_status'], 'not_imported')
            self.assertTrue(all(m['rating'] is None for m in hospital['hcai_performance']['measures']))

    def test_reimport_preserves_source_hospitals_and_record_counts(self):
        source = read_csv(SOURCE_FILE)
        facilities, records = prepare_source(source)
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM hospital_search ORDER BY location_id")
            locations = cursor.fetchall()
            cursor.execute("SELECT * FROM hospitals ORDER BY cms_facility_id")
            original_hospitals = cursor.fetchall()
            matches = match_locations(locations, read_csv(CROSSWALK_FILE), source)
            for _ in range(2):
                write_snapshot(cursor, facilities, records, matches, 'test-source-hash', 'test-crosswalk-hash')
                cursor.execute("SELECT COUNT(*) AS total FROM hcai_performance")
                self.assertEqual(cursor.fetchone()['total'], 1981)
                cursor.execute("SELECT COUNT(*) AS total FROM hcai_location_matches")
                self.assertEqual(cursor.fetchone()['total'], 320)
            cursor.execute("SELECT * FROM hospital_search ORDER BY location_id")
            self.assertEqual(cursor.fetchall(), locations)
            cursor.execute("SELECT * FROM hospitals ORDER BY cms_facility_id")
            self.assertEqual(cursor.fetchall(), original_hospitals)


if __name__ == '__main__':
    unittest.main()
