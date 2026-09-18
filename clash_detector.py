"""
Venue Clash Detection Engine
Detects time-slot overlaps for campus venues (Auditoriums, Labs, Interview Cabins)
to prevent double booking during placement drives and career guidance events.
"""
from datetime import datetime

def parse_time(time_str):
    """Parses HH:MM or HH:MM:SS string to minutes from midnight for quick comparison."""
    if not time_str:
        return 0
    parts = [int(p) for p in time_str.strip().split(":")[:2]]
    return parts[0] * 60 + parts[1]

def times_overlap(start_a, end_a, start_b, end_b):
    """
    Checks if interval [start_a, end_a] overlaps with [start_b, end_b].
    Returns True if there is an overlap, False otherwise.
    Note: Consecutive slots (e.g. 10:00-11:00 and 11:00-12:00) do NOT overlap.
    """
    sa = parse_time(start_a)
    ea = parse_time(end_a)
    sb = parse_time(start_b)
    eb = parse_time(end_b)
    
    # Validation: start must be before end
    if sa >= ea or sb >= eb:
        return False
        
    # Standard interval intersection condition: A starts before B ends AND B starts before A ends
    return sa < eb and sb < ea

def check_venue_clash(existing_allocations, target_venue_id, target_date, target_start, target_end, exclude_id=None):
    """
    Evaluates a candidate room booking against existing allocations.
    
    Args:
        existing_allocations: List of dicts/rows containing:
            - id: allocation id
            - venue_id: integer
            - date: YYYY-MM-DD
            - start_time: HH:MM
            - end_time: HH:MM
            - company_name: string (optional)
            - round_name: string (optional)
            - event_title: string (optional)
            - venue_name: string (optional)
        target_venue_id: Venue to check
        target_date: Date string (YYYY-MM-DD)
        target_start: Start time (HH:MM)
        target_end: End time (HH:MM)
        exclude_id: Optional ID to exclude (e.g. when updating existing)
        
    Returns:
        dict: {
            "has_clash": bool,
            "conflict": dict or None,
            "message": str
        }
    """
    # Check start before end
    if parse_time(target_start) >= parse_time(target_end):
        return {
            "has_clash": True,
            "conflict": None,
            "message": "Start time must be strictly earlier than end time."
        }

    for alloc in existing_allocations:
        if exclude_id is not None and alloc.get("id") == exclude_id:
            continue
            
        if int(alloc.get("venue_id")) == int(target_venue_id) and str(alloc.get("date")).strip() == str(target_date).strip():
            if times_overlap(target_start, target_end, alloc.get("start_time"), alloc.get("end_time")):
                venue_name = alloc.get("venue_name") or f"Venue #{target_venue_id}"
                event_desc = alloc.get("company_name", "")
                if alloc.get("round_name"):
                    event_desc += f" ({alloc.get('round_name')})"
                elif alloc.get("event_title"):
                    event_desc = alloc.get("event_title")
                else:
                    event_desc = "Another Scheduled Event"
                    
                msg = (
                    f"Room Clash Detected! {venue_name} is already booked on {target_date} "
                    f"from {alloc.get('start_time')} to {alloc.get('end_time')} for '{event_desc}'."
                )
                return {
                    "has_clash": True,
                    "conflict": alloc,
                    "message": msg
                }
                
    return {
        "has_clash": False,
        "conflict": None,
        "message": "Venue is available for the requested time slot."
    }
