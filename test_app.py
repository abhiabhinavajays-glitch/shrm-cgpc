"""
Integration test suite for SHRM Placement Cell Flask app.
Sets up its own isolated test records, tests endpoints, and cleans up.
"""
import unittest
from app import app
import models

class TestSHRMAppIntegration(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_dashboard_route_empty_or_filled(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Placement Cell Dashboard", response.data)

    def test_drives_page(self):
        response = self.client.get('/drives')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Placement Drives", response.data)

    def test_room_allotment_clash_prevention_flow(self):
        # 1. Create a test venue
        v_resp = self.client.post('/api/venues', data={
            "name": "Test Auditorium X",
            "type": "Auditorium",
            "capacity": 200,
            "block": "Block X",
            "floor": "1st Floor"
        })
        self.assertEqual(v_resp.status_code, 201)
        vid = v_resp.get_json()["id"]

        # 2. Book Test Auditorium X from 10:00 to 12:00 on 2026-11-10
        alloc1_resp = self.client.post('/api/allocations', data={
            "venue_id": vid,
            "date": "2026-11-10",
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Placement Drive",
            "invigilator": "Prof Test"
        })
        self.assertEqual(alloc1_resp.status_code, 201)
        alloc1_id = alloc1_resp.get_json()["id"]

        # 3. Attempt to book same venue on same date with overlapping slot (11:00 to 13:00)
        clash_resp = self.client.post('/api/allocations', data={
            "venue_id": vid,
            "date": "2026-11-10",
            "start_time": "11:00",
            "end_time": "13:00",
            "purpose": "Placement Drive"
        })
        self.assertEqual(clash_resp.status_code, 409)
        self.assertFalse(clash_resp.get_json()["success"])
        self.assertIn("already booked", clash_resp.get_json()["message"])

        # 4. Clean up
        self.client.delete(f'/api/allocations/{alloc1_id}')
        self.client.delete(f'/api/venues/{vid}')

    def test_schedule_drive_and_export_flow(self):
        # 1. Create a test drive
        drive_resp = self.client.post('/api/drives', data={
            "company_name": "TestCorp Technologies",
            "role": "Software Developer",
            "ctc_lpa": 12.0,
            "category": "Dream",
            "drive_date": "2026-11-15",
            "min_cgpa": 7.0,
            "allowed_backlogs": 0,
            "eligible_branches": "CSE,IT"
        })
        self.assertEqual(drive_resp.status_code, 201)
        drive_id = drive_resp.get_json()["id"]

        # 2. Register a student who qualifies
        stud_resp = self.client.post('/api/students', data={
            "usn": "1MS22TEST01",
            "name": "Test Student",
            "email": "test.student@test.edu",
            "branch": "CSE",
            "cgpa": 8.5,
            "backlogs": 0
        })
        self.assertEqual(stud_resp.status_code, 201)

        # 3. Verify eligible students API
        el_resp = self.client.get(f'/api/drives/{drive_id}/eligible-students')
        self.assertEqual(el_resp.status_code, 200)
        students = el_resp.get_json()
        self.assertTrue(any(s['usn'] == '1MS22TEST01' for s in students))

        # 4. Verify CSV export
        csv_resp = self.client.get(f'/api/drives/{drive_id}/export-eligible')
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn(b"1MS22TEST01", csv_resp.data)

        # 5. Clean up
        self.client.delete(f'/api/drives/{drive_id}')
        models.get_db().execute("DELETE FROM students WHERE usn = '1MS22TEST01'").connection.commit()

if __name__ == "__main__":
    unittest.main()
