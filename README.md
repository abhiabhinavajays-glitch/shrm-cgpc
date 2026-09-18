# SHRM Web App for College Career Guidance & Placement Cell

A modern, production-grade web application designed for College Placement & Training (T&P) Officers, Career Counselors, and Recruitment Coordinators. It streamlines company recruitment pipelines, eliminates campus venue scheduling conflicts with automated clash detection, screens student eligibility, and tracks placement analytics.

---

## Key Features

1. **Placement Drive Scheduling & Multi-Round Pipeline**:
   - Schedule company recruitment drives with CTC packages, category (Super Dream, Dream, Core/IT), job designations, and eligibility criteria (Minimum CGPA, maximum backlogs, eligible branches).
   - Automated generation of recruitment stages: Pre-Placement Talk (PPT), Online Aptitude/Coding Assessment, Technical Interview Rounds 1 & 2, and HR/Management Interviews.

2. **Smart Room / Venue Allotment with Clash Detection**:
   - Master catalog of college infrastructure: Auditoriums, Seminar Halls, Computer Labs, Group Discussion (GD) Rooms, and Interview Cabins.
   - **Clash Prevention Engine**: Automatically calculates time interval intersections on the requested date. If a room is already allocated to another drive round or workshop, double-booking is blocked with an instant conflict alert detailing who is occupying the room.
   - Interactive Visual Daily Timeline Matrix showing venue availability and occupancy blocks.

3. **Student Eligibility Screening & CSV Export**:
   - Student database with USN, Branch, CGPA, and Active Backlogs.
   - One-click eligibility matcher: Instantly filters eligible candidates for any company drive based on cutoff criteria and allows 1-click CSV roster download.

4. **Career Guidance & Skill Training Programs**:
   - Schedule mock interviews, resume bootcamps, and technical preparation clinics.
   - Allot campus venues for guidance events with the same conflict protection.

5. **Placement Analytics Dashboard**:
   - Conversion rate, placed students vs. batch size, average package, highest package, and branch-wise placement breakdown chart.

---

## How to Run

### Quick Start (Double-Click)
Run `run.bat` in this folder, or open a terminal and run:

```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Automated Tests

Run the test suite to verify clash detection and application workflows:
```bash
python test_clashes.py
python test_app.py
```
