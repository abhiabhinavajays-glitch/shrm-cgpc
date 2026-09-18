"""
Database Models & Data Access Layer for SHRM Placement Cell System
Uses SQLite with WAL mode for fast concurrency and reliability.
"""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placement_shrm.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Venues / Rooms Master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        block TEXT NOT NULL,
        floor TEXT NOT NULL,
        equipment TEXT,
        status TEXT DEFAULT 'Active'
    );
    """)

    # Placement Drives Master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        role TEXT NOT NULL,
        ctc_lpa REAL NOT NULL,
        category TEXT NOT NULL,
        drive_date TEXT NOT NULL,
        min_cgpa REAL DEFAULT 6.0,
        allowed_backlogs INTEGER DEFAULT 0,
        eligible_branches TEXT DEFAULT 'CSE,IT,ECE,EEE,MECH,CIVIL',
        job_location TEXT,
        contact_person TEXT,
        contact_email TEXT,
        contact_phone TEXT,
        status TEXT DEFAULT 'Scheduled',
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Multi-round breakdown for drives
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drive_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_id INTEGER NOT NULL REFERENCES drives(id) ON DELETE CASCADE,
        round_name TEXT NOT NULL,
        round_order INTEGER DEFAULT 1,
        round_date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'Scheduled'
    );
    """)

    # Students Master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usn TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        branch TEXT NOT NULL,
        cgpa REAL NOT NULL,
        backlogs INTEGER DEFAULT 0,
        passing_year INTEGER DEFAULT 2026,
        placement_status TEXT DEFAULT 'Unplaced',
        placed_company TEXT,
        package_lpa REAL
    );
    """)

    # Career Guidance & Training Workshops
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guidance_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        trainer_name TEXT NOT NULL,
        trainer_org TEXT,
        event_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        venue_id INTEGER REFERENCES venues(id) ON DELETE SET NULL,
        target_audience TEXT,
        status TEXT DEFAULT 'Upcoming',
        description TEXT
    );
    """)

    # Venue / Room Allocations (Clash Protected)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_id INTEGER NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
        drive_round_id INTEGER REFERENCES drive_rounds(id) ON DELETE CASCADE,
        guidance_event_id INTEGER REFERENCES guidance_events(id) ON DELETE CASCADE,
        purpose TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        invigilator TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def clear_all_data(clear_venues=False):
    """Clears all drives, rounds, room allocations, students, and guidance events."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM room_allocations")
    cursor.execute("DELETE FROM drive_rounds")
    cursor.execute("DELETE FROM drives")
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM guidance_events")
    if clear_venues:
        cursor.execute("DELETE FROM venues")
    conn.commit()
    conn.close()

def delete_venue(venue_id):
    conn = get_db()
    conn.execute("DELETE FROM venues WHERE id = ?", (venue_id,))
    conn.commit()
    conn.close()

def seed_sample_data():
    conn = get_db()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM venues")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Insert Master Venues
    venues = [
        ("Dr. A.P.J. Abdul Kalam Auditorium", "Auditorium", 550, "Main Block", "Ground Floor", "Central Stage, 4K Projector, Surround Audio, Dual Podiums, AC"),
        ("Alan Turing Seminar Hall", "Seminar Hall", 180, "Computer Science Block", "1st Floor", "Dual Screen Projector, Wireless Microphones, Smart Board, AC"),
        ("Ada Lovelace Computing Lab 01", "Computer Lab", 120, "IT Block", "2nd Floor", "120 Core i7 Workstations, High-speed LAN, UPS Backup, AC"),
        ("John von Neumann Computing Lab 02", "Computer Lab", 100, "IT Block", "2nd Floor", "100 High-performance PCs, Online Assessment Server, AC"),
        ("Sir M. Visvesvaraya GD Room 1", "GD Room", 25, "Placement Tower", "3rd Floor", "Circular Discussion Table, HD Camera, Flip-charts, AC"),
        ("Vikram Sarabhai GD Room 2", "GD Room", 25, "Placement Tower", "3rd Floor", "Conference Table, Smart Display, Recording Setup, AC"),
        ("Interview Cabin Alpha (101)", "Interview Cabin", 6, "Placement Tower", "3rd Floor", "Executive Desk, Dual Interviewer Chairs, Glass Partition, AC"),
        ("Interview Cabin Beta (102)", "Interview Cabin", 6, "Placement Tower", "3rd Floor", "Executive Desk, Video Conferencing Rig, AC"),
        ("Interview Cabin Gamma (103)", "Interview Cabin", 6, "Placement Tower", "3rd Floor", "Interview Table, Panel Seating, High-speed Wi-Fi, AC"),
        ("C.V. Raman Multi-Purpose Hall", "Auditorium", 300, "Science & Humanities Block", "Ground Floor", "Acoustic Panels, Projection Screen, PA System, AC")
    ]
    cursor.executemany("""
        INSERT INTO venues (name, type, capacity, block, floor, equipment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, venues)

    # 2. Insert Placement Drives
    drives = [
        ("Google Cloud India", "Software Engineer - Campus", 28.5, "Super Dream", "2026-09-24", 8.0, 0, "CSE,IT,ECE", "Bangalore / Hyderabad", "Neha Sharma", "neha.recruitment@google.com", "+91 98112 34567", "Scheduled", "Full-time software engineering role for distributed systems and cloud applications."),
        ("Microsoft IDC", "Software Development Engineer (SDE-1)", 32.0, "Super Dream", "2026-09-26", 8.2, 0, "CSE,IT", "Hyderabad / Noida", "Rohan Mehta", "rmehta@microsoft.com", "+91 98450 11223", "Scheduled", "Hiring for Azure and Office 365 core engineering divisions."),
        ("Texas Instruments", "Analog & Embedded Systems Design Engineer", 18.0, "Dream", "2026-09-28", 7.5, 0, "ECE,EEE", "Bangalore", "Karthik Subramanian", "karthik.s@ti.com", "+91 97410 99881", "Scheduled", "VLSI design, embedded firmware, and board level verification."),
        ("Tata Consultancy Services (TCS)", "Systems Engineer (Digital & Prime)", 9.0, "Core / IT", "2026-10-02", 6.5, 1, "CSE,IT,ECE,EEE,MECH,CIVIL", "Pan India", "Priya Nambiar", "priya.n@tcs.com", "+91 99001 22334", "Scheduled", "Mass recruitment drive for Digital Transformation and Prime technical wings."),
        ("Larsen & Toubro (L&T)", "Graduate Engineer Trainee (GET)", 7.5, "Core / IT", "2026-10-05", 6.5, 0, "MECH,CIVIL,EEE", "Mumbai / Chennai / Site", "Anand Kulkarni", "anand.k@larsentoubro.com", "+91 94220 55443", "Scheduled", "EPC project engineering, structural execution, and design analysis.")
    ]

    for d in drives:
        cursor.execute("""
            INSERT INTO drives (company_name, role, ctc_lpa, category, drive_date, min_cgpa, allowed_backlogs, eligible_branches, job_location, contact_person, contact_email, contact_phone, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, d)
        drive_id = cursor.lastrowid

        # Insert Standard Multi-Rounds for this drive
        rounds = [
            (drive_id, "Pre-Placement Talk (PPT)", 1, d[4], "09:00", "10:30", "Scheduled"),
            (drive_id, "Online Aptitude & Coding Test", 2, d[4], "11:00", "13:00", "Scheduled"),
            (drive_id, "Technical Interview Round 1", 3, d[4], "14:00", "17:00", "Scheduled"),
            (drive_id, "HR & Final Interview", 4, d[4], "17:30", "19:00", "Scheduled")
        ]
        cursor.executemany("""
            INSERT INTO drive_rounds (drive_id, round_name, round_order, round_date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rounds)

    # 3. Insert Students (25 realistic records across branches)
    students = [
        ("1MS22CS001", "Aarav Sharma", "aarav.sharma@college.edu", "+91 91234 56780", "CSE", 9.42, 0, 2026, "Unplaced", None, None),
        ("1MS22CS014", "Ananya Deshmukh", "ananya.d@college.edu", "+91 91234 56781", "CSE", 8.85, 0, 2026, "Unplaced", None, None),
        ("1MS22CS025", "Devansh Nair", "devansh.n@college.edu", "+91 91234 56782", "CSE", 8.10, 0, 2026, "Unplaced", None, None),
        ("1MS22CS042", "Ishita Gupta", "ishita.g@college.edu", "+91 91234 56783", "CSE", 7.65, 0, 2026, "Unplaced", None, None),
        ("1MS22CS089", "Karan Patel", "karan.p@college.edu", "+91 91234 56784", "CSE", 6.80, 1, 2026, "Unplaced", None, None),
        
        ("1MS22IS005", "Meera Krishnan", "meera.k@college.edu", "+91 92345 67890", "IT", 9.15, 0, 2026, "Unplaced", None, None),
        ("1MS22IS019", "Nikhil Verma", "nikhil.v@college.edu", "+91 92345 67891", "IT", 8.40, 0, 2026, "Unplaced", None, None),
        ("1MS22IS033", "Pooja Reddy", "pooja.r@college.edu", "+91 92345 67892", "IT", 7.90, 0, 2026, "Unplaced", None, None),
        ("1MS22IS048", "Rahul Sen", "rahul.s@college.edu", "+91 92345 67893", "IT", 6.45, 0, 2026, "Unplaced", None, None),
        
        ("1MS22EC003", "Aditi Rao", "aditi.rao@college.edu", "+91 93456 78901", "ECE", 8.90, 0, 2026, "Unplaced", None, None),
        ("1MS22EC018", "Gaurav Joshi", "gaurav.j@college.edu", "+91 93456 78902", "ECE", 8.20, 0, 2026, "Unplaced", None, None),
        ("1MS22EC027", "Harini Venkat", "harini.v@college.edu", "+91 93456 78903", "ECE", 7.75, 0, 2026, "Unplaced", None, None),
        ("1MS22EC045", "Manish Tiwari", "manish.t@college.edu", "+91 93456 78904", "ECE", 6.90, 1, 2026, "Unplaced", None, None),

        ("1MS22EE008", "Kavya Murthy", "kavya.m@college.edu", "+91 94567 89012", "EEE", 8.35, 0, 2026, "Unplaced", None, None),
        ("1MS22EE015", "Rohan Pillai", "rohan.p@college.edu", "+91 94567 89013", "EEE", 7.45, 0, 2026, "Unplaced", None, None),
        ("1MS22EE030", "Sneha Hegde", "sneha.h@college.edu", "+91 94567 89014", "EEE", 6.70, 0, 2026, "Unplaced", None, None),

        ("1MS22ME002", "Abhishek Menon", "abhishek.m@college.edu", "+91 95678 90123", "MECH", 8.60, 0, 2026, "Unplaced", None, None),
        ("1MS22ME014", "Deepak Saxena", "deepak.s@college.edu", "+91 95678 90124", "MECH", 7.80, 0, 2026, "Unplaced", None, None),
        ("1MS22ME029", "Karthik Gowda", "karthik.g@college.edu", "+91 95678 90125", "MECH", 6.95, 0, 2026, "Unplaced", None, None),
        ("1MS22ME041", "Pranav Das", "pranav.d@college.edu", "+91 95678 90126", "MECH", 6.20, 2, 2026, "Unplaced", None, None),

        ("1MS22CV006", "Divya Shetty", "divya.s@college.edu", "+91 96789 01234", "CIVIL", 8.15, 0, 2026, "Unplaced", None, None),
        ("1MS22CV021", "Naveen Raj", "naveen.r@college.edu", "+91 96789 01235", "CIVIL", 7.50, 0, 2026, "Unplaced", None, None),
        ("1MS22CV034", "Suresh Patil", "suresh.p@college.edu", "+91 96789 01236", "CIVIL", 6.60, 1, 2026, "Unplaced", None, None),
        
        ("1MS22CS102", "Siddharth Bhat", "sid.bhat@college.edu", "+91 97890 12345", "CSE", 9.65, 0, 2026, "Placed", "Amazon AWS", 45.0),
        ("1MS22IS091", "Tanvi Agarwal", "tanvi.a@college.edu", "+91 98901 23456", "IT", 9.30, 0, 2026, "Placed", "Cisco Systems", 24.0)
    ]
    cursor.executemany("""
        INSERT INTO students (usn, name, email, phone, branch, cgpa, backlogs, passing_year, placement_status, placed_company, package_lpa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, students)

    # 4. Insert Career Guidance Events
    guidance_events = [
        ("Ace the Coding Assessment: DSA & LeetCode Patterns", "Saurabh Mukherjee", "Senior SDE @ Atlassian", "2026-09-23", "14:00", "16:30", 2, "CSE, IT & ECE 3rd & 4th Years", "Upcoming", "Intensive problem-solving workshop on Trees, Graphs, and Dynamic Programming."),
        ("Resume Building & Executive LinkedIn Presence", "Pooja Banerjee", "Lead HR Business Partner", "2026-09-25", "10:00", "12:00", 1, "All Branches 2026 Batch", "Upcoming", "ATS-compliant resume design, STAR framework, and LinkedIn outreach secrets."),
        ("Mock Technical Interviews & System Design Clinic", "Vikramaditya Roy", "Ex-Google Staff Engineer", "2026-09-27", "09:30", "13:00", 7, "Shortlisted candidates for Super Dream drives", "Upcoming", "One-on-one simulated interviews with real-time feedback and rubric scoring."),
        ("Core Engineering Careers in Renewable Energy & EV", "Dr. H.S. Nagaraj", "Director, Tech Advisory", "2026-09-29", "15:00", "17:00", 10, "MECH, EEE, CIVIL Students", "Upcoming", "Roadmap to cracking interviews in EV, battery tech, and modern infrastructure.")
    ]
    cursor.executemany("""
        INSERT INTO guidance_events (title, trainer_name, trainer_org, event_date, start_time, end_time, venue_id, target_audience, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, guidance_events)

    # 5. Insert Initial Room Allocations
    # Google Drive on 2026-09-24:
    # Round 1 (PPT): Kalam Auditorium (1) 09:00 - 10:30
    # Round 2 (Online Test): Ada Lovelace Lab 1 (3) 11:00 - 13:00
    # Round 3 (Tech Interviews): Interview Cabin Alpha (7) 14:00 - 17:00
    allocations = [
        (1, 1, None, "Placement Drive", "2026-09-24", "09:00", "10:30", "Prof. R. Sundaram", "Audio-visual check at 08:30 AM required"),
        (3, 2, None, "Placement Drive", "2026-09-24", "11:00", "13:00", "Lab Admin Suresh", "Assigned 120 systems with secure browser lockdown"),
        (7, 3, None, "Placement Drive", "2026-09-24", "14:00", "17:00", "Dr. S. K. Mitra", "Panel 1 technical interview room"),
        # Guidance event on 2026-09-25:
        (1, None, 2, "Career Guidance", "2026-09-25", "10:00", "12:00", "Placement Officer", "Open house for all 2026 passing out batch")
    ]
    cursor.executemany("""
        INSERT INTO room_allocations (venue_id, drive_round_id, guidance_event_id, purpose, date, start_time, end_time, invigilator, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, allocations)

    conn.commit()
    conn.close()

# Helper queries
def get_all_venues():
    conn = get_db()
    venues = conn.execute("SELECT * FROM venues ORDER BY type, name").fetchall()
    conn.close()
    return [dict(v) for v in venues]

def get_all_drives():
    conn = get_db()
    drives = conn.execute("""
        SELECT d.*, 
            (SELECT COUNT(*) FROM drive_rounds WHERE drive_id = d.id) as round_count,
            (SELECT COUNT(*) FROM room_allocations ra 
             JOIN drive_rounds dr ON ra.drive_round_id = dr.id 
             WHERE dr.drive_id = d.id) as allocated_rooms_count
        FROM drives d 
        ORDER BY d.drive_date ASC, d.id DESC
    """).fetchall()
    conn.close()
    return [dict(d) for d in drives]

def get_drive_details(drive_id):
    conn = get_db()
    drive = conn.execute("SELECT * FROM drives WHERE id = ?", (drive_id,)).fetchone()
    if not drive:
        conn.close()
        return None
    drive_dict = dict(drive)
    
    rounds = conn.execute("""
        SELECT dr.*, 
               ra.id as allocation_id,
               ra.venue_id,
               v.name as venue_name,
               v.type as venue_type,
               v.capacity as venue_capacity,
               ra.date as allocated_date,
               ra.start_time as allocated_start_time,
               ra.end_time as allocated_end_time,
               ra.invigilator
        FROM drive_rounds dr
        LEFT JOIN room_allocations ra ON dr.id = ra.drive_round_id
        LEFT JOIN venues v ON ra.venue_id = v.id
        WHERE dr.drive_id = ?
        ORDER BY dr.round_order ASC
    """, (drive_id,)).fetchall()
    
    drive_dict["rounds"] = [dict(r) for r in rounds]
    conn.close()
    return drive_dict

def get_allocations_for_clash_check():
    conn = get_db()
    rows = conn.execute("""
        SELECT ra.id, ra.venue_id, ra.date, ra.start_time, ra.end_time,
               v.name as venue_name,
               d.company_name,
               dr.round_name,
               ge.title as event_title
        FROM room_allocations ra
        JOIN venues v ON ra.venue_id = v.id
        LEFT JOIN drive_rounds dr ON ra.drive_round_id = dr.id
        LEFT JOIN drives d ON dr.drive_id = d.id
        LEFT JOIN guidance_events ge ON ra.guidance_event_id = ge.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_allocations_detailed(target_date=None):
    conn = get_db()
    query = """
        SELECT ra.*, 
               v.name as venue_name, v.type as venue_type, v.capacity as venue_capacity,
               v.block as venue_block, v.floor as venue_floor,
               d.company_name, d.role as company_role, d.category as company_category,
               dr.round_name,
               ge.title as event_title, ge.trainer_name
        FROM room_allocations ra
        JOIN venues v ON ra.venue_id = v.id
        LEFT JOIN drive_rounds dr ON ra.drive_round_id = dr.id
        LEFT JOIN drives d ON dr.drive_id = d.id
        LEFT JOIN guidance_events ge ON ra.guidance_event_id = ge.id
    """
    params = []
    if target_date:
        query += " WHERE ra.date = ?"
        params.append(target_date)
    query += " ORDER BY ra.date DESC, ra.start_time ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_eligible_students(drive_id):
    conn = get_db()
    drive = conn.execute("SELECT min_cgpa, allowed_backlogs, eligible_branches FROM drives WHERE id = ?", (drive_id,)).fetchone()
    if not drive:
        conn.close()
        return []
    
    min_cgpa = drive["min_cgpa"]
    max_backlogs = drive["allowed_backlogs"]
    branches = [b.strip() for b in drive["eligible_branches"].split(",") if b.strip()]
    
    placeholders = ",".join(["?"] * len(branches))
    query = f"""
        SELECT * FROM students 
        WHERE cgpa >= ? 
          AND backlogs <= ? 
          AND branch IN ({placeholders})
        ORDER BY cgpa DESC, name ASC
    """
    params = [min_cgpa, max_backlogs] + branches
    students = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(s) for s in students]

def get_kpis():
    conn = get_db()
    total_drives = conn.execute("SELECT COUNT(*) FROM drives").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    placed_students = conn.execute("SELECT COUNT(*) FROM students WHERE placement_status IN ('Placed', 'Dream Placed', 'Offered')").fetchone()[0]
    avg_package = conn.execute("SELECT AVG(package_lpa) FROM students WHERE package_lpa IS NOT NULL").fetchone()[0] or 0.0
    highest_package = conn.execute("SELECT MAX(package_lpa) FROM students WHERE package_lpa IS NOT NULL").fetchone()[0] or 0.0
    total_venues = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
    upcoming_guidance = conn.execute("SELECT COUNT(*) FROM guidance_events WHERE status = 'Upcoming'").fetchone()[0]
    
    # Branch-wise placement stats
    branch_stats = conn.execute("""
        SELECT branch, 
               COUNT(*) as total,
               SUM(CASE WHEN placement_status != 'Unplaced' THEN 1 ELSE 0 END) as placed
        FROM students 
        GROUP BY branch
    """).fetchall()

    conn.close()
    return {
        "total_drives": total_drives,
        "total_students": total_students,
        "placed_students": placed_students,
        "placement_pct": round((placed_students / total_students * 100), 1) if total_students else 0,
        "avg_package": round(avg_package, 2),
        "highest_package": round(highest_package, 2),
        "total_venues": total_venues,
        "upcoming_guidance": upcoming_guidance,
        "branch_stats": [dict(b) for b in branch_stats]
    }
