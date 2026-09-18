"""
Unit Tests for Venue Clash Detection Engine
Tests all overlap scenarios:
1. Exact same time slot
2. Partial overlap (starts during another event)
3. Partial overlap (ends during another event)
4. Enclosing time slot
5. Consecutive time slots (10:00-11:00 vs 11:00-12:00 -> NO clash)
6. Different dates (NO clash)
7. Different venues (NO clash)
8. Exclude ID during edits (NO clash with self)
"""
import unittest
from clash_detector import check_venue_clash, times_overlap

class TestVenueClashDetection(unittest.TestCase):

    def setUp(self):
        self.mock_allocations = [
            {
                "id": 1,
                "venue_id": 10,
                "venue_name": "APJ Auditorium",
                "company_name": "Google",
                "round_name": "PPT",
                "date": "2026-10-01",
                "start_time": "10:00",
                "end_time": "12:00"
            },
            {
                "id": 2,
                "venue_id": 20,
                "venue_name": "Lovelace Lab",
                "company_name": "Microsoft",
                "round_name": "Coding Test",
                "date": "2026-10-01",
                "start_time": "14:00",
                "end_time": "16:00"
            }
        ]

    def test_exact_overlap(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "10:00", "12:00")
        self.assertTrue(res["has_clash"])
        self.assertIn("already booked", res["message"])

    def test_partial_overlap_starts_inside(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "11:00", "13:00")
        self.assertTrue(res["has_clash"])

    def test_partial_overlap_ends_inside(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "09:00", "10:30")
        self.assertTrue(res["has_clash"])

    def test_enclosing_overlap(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "09:00", "13:00")
        self.assertTrue(res["has_clash"])

    def test_consecutive_slots_no_clash(self):
        # 12:00 to 13:00 right after 10:00-12:00 should NOT clash
        res_after = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "12:00", "13:00")
        self.assertFalse(res_after["has_clash"])
        
        # 09:00 to 10:00 right before 10:00-12:00 should NOT clash
        res_before = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "09:00", "10:00")
        self.assertFalse(res_before["has_clash"])

    def test_different_venue_no_clash(self):
        res = check_venue_clash(self.mock_allocations, 30, "2026-10-01", "10:00", "12:00")
        self.assertFalse(res["has_clash"])

    def test_different_date_no_clash(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-02", "10:00", "12:00")
        self.assertFalse(res["has_clash"])

    def test_exclude_self_during_edit(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "10:00", "12:00", exclude_id=1)
        self.assertFalse(res["has_clash"])

    def test_invalid_time_range(self):
        res = check_venue_clash(self.mock_allocations, 10, "2026-10-01", "15:00", "14:00")
        self.assertTrue(res["has_clash"])
        self.assertIn("strictly earlier", res["message"])

if __name__ == "__main__":
    unittest.main()
