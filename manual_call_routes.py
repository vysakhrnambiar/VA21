# manual_call_routes.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import json
import time
import sqlite3
from typing import Optional
from datetime import datetime, timedelta

# --- Router Setup ---
router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend/manual_call"))

# --- Logging ---
def log_manual_call(msg: str):
    print(f"[MANUAL_CALL] {time.strftime('%Y-%m-%d %H:%M:%S')} {msg}")

# --- Database Functions ---
def create_manual_call_request(contact_name: str, phone_number: str,
                               company_name: Optional[str], call_purpose: str, urgency: str,
                               scheduled_time: Optional[str] = None, timezone_offset: Optional[int] = None,
                               notes: Optional[str] = None):
    """
    Add a manually created call request to the scheduled_calls database.
    This creates an outbound call from the agent to a customer who previously
    requested information from the specified company. If no company is specified,
    DTC Executive Office will be used as the default.

    If scheduled_time is provided, it will be used as the scheduled time for the call,
    taking into account the timezone_offset from UTC in minutes.
    If not provided, the call will be scheduled based on urgency.
    """
    try:
        conn = sqlite3.connect('scheduled_calls.db')
        cursor = conn.cursor()
        
        # Status is always PENDING for new calls
        status = "PENDING"
        
        # Get current timestamp
        now = datetime.now()
        
        # Set next_retry_at based on scheduled_time if provided, otherwise use urgency
        next_retry = None
        
        if scheduled_time and scheduled_time.strip():
            try:
                # Parse the scheduled time from input format
                scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                
                # Apply timezone offset if provided (convert from local time to UTC)
                # Note: getTimezoneOffset() returns minutes WEST of UTC, so we add it to convert to UTC
                if timezone_offset is not None:
                    # Convert timezone_offset from minutes to a timedelta
                    tz_delta = timedelta(minutes=timezone_offset)
                    # Add the offset to adjust from local time to UTC
                    scheduled_dt = scheduled_dt + tz_delta
                
                # Format for database
                next_retry = scheduled_dt.strftime('%Y-%m-%d %H:%M:%S')
                log_manual_call(f"Using custom scheduled time: {next_retry} (original input: {scheduled_time}, timezone offset: {timezone_offset})")
            except (ValueError, TypeError) as e:
                # If there's an error with the scheduled time, fall back to urgency-based scheduling
                log_manual_call(f"Error parsing scheduled time '{scheduled_time}': {str(e)}. Falling back to urgency-based scheduling.")
                next_retry = None
        
        # If no valid scheduled time was provided, use urgency-based scheduling
        if next_retry is None:
            if urgency == "urgent":
                next_retry = now.strftime('%Y-%m-%d %H:%M:%S')  # Immediate
            elif urgency == "high":
                next_retry = (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            elif urgency == "medium":
                next_retry = (now + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
            else:  # low
                next_retry = (now + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            log_manual_call(f"Using urgency-based scheduling: {urgency} -> {next_retry}")
        
        # For the company_name_for_agent field, use the provided company name or default
        # The JavaScript handles replacing [COMPANY] in the call_purpose text,
        # but we also need to store it separately for the agent to use when introducing itself
        company_name_for_agent = company_name if company_name and company_name.strip() else "DTC Executive Office"
        log_manual_call(f"Using company name for agent: {company_name_for_agent}")
        
        # Build objective description with notes if provided
        objective = call_purpose
        if notes and notes.strip():
            objective += f"\n\nAdditional information: {notes}"
        
        # Insert the new call request
        cursor.execute('''
            INSERT INTO scheduled_calls
            (contact_name, phone_number, initial_call_objective_description,
            current_call_objective_description, overall_status, next_retry_at,
            retries_attempted, max_retries, company_name_for_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (contact_name, phone_number, objective, objective, status, next_retry, 0, 3, company_name_for_agent))
        
        conn.commit()
        call_id = cursor.lastrowid
        conn.close()
        
        log_manual_call(f"Created new call request for {contact_name} with ID {call_id}")
        return {"success": True, "call_id": call_id}
    except Exception as e:
        log_manual_call(f"Error creating call request: {str(e)}")
        return {"success": False, "error": str(e)}

# --- Route Handlers ---
@router.get("/addcall", response_class=HTMLResponse)
async def get_add_call_form(request: Request):
    """
    Serve the manual call request form.
    """
    log_manual_call("Serving manual call request form")
    return templates.TemplateResponse("addcall.html", {"request": request})

@router.post("/api/manual_call")
async def create_call_request(
    contact_name: str = Form(...),
    phone_number: str = Form(...),
    company_name: Optional[str] = Form(None),
    call_purpose: str = Form(...),
    urgency: str = Form(...),
    scheduled_time: Optional[str] = Form(None),
    timezone_offset: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """
    Process the submitted form data and create a new call request.
    This will schedule an outbound call to the customer from the specified company.
    If a scheduled_time is provided, the call will be scheduled at that time (adjusted for timezone),
    otherwise it will be scheduled based on the urgency level.
    """
    # Validate required fields
    if not contact_name or not phone_number or not call_purpose or not urgency:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Validate phone number format (basic check)
    if not (phone_number.isdigit() and len(phone_number) >= 7):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    # Create the call request in the database
    # Convert timezone_offset to int if it's provided
    tz_offset_int = None
    if timezone_offset:
        try:
            tz_offset_int = int(timezone_offset)
            log_manual_call(f"Using timezone offset: {tz_offset_int} minutes from UTC")
        except (ValueError, TypeError):
            log_manual_call(f"Invalid timezone offset value: {timezone_offset}, ignoring")
    
    result = create_manual_call_request(
        contact_name=contact_name,
        phone_number=phone_number,
        company_name=company_name,
        call_purpose=call_purpose,
        urgency=urgency,
        scheduled_time=scheduled_time,
        timezone_offset=tz_offset_int,
        notes=notes
    )
    
    if result["success"]:
        log_manual_call(f"Successfully created call request #{result['call_id']} for {contact_name}")
        return {"status": "success", "message": f"Call request created successfully (ID: {result['call_id']})"}
    else:
        log_manual_call(f"Failed to create call request for {contact_name}: {result.get('error', 'Unknown error')}")
        raise HTTPException(status_code=500, detail=f"Failed to create call request: {result.get('error', 'Unknown error')}")

@router.get("/calls", response_class=HTMLResponse)
async def get_calls_list(request: Request):
    """
    Display a list of all scheduled calls with their status.
    """
    log_manual_call("Serving calls monitoring page")
    return templates.TemplateResponse("calls.html", {"request": request})

@router.get("/api/calls")
async def get_calls_data():
    """
    API endpoint to retrieve all calls data for the monitoring table.
    """
    try:
        conn = sqlite3.connect('scheduled_calls.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query to get all scheduled calls with essential information
        cursor.execute('''
            SELECT
                id, contact_name, phone_number, overall_status,
                retries_attempted, max_retries, next_retry_at,
                created_at, updated_at
            FROM scheduled_calls
            ORDER BY
                CASE
                    WHEN overall_status = 'PENDING' THEN 1
                    WHEN overall_status = 'IN_PROGRESS' THEN 2
                    WHEN overall_status = 'COMPLETED' THEN 3
                    WHEN overall_status = 'FAILED' THEN 4
                    ELSE 5
                END,
                next_retry_at ASC
        ''')
        
        calls = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"calls": calls}
    except Exception as e:
        log_manual_call(f"Error retrieving calls data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/api/call/{call_id}/attempts")
async def get_call_attempts(call_id: int):
    """
    API endpoint to retrieve all attempts for a specific call.
    """
    try:
        conn = sqlite3.connect('scheduled_calls.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # First get the call details
        cursor.execute('''
            SELECT
                id, contact_name, phone_number, initial_call_objective_description,
                current_call_objective_description, overall_status,
                retries_attempted, max_retries, final_summary_for_main_agent,
                next_retry_at, created_at, updated_at
            FROM scheduled_calls
            WHERE id = ?
        ''', (call_id,))
        
        call = dict(cursor.fetchone() or {})
        
        if not call:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Call with ID {call_id} not found")
        
        # Then get all attempts for this call
        cursor.execute('''
            SELECT
                attempt_id, job_id, attempt_number, objective_for_this_attempt,
                ultravox_call_id, attempt_started_at, attempt_ended_at,
                end_reason, transcript, strategist_summary_of_attempt,
                strategist_objective_met_status_for_attempt, strategist_reasoning_for_attempt,
                attempt_status, attempt_error_details, created_at
            FROM call_attempts
            WHERE job_id = ?
            ORDER BY attempt_number ASC
        ''', (call_id,))
        
        attempts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"call": call, "attempts": attempts}
    except sqlite3.Error as e:
        log_manual_call(f"Database error retrieving call attempts for call {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        log_manual_call(f"Error retrieving call attempts for call {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))