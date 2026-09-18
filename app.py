"""
Flask Application for Career Guidance & Placement Cell SHRM
Handles placement drive pipelines, venue allotments, conflict detection,
student eligibility screening, and placement metrics.
"""
import os
import csv
import io
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_cors import CORS

import models
from clash_detector import check_venue_clash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shrm-placement-secret-key-2026'
CORS(app)

# Ensure DB initialized on startup (clean without dummy data)
with app.app_context():
    models.init_db()

# ==========================================
# Template Filters & Context
# ==========================================
@app.context_processor
def inject_now():
    return {
        'current_date': date.today().strftime('%Y-%m-%d'),
        'current_year': datetime.now().year
    }

# ==========================================
# Web Page Routes (HTML)
# ==========================================
@app.route('/')
def index():
    kpis = models.get_kpis()
    today_str = date.today().strftime('%Y-%m-%d')
    upcoming_drives = models.get_all_drives()[:5]
    all_allocations = models.get_all_allocations_detailed()[:6]
    venues = models.get_all_venues()
    return render_template(
        'index.html',
        kpis=kpis,
        upcoming_drives=upcoming_drives,
        allocations=all_allocations,
        venues=venues,
        active_page='dashboard'
    )

@app.route('/drives')
def drives_page():
    drives = models.get_all_drives()
    venues = models.get_all_venues()
    return render_template('drives.html', drives=drives, venues=venues, active_page='drives')

@app.route('/drives/<int:drive_id>')
def drive_detail_page(drive_id):
    drive = models.get_drive_details(drive_id)
    if not drive:
        return redirect(url_for('drives_page'))
    eligible_students = models.get_eligible_students(drive_id)
    venues = models.get_all_venues()
    return render_template('drive_detail.html', drive=drive, eligible_students=eligible_students, venues=venues, active_page='drives')

@app.route('/room-allotment')
def room_allotment_page():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    venues = models.get_all_venues()
    allocations = models.get_all_allocations_detailed(target_date=selected_date)
    drives = models.get_all_drives()
    
    # Get all unassigned or all rounds for quick picker
    conn = models.get_db()
    rounds = conn.execute("""
        SELECT dr.id, dr.round_name, dr.round_date, dr.start_time, dr.end_time,
               d.company_name, d.role, d.drive_date
        FROM drive_rounds dr
        JOIN drives d ON dr.drive_id = d.id
        ORDER BY dr.round_date ASC, dr.id ASC
    """).fetchall()
    conn.close()
    
    return render_template(
        'room_allotment.html',
        venues=venues,
        allocations=allocations,
        selected_date=selected_date,
        drives=drives,
        rounds=[dict(r) for r in rounds],
        active_page='rooms'
    )

@app.route('/students')
def students_page():
    branch = request.args.get('branch', '')
    min_cgpa = request.args.get('min_cgpa', '')
    status = request.args.get('status', '')
    
    conn = models.get_db()
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    if branch:
        query += " AND branch = ?"
        params.append(branch)
    if min_cgpa:
        try:
            query += " AND cgpa >= ?"
            params.append(float(min_cgpa))
        except ValueError:
            pass
    if status:
        query += " AND placement_status = ?"
        params.append(status)
        
    query += " ORDER BY cgpa DESC, name ASC"
    students = conn.execute(query, params).fetchall()
    conn.close()
    
    drives = models.get_all_drives()
    return render_template(
        'students.html',
        students=[dict(s) for s in students],
        drives=drives,
        active_page='students',
        filter_branch=branch,
        filter_cgpa=min_cgpa,
        filter_status=status
    )

@app.route('/guidance')
def guidance_page():
    conn = models.get_db()
    events = conn.execute("""
        SELECT ge.*, v.name as venue_name, v.capacity as venue_capacity, v.block as venue_block
        FROM guidance_events ge
        LEFT JOIN venues v ON ge.venue_id = v.id
        ORDER BY ge.event_date ASC, ge.start_time ASC
    """).fetchall()
    conn.close()
    venues = models.get_all_venues()
    return render_template('guidance.html', events=[dict(e) for e in events], venues=venues, active_page='guidance')

def get_req_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()

# ==========================================
# REST API Endpoints
# ==========================================
@app.route('/api/kpis')
def api_kpis():
    return jsonify(models.get_kpis())

@app.route('/api/venues', methods=['GET', 'POST'])
def api_venues():
    if request.method == 'GET':
        return jsonify(models.get_all_venues())
    
    data = get_req_data()
    name = data.get('name', '').strip()
    vtype = data.get('type', 'Seminar Hall').strip()
    capacity = int(data.get('capacity', 50))
    block = data.get('block', 'Main Block').strip()
    floor = data.get('floor', 'Ground Floor').strip()
    equipment = data.get('equipment', 'Projector, AC').strip()

    if not name:
        return jsonify({'error': 'Venue name is required'}), 400

    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO venues (name, type, capacity, block, floor, equipment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, vtype, capacity, block, floor, equipment))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': new_id, 'message': 'Venue added successfully'}), 201

@app.route('/api/venues/<int:venue_id>', methods=['DELETE'])
def api_delete_venue(venue_id):
    models.delete_venue(venue_id)
    return jsonify({'success': True, 'message': 'Campus venue deleted'})

@app.route('/api/admin/clear-data', methods=['POST'])
def api_clear_data():
    data = get_req_data()
    clear_venues = data.get('clear_venues') in [True, 'true', '1', 1]
    models.clear_all_data(clear_venues=clear_venues)
    return jsonify({'success': True, 'message': 'All placement data cleared successfully'})

@app.route('/api/admin/seed-sample-data', methods=['POST'])
def api_seed_data():
    models.seed_sample_data()
    return jsonify({'success': True, 'message': 'Sample demo data loaded successfully'})

@app.route('/api/admin/add-default-venues', methods=['POST'])
def api_add_default_venues():
    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM venues")
    if cursor.fetchone()[0] == 0:
        default_venues = [
            ("Main Auditorium", "Auditorium", 500, "Admin Block", "Ground Floor", "Projector, Sound System, Dual Mics, AC"),
            ("Seminar Hall 1", "Seminar Hall", 150, "Academic Block", "1st Floor", "Smart Display, Wireless Mic, AC"),
            ("Computer Center Lab 1", "Computer Lab", 100, "Tech Block", "2nd Floor", "100 Workstations, LAN, UPS Backup, AC"),
            ("Group Discussion Room", "GD Room", 20, "Placement Wing", "3rd Floor", "Conference Table, Whiteboard, AC"),
            ("Interview Cabin 1", "Interview Cabin", 6, "Placement Wing", "3rd Floor", "Interview Table, Panel Chairs, Wi-Fi, AC")
        ]
        cursor.executemany("""
            INSERT INTO venues (name, type, capacity, block, floor, equipment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, default_venues)
        conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Standard campus venues created'})

@app.route('/api/drives', methods=['GET', 'POST'])
def api_drives():
    if request.method == 'GET':
        return jsonify(models.get_all_drives())
        
    data = get_req_data()
    company_name = data.get('company_name', '').strip()
    role = data.get('role', '').strip()
    ctc_lpa = float(data.get('ctc_lpa', 0.0))
    category = data.get('category', 'Core / IT').strip()
    drive_date = data.get('drive_date', '').strip()
    min_cgpa = float(data.get('min_cgpa', 6.0))
    allowed_backlogs = int(data.get('allowed_backlogs', 0))
    eligible_branches = data.get('eligible_branches', 'CSE,IT,ECE')
    if isinstance(eligible_branches, list):
        eligible_branches = ",".join(eligible_branches)
    job_location = data.get('job_location', 'Bangalore').strip()
    contact_person = data.get('contact_person', '').strip()
    contact_email = data.get('contact_email', '').strip()
    contact_phone = data.get('contact_phone', '').strip()
    description = data.get('description', '').strip()

    if not company_name or not role or not drive_date:
        return jsonify({'error': 'Company name, role, and drive date are required.'}), 400

    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO drives (company_name, role, ctc_lpa, category, drive_date, min_cgpa, allowed_backlogs, eligible_branches, job_location, contact_person, contact_email, contact_phone, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Scheduled', ?)
    """, (company_name, role, ctc_lpa, category, drive_date, min_cgpa, allowed_backlogs, eligible_branches, job_location, contact_person, contact_email, contact_phone, description))
    drive_id = cursor.lastrowid

    # Auto-generate standard 4 rounds for recruitment
    standard_rounds = [
        (drive_id, "Pre-Placement Talk (PPT)", 1, drive_date, "09:00", "10:30", "Scheduled"),
        (drive_id, "Online Aptitude / Technical Test", 2, drive_date, "11:00", "12:30", "Scheduled"),
        (drive_id, "Technical Interview (Round 1)", 3, drive_date, "13:30", "16:30", "Scheduled"),
        (drive_id, "HR & Management Interview", 4, drive_date, "17:00", "18:30", "Scheduled")
    ]
    cursor.executemany("""
        INSERT INTO drive_rounds (drive_id, round_name, round_order, round_date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, standard_rounds)

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'id': drive_id, 'message': 'Placement drive and rounds scheduled successfully.'}), 201

@app.route('/api/drives/<int:drive_id>', methods=['GET', 'PUT', 'DELETE'])
def api_drive_item(drive_id):
    if request.method == 'GET':
        d = models.get_drive_details(drive_id)
        if not d:
            return jsonify({'error': 'Drive not found'}), 404
        return jsonify(d)

    if request.method == 'PUT':
        data = get_req_data()
        status = data.get('status')
        conn = models.get_db()
        conn.execute("UPDATE drives SET status = ? WHERE id = ?", (status, drive_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Drive status updated'})

    if request.method == 'DELETE':
        conn = models.get_db()
        conn.execute("DELETE FROM drives WHERE id = ?", (drive_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Drive removed'})

@app.route('/api/drives/<int:drive_id>/rounds', methods=['POST'])
def api_add_round(drive_id):
    data = get_req_data()
    round_name = data.get('round_name')
    round_order = int(data.get('round_order', 1))
    round_date = data.get('round_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not round_name or not round_date or not start_time or not end_time:
        return jsonify({'error': 'Round details missing'}), 400

    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO drive_rounds (drive_id, round_name, round_order, round_date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Scheduled')
    """, (drive_id, round_name, round_order, round_date, start_time, end_time))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Round added successfully'})

# ==========================================
# Clash Check & Room Allotment APIs
# ==========================================
@app.route('/api/allocations/check-clash', methods=['POST'])
def api_check_clash():
    """
    Simulates / checks whether a proposed room booking creates a clash.
    Useful for live validation in UI before clicking submit.
    """
    data = get_req_data()
    venue_id = data.get('venue_id')
    alloc_date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    exclude_id = data.get('exclude_id')
    if exclude_id:
        try:
            exclude_id = int(exclude_id)
        except ValueError:
            exclude_id = None

    if not venue_id or not alloc_date or not start_time or not end_time:
        return jsonify({'has_clash': False, 'message': 'Incomplete data for check'}), 200

    existing_allocations = models.get_allocations_for_clash_check()
    clash_result = check_venue_clash(
        existing_allocations,
        target_venue_id=int(venue_id),
        target_date=alloc_date,
        target_start=start_time,
        target_end=end_time,
        exclude_id=exclude_id
    )
    return jsonify(clash_result)

@app.route('/api/allocations', methods=['GET', 'POST'])
def api_allocations():
    if request.method == 'GET':
        target_date = request.args.get('date')
        return jsonify(models.get_all_allocations_detailed(target_date))

    data = get_req_data()
    raw_vid = data.get('venue_id')
    if not raw_vid:
        return jsonify({'error': 'Please select a venue'}), 400
    try:
        venue_id = int(raw_vid)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid venue ID'}), 400

    alloc_date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    purpose = data.get('purpose', 'Placement Drive').strip()
    drive_round_id = data.get('drive_round_id')
    if drive_round_id and str(drive_round_id).strip():
        drive_round_id = int(drive_round_id)
    else:
        drive_round_id = None
        
    guidance_event_id = data.get('guidance_event_id')
    if guidance_event_id and str(guidance_event_id).strip():
        guidance_event_id = int(guidance_event_id)
    else:
        guidance_event_id = None
        
    invigilator = data.get('invigilator', '').strip()
    notes = data.get('notes', '').strip()

    # 1. Run Real-time Clash Check
    existing_allocations = models.get_allocations_for_clash_check()
    clash_result = check_venue_clash(
        existing_allocations,
        target_venue_id=venue_id,
        target_date=alloc_date,
        target_start=start_time,
        target_end=end_time
    )

    if clash_result["has_clash"]:
        # Block double booking and return 409 Conflict
        return jsonify({
            'success': False,
            'error': 'ROOM_CLASH',
            'message': clash_result["message"],
            'conflict': clash_result.get("conflict")
        }), 409

    # 2. Persist Allocation
    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO room_allocations (venue_id, drive_round_id, guidance_event_id, purpose, date, start_time, end_time, invigilator, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (venue_id, drive_round_id, guidance_event_id, purpose, alloc_date, start_time, end_time, invigilator, notes))
    conn.commit()
    alloc_id = cursor.lastrowid
    conn.close()

    return jsonify({
        'success': True,
        'id': alloc_id,
        'message': 'Room allotted successfully without conflicts!'
    }), 201

@app.route('/api/allocations/<int:alloc_id>', methods=['DELETE'])
def api_delete_allocation(alloc_id):
    conn = models.get_db()
    conn.execute("DELETE FROM room_allocations WHERE id = ?", (alloc_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Room allotment cancelled successfully'})

# ==========================================
# Student Management & Eligibility APIs
# ==========================================
@app.route('/api/students', methods=['GET', 'POST'])
def api_students():
    if request.method == 'GET':
        conn = models.get_db()
        students = conn.execute("SELECT * FROM students ORDER BY cgpa DESC").fetchall()
        conn.close()
        return jsonify([dict(s) for s in students])

    data = get_req_data()
    usn = data.get('usn', '').strip().upper()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    branch = data.get('branch', 'CSE').strip().upper()
    cgpa = float(data.get('cgpa', 0.0))
    backlogs = int(data.get('backlogs', 0))
    passing_year = int(data.get('passing_year', 2026))

    if not usn or not name or not email:
        return jsonify({'error': 'USN, Name and Email are required'}), 400

    conn = models.get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (usn, name, email, phone, branch, cgpa, backlogs, passing_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (usn, name, email, phone, branch, cgpa, backlogs, passing_year))
        conn.commit()
        sid = cursor.lastrowid
        conn.close()
        return jsonify({'success': True, 'id': sid, 'message': 'Student registered successfully'}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Could not register student: {str(e)}'}), 400

@app.route('/api/drives/<int:drive_id>/eligible-students')
def api_eligible_students(drive_id):
    students = models.get_eligible_students(drive_id)
    return jsonify(students)

@app.route('/api/drives/<int:drive_id>/export-eligible')
def export_eligible_csv(drive_id):
    drive = models.get_drive_details(drive_id)
    if not drive:
        return "Drive not found", 404
        
    students = models.get_eligible_students(drive_id)
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['USN', 'Student Name', 'Branch', 'CGPA', 'Active Backlogs', 'Email', 'Phone', 'Placement Status'])
    for s in students:
        cw.writerow([s['usn'], s['name'], s['branch'], s['cgpa'], s['backlogs'], s['email'], s.get('phone', ''), s['placement_status']])
        
    output = si.getvalue()
    filename = f"Eligible_Students_{drive['company_name'].replace(' ', '_')}_{drive['drive_date']}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# ==========================================
# Career Guidance APIs
# ==========================================
@app.route('/api/guidance', methods=['GET', 'POST'])
def api_guidance():
    if request.method == 'GET':
        conn = models.get_db()
        events = conn.execute("SELECT * FROM guidance_events ORDER BY event_date ASC").fetchall()
        conn.close()
        return jsonify([dict(e) for e in events])

    data = get_req_data()
    title = data.get('title', '').strip()
    trainer_name = data.get('trainer_name', '').strip()
    trainer_org = data.get('trainer_org', '').strip()
    event_date = data.get('event_date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    venue_id = data.get('venue_id')
    venue_id = int(venue_id) if venue_id else None
    target_audience = data.get('target_audience', 'All Students').strip()
    description = data.get('description', '').strip()

    if not title or not trainer_name or not event_date or not start_time or not end_time:
        return jsonify({'error': 'Required fields missing'}), 400

    # If venue is requested, check clash
    if venue_id:
        existing = models.get_allocations_for_clash_check()
        clash = check_venue_clash(existing, venue_id, event_date, start_time, end_time)
        if clash['has_clash']:
            return jsonify({'error': 'ROOM_CLASH', 'message': clash['message']}), 409

    conn = models.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO guidance_events (title, trainer_name, trainer_org, event_date, start_time, end_time, venue_id, target_audience, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, trainer_name, trainer_org, event_date, start_time, end_time, venue_id, target_audience, description))
    ge_id = cursor.lastrowid

    # If venue allotted, also add to room_allocations
    if venue_id:
        cursor.execute("""
            INSERT INTO room_allocations (venue_id, guidance_event_id, purpose, date, start_time, end_time, invigilator, notes)
            VALUES (?, ?, 'Career Guidance', ?, ?, ?, ?, ?)
        """, (venue_id, ge_id, event_date, start_time, end_time, trainer_name, f"Guidance: {title}"))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': ge_id, 'message': 'Career Guidance Workshop scheduled'}), 201

if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    port = int(os.environ.get('PORT', 5000))
    print("===========================================================")
    print(">>> SHRM Placement Cell & Room Allotment Web App is running!")
    print(f">>> Access Web App at: http://127.0.0.1:{port}")
    print("===========================================================")
    app.run(host='0.0.0.0', port=port, debug=False)
