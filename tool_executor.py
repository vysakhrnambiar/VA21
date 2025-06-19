# tool_executor.py
import json
import sys
import os
import requests # For synchronous HTTP requests
from datetime import datetime, date, timedelta, time, timezone # Added timezone

from dateutil import parser as dateutil_parser # For flexible date string parsing
from dateutil.relativedelta import relativedelta # For "two days back" etc.
from typing import List, Dict, Optional # Ensure Optional is imported from typing
import sqlite3 # For database operations
try:
    import anthropic_llm_services as anthropic_svc
    ANTHROPIC_SERVICES_AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
    if ANTHROPIC_SERVICES_AVAILABLE:
        print("Successfully imported anthropic_llm_services.")
except ImportError:
    print("anthropic_llm_services.py not found. Anthropic-based generation will not function.")
    ANTHROPIC_SERVICES_AVAILABLE = False


from conversation_history_db import get_filtered_turns # Import new DB function
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro" # Or some placeholder
CONTEXT_SUMMARIZER_MODEL_FOR_TOOL = os.getenv("CONTEXT_SUMMARIZER_MODEL", "gpt-4o-mini")
# Tool name from tools_definition
#from tools_definition import GET_CONVERSATION_HISTORY_SUMMARY_TOOL_NAME
from dateutil import parser as dateutil_parser
# Import tool names from tools_definition
from tools_definition import (
    SEND_EMAIL_SUMMARY_TOOL_NAME,
    RAISE_TICKET_TOOL_NAME,
    GET_BOLT_KB_TOOL_NAME,
    GET_DTC_KB_TOOL_NAME,
    DISPLAY_ON_INTERFACE_TOOL_NAME,
    GET_TAXI_IDEAS_FOR_TODAY_TOOL_NAME,
    GENERAL_GOOGLE_SEARCH_TOOL_NAME,
    # New tool names for Phase 1
    SCHEDULE_OUTBOUND_CALL_TOOL_NAME,
    CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME,
    GENERATE_HTML_VISUALIZATION_TOOL_NAME,
    GET_CONVERSATION_HISTORY_SUMMARY_TOOL_NAME
)

# Import the new KB extraction function from kb_llm_extractor.py
from kb_llm_extractor import extract_relevant_sections
import openai # <<< ADD THIS AT THE TOP
from dotenv import load_dotenv # <<< ADD THIS AT THE TOP
load_dotenv() # Ensure .env is loaded when this module is imported

# ... (existing _tool_log, _load_kb_content, database functions, other handlers) ...

CONTEXT_SUMMARIZER_MODEL_FOR_TOOL = os.getenv("CONTEXT_SUMMARIZER_MODEL", "gpt-4o-mini")
OPENAI_API_KEY_FOR_TOOL_SUMMARIZER = os.getenv("OPENAI_API_KEY") # Get key directly

# Import the new Google services module
try:
    from google_llm_services import get_gemini_response, GOOGLE_API_KEY
    GOOGLE_SERVICES_AVAILABLE = bool(GOOGLE_API_KEY)
except ImportError:
    print("[TOOL_EXECUTOR] WARNING: google_llm_services.py not found or GOOGLE_API_KEY missing. Google-based tools will not function.")
    GOOGLE_SERVICES_AVAILABLE = False
    def get_gemini_response(user_prompt_text: str, system_instruction_text: str, use_google_search_tool: bool = False, model_name: str = "") -> str:
        return "Error: Google AI services are not available (module load failure)."

# --- Knowledge Base File Paths & DB Path ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_FOLDER_PATH = os.path.join(BASE_DIR, "knowledge_bases")
BOLT_KB_FILE = os.path.join(KB_FOLDER_PATH, "bolt_kb.txt")
DTC_KB_FILE = os.path.join(KB_FOLDER_PATH, "dtc_kb.txt")

DATABASE_NAME = "scheduled_calls.db"
DB_PATH = os.path.join(BASE_DIR, DATABASE_NAME)
DEFAULT_MAX_RETRIES = 3 # Default for new scheduled calls

# Helper for logging within this module
def _tool_log(message):
    print(f"[TOOL_EXECUTOR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}")

# --- Database Utility ---
def get_tool_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON;")
        _tool_log(f"Successfully connected to database: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        _tool_log(f"CRITICAL_ERROR: Failed to connect to database {DB_PATH}: {e}")
        return None

def _load_kb_content(file_path: str) -> str:
    try:
        if not os.path.exists(KB_FOLDER_PATH):
            _tool_log(f"ERROR: Knowledge base directory not found: {KB_FOLDER_PATH}")
            return f"Error: KB_DIRECTORY_MISSING"
        if not os.path.exists(file_path):
            _tool_log(f"ERROR: Knowledge base file not found: {file_path}")
            return f"Error: KB_FILE_NOT_FOUND ({os.path.basename(file_path)})"
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        _tool_log(f"ERROR: Could not read KB file {file_path}: {e}")
        return f"Error: KB_READ_ERROR ({os.path.basename(file_path)})"

# --- Email Sending Logic (execute_send_email) ---
def execute_send_email(subject: str, body_text: str, html_body_content: str, config: dict, is_ticket_format: bool = False) -> tuple[bool, str]:
    _tool_log(f"Attempting to send email. Subject: '{subject}'")
    api_key = config.get("RESEND_API_KEY")
    from_email = config.get("DEFAULT_FROM_EMAIL")
    to_emails_str = config.get("RESEND_RECIPIENT_EMAILS")
    bcc_emails_str = config.get("RESEND_RECIPIENT_EMAILS_BCC")
    api_url = config.get("RESEND_API_URL")

    if not all([api_key, from_email, to_emails_str, api_url]) or api_key == "YOUR_ACTUAL_RESEND_API_TOKEN_HERE":
        error_msg = "Email service configuration is incomplete (missing API key, from/to email, or API URL)."
        _tool_log(f"ERROR: {error_msg}")
        return False, f"Error: Email service is not properly configured by the administrator. ({error_msg})"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    ai_disclaimer = "<p style='margin-top: 20px; padding-top: 10px; border-top: 1px solid #ccc; color: #666; font-size: 0.9em;'>This message was generated with the assistance of an AI voice assistant. Please verify any important information.</p>"
    final_html_body = f"<div>{html_body_content}</div>{ai_disclaimer}"
    to_list = [email.strip() for email in to_emails_str.split(',') if email.strip()]
    bcc_list = [email.strip() for email in bcc_emails_str.split(',') if email.strip()] if bcc_emails_str else []

    if not to_list:
        _tool_log(f"ERROR: No valid 'to' recipients after stripping. Original: {to_emails_str}")
        return False, "Error: Email configuration is missing a valid primary recipient."

    payload = {"from": from_email, "to": to_list, "bcc": bcc_list, "subject": subject, "text": body_text, "html": final_html_body}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        if 200 <= response.status_code < 300:
            _tool_log(f"Email sent successfully via Resend.")
            return True, "Email has been sent successfully." if not is_ticket_format else "Ticket has been successfully raised."
        else:
            error_detail = response.text
            try: error_json = response.json(); error_detail = error_json.get("message", error_json.get("error",{}).get("message", str(error_json)))
            except: pass
            error_msg = f"Failed to send email. Status: {response.status_code}. Detail: {error_detail}"
            _tool_log(f"ERROR: {error_msg}")
            return False, f"Error: Email could not be sent (Code: RESEND-{response.status_code}). Detail: {error_detail[:200]}"
    except requests.exceptions.RequestException as e:
        _tool_log(f"ERROR: Email sending failed due to network/request error: {e}"); return False, "Error: Email could not be sent due to a network issue."
    except Exception as e:
        _tool_log(f"ERROR: An unexpected error occurred during email sending: {e}"); return False, "Error: An unexpected issue occurred while trying to send the email."

# --- Tool Handler Functions ---

def handle_send_email_discussion_summary(subject: str, body_summary: str, config: dict) -> str:
    _tool_log(f"Handling send_email_discussion_summary. Subject: {subject}")
    formatted_body = body_summary.replace('\\n', '<br>').replace('\n', '<br>')
    html_content = f"<h2>Discussion Summary</h2><p>{formatted_body}</p>"
    success, message = execute_send_email(subject, body_summary, html_content, config, is_ticket_format=False)
    return message

def handle_raise_ticket_for_missing_knowledge(user_query: str, additional_context: str = "", config: dict = None) -> str:
    if config is None: return "Error: Tool configuration missing for raising ticket."
    _tool_log(f"Handling raise_ticket_for_missing_knowledge. Query: {user_query}")
    subject = f"AI Ticket: Missing Knowledge - \"{user_query[:50]}...\""
    body_text = f"User Query for Missing Knowledge:\n{user_query}\n\nAdditional Context:\n{additional_context if additional_context else 'N/A'}\nGenerated by AI Assistant."
    formatted_user_query = user_query.replace('\\n', '<br>').replace('\n', '<br>')
    formatted_additional_context = (additional_context or 'N/A').replace('\\n', '<br>').replace('\n', '<br>')
    html_content = f"<h2>Missing Knowledge Ticket (AI Generated)</h2><p><strong>Query:</strong><br>{formatted_user_query}</p><p><strong>Context:</strong><br>{formatted_additional_context}</p>"
    ticket_recipient_str = config.get("TICKET_EMAIL") or config.get("RESEND_RECIPIENT_EMAILS")
    if not ticket_recipient_str: return "Error: Ticket email recipient not configured."
    ticket_config = config.copy(); ticket_config["RESEND_RECIPIENT_EMAILS"] = ticket_recipient_str
    success, message = execute_send_email(subject, body_text, html_content, ticket_config, is_ticket_format=True)
    return message

def handle_get_bolt_knowledge_base_info(query_topic: str, config: dict) -> str:
    _tool_log(f"Handling get_bolt_knowledge_base_info. Query Topic: '{query_topic}'")
    kb_content_full = _load_kb_content(BOLT_KB_FILE)
    if kb_content_full.startswith("Error:"): return kb_content_full
    return extract_relevant_sections(kb_full_text=kb_content_full, query_topic=query_topic, kb_name="Bolt")

def handle_get_dtc_knowledge_base_info(query_topic: str, config: dict) -> str:
    _tool_log(f"Handling get_dtc_knowledge_base_info. Query Topic: '{query_topic}'")
    kb_content_full = _load_kb_content(DTC_KB_FILE)
    if kb_content_full.startswith("Error:"): return kb_content_full
    return extract_relevant_sections(kb_full_text=kb_content_full, query_topic=query_topic, kb_name="DTC")

def handle_display_on_interface(display_type: str, data: dict, config: dict, title: str = None) -> str:
    _tool_log(f"Handling display_on_interface. Type: {display_type}, Title: {title}")
    fastapi_url = config.get("FASTAPI_DISPLAY_API_URL")
    if not fastapi_url: return "Error: Display interface URL is not configured."
    # Basic validation (can be expanded)
    if display_type == "markdown" and ("content" not in data or not isinstance(data.get("content"), str)):
        return "Error: Invalid data for markdown: 'content' string missing/invalid."
    elif display_type in ["graph_bar", "graph_line", "graph_pie"] and (not isinstance(data.get("labels"), list) or not isinstance(data.get("datasets"), list) or not data.get("datasets")):
        return "Error: Invalid data for graph: 'labels' or 'datasets' missing/invalid or 'datasets' is empty."

    payload_to_send = {"type": display_type, "payload": {**(data if isinstance(data, dict) else {})}}
    if title: payload_to_send["payload"]["title"] = title
    try:
        response = requests.post(fastapi_url, json=payload_to_send, timeout=7)
        response.raise_for_status(); response_data = response.json()
        status = response_data.get("status", "unknown"); message = response_data.get("message", "No message.")
        if status == "success": return f"Content sent to display. Server: {message}"
        if status == "received_but_no_clients": return f"Attempted display, but no visual interface connected. Server: {message}"
        return f"Display interface issue: {message} (Status: {status})"
    except requests.exceptions.RequestException as e:
        _tool_log(f"Error sending to display: {e}"); return f"Error connecting to display: {str(e)[:100]}"
    except Exception as e:
        _tool_log(f"Unexpected error in display handler: {e}"); return "Unexpected error displaying content."

def handle_get_taxi_ideas_for_today(current_date: str, config: dict, specific_focus: str = None) -> str:
    _tool_log(f"Handling get_taxi_ideas_for_today. Date: {current_date}, Focus: {specific_focus}")
    
    # Original Gemini implementation (commented out)
    # if not GOOGLE_SERVICES_AVAILABLE: return "Error: Google AI services are not available for taxi ideas."
    # system_instruction_for_taxi_ideas = f"You are an AI assistant for Dubai Taxi Corporation (DTC). Find actionable ideas, news, and events for taxi services in Dubai for {current_date}. Consider Khaleej Times or local news. If no specific business-impacting ideas are found for {current_date}, respond with: 'No new business ideas found for today, {current_date}, based on current information.' Only provide info for {current_date}."
    # user_prompt_for_gemini = f"Analyze information for Dubai for today, {current_date}, and provide actionable taxi service ideas or relevant event information."
    # if specific_focus: user_prompt_for_gemini += f" Pay special attention to: {specific_focus}."
    # return get_gemini_response(user_prompt_text=user_prompt_for_gemini, system_instruction_text=system_instruction_for_taxi_ideas, use_google_search_tool=True)
    
    # New OpenAI implementation
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY_FOR_TOOL_SUMMARIZER:
        _tool_log("ERROR: OPENAI_API_KEY not found in environment for taxi ideas.")
        return "Error: OpenAI services are not available for taxi ideas (missing API key)."
    
    system_instruction = f"You are an AI assistant for Dubai Taxi Corporation (DTC). Find actionable ideas, news, and events for taxi services in Dubai for {current_date}. Consider Khaleej Times or local news. If no specific business-impacting ideas are found for {current_date}, respond with: 'No new business ideas found for today, {current_date}, based on current information.' Only provide info for {current_date}."
    
    user_prompt = f"Analyze information for Dubai for today, {current_date}, and provide actionable taxi service ideas or relevant event information."
    if specific_focus:
        user_prompt += f" Pay special attention to: {specific_focus}."
    
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY_FOR_TOOL_SUMMARIZER)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "text"
            },
            web_search_options={
                "search_context_size": "high",
                "user_location": {
                    "type": "approximate",
                    "approximate": {
                        "country": "AE"
                    }
                }
            }
        )
        
        _tool_log(f"Successfully received response from OpenAI for taxi ideas")
        return response.choices[0].message.content
    except Exception as e:
        _tool_log(f"ERROR in get_taxi_ideas_for_today with OpenAI: {e}")
        return f"Error: Could not get taxi ideas. Detail: {str(e)}"

def handle_general_google_search(search_query: str, config: dict) -> str:
    _tool_log(f"Handling general_google_search. Query: '{search_query}'")
    
    # Original Gemini implementation (commented out)
    # if not GOOGLE_SERVICES_AVAILABLE: return "Error: Google AI services are not available for general search."
    # system_instruction_for_general_search = "You are an AI assistant for a Dubai Taxi Corporation (DTC) employee. Answer the user's query based ONLY on Google Search results. Be factual and concise. Context is Dubai-related, professional. If no clear answer, state that. Prioritize reputable sources. Give direct answer."
    # return get_gemini_response(user_prompt_text=search_query, system_instruction_text=system_instruction_for_general_search, use_google_search_tool=True)
    
    # New OpenAI implementation
    # Check if OpenAI API key is available
    if not OPENAI_API_KEY_FOR_TOOL_SUMMARIZER:
        _tool_log("ERROR: OPENAI_API_KEY not found in environment for general search.")
        return "Error: OpenAI services are not available for general search (missing API key)."
    
    system_instruction = "You are an AI assistant for a Dubai Taxi Corporation (DTC) employee. Answer the user's query based ONLY on search results. Be factual and concise. Context is Dubai-related, professional. If no clear answer, state that. Prioritize reputable sources. Give direct answer."
    
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY_FOR_TOOL_SUMMARIZER)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": search_query}
            ],
            response_format={
                "type": "text"
            },
            web_search_options={
                "search_context_size": "high",
                "user_location": {
                    "type": "approximate",
                    "approximate": {
                        "country": "AE"
                    }
                }
            }
        )
        
        _tool_log(f"Successfully received response from OpenAI for general search")
        return response.choices[0].message.content
    except Exception as e:
        _tool_log(f"ERROR in general_google_search with OpenAI: {e}")
        return f"Error: Could not get search results. Detail: {str(e)}"

# --- New Tool Handlers for Phase 1 ---

def handle_schedule_outbound_call(phone_number: str, contact_name: str, call_objective: str, config: dict) -> str:
    _tool_log(f"Handling schedule_outbound_call. To: {contact_name} ({phone_number}). Objective: {call_objective[:70]}...")
    conn = get_tool_db_connection()
    if not conn:
        return "Error: Could not connect to the scheduling database. Please try again later."

    try:
        cursor = conn.cursor()
        insert_sql = """
            INSERT INTO scheduled_calls
            (phone_number, contact_name, initial_call_objective_description, current_call_objective_description, overall_status, max_retries, created_at, updated_at, company_name_for_agent)
            VALUES (?, ?, ?, ?, 'PENDING', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
        """
        # Using initial and current objective same at creation
        params = (phone_number, contact_name, call_objective, call_objective, DEFAULT_MAX_RETRIES, "DTC")
        cursor.execute(insert_sql, params)
        conn.commit()
        job_id = cursor.lastrowid
        _tool_log(f"Successfully scheduled call. Job ID: {job_id}, To: {contact_name}, Objective: {call_objective[:50]}...")
        objective_snippet = call_objective[:30] + "..." if len(call_objective) > 30 else call_objective
        return f"Okay, I've scheduled the call to {contact_name} regarding '{objective_snippet}'. The Job ID is {job_id}. I will provide updates as they become available or when the task is complete."
    except sqlite3.Error as e:
        _tool_log(f"ERROR: Database error while scheduling call: {e}")
        return f"Error: A database error occurred while trying to schedule the call: {e}"
    except Exception as e:
        _tool_log(f"ERROR: Unexpected error in handle_schedule_outbound_call: {e}")
        return "Error: An unexpected error occurred while scheduling the call."
    finally:
        if conn:
            conn.close()

def handle_check_scheduled_call_status(
    config: dict, 
    contact_name: str = None, 
    call_objective_snippet: str = None,
    date_reference: str = None,
    time_of_day_preference: str = "any", # Default to "any"
    job_id: int = None
    ) -> str:
    _tool_log(f"Handling check_scheduled_call_status. Job ID: {job_id}, Contact: {contact_name}, Objective: {call_objective_snippet}, DateRef: {date_reference}, TimePref: {time_of_day_preference}")
    conn = get_tool_db_connection()
    if not conn:
        return "Error: Could not connect to the scheduling database to check status."

    query_parts = []
    params = []
    order_by_clauses = ["updated_at DESC"] # Default sort

    if job_id is not None:
        query_parts.append("id = ?")
        params.append(job_id)
    if contact_name:
        query_parts.append("contact_name LIKE ?")
        params.append(f"%{contact_name}%")
    if call_objective_snippet:
        query_parts.append("(initial_call_objective_description LIKE ? OR current_call_objective_description LIKE ?)")
        params.append(f"%{call_objective_snippet}%")
        params.append(f"%{call_objective_snippet}%")

    # Date/Time Reference Parsing Logic
    # This will be a bit complex and might need refinement based on typical user inputs.
    # We'll target the 'created_at' or 'updated_at' columns. Let's use 'updated_at' as it reflects last action.
    if date_reference:
        try:
            target_date = None
            date_start_dt = None
            date_end_dt = None
            
            today = date.today()
            now = datetime.now()

            if date_reference.lower() == "today":
                target_date = today
            elif date_reference.lower() == "yesterday":
                target_date = today - timedelta(days=1)
            elif "days back" in date_reference.lower() or "days ago" in date_reference.lower():
                try:
                    num_days = int(date_reference.lower().split()[0])
                    target_date = today - timedelta(days=num_days)
                except ValueError:
                    _tool_log(f"Could not parse number of days from '{date_reference}'")
            elif date_reference.lower() in ["last call", "most recent"]:
                # This is handled by default sorting, but we can acknowledge it.
                # No specific date filter, but ensure `order_by_clauses.insert(0, "updated_at DESC")` is effectively done.
                pass 
            else: # Try parsing as a specific date
                parsed_dt_obj = dateutil_parser.parse(date_reference, default=datetime(now.year, now.month, now.day))
                target_date = parsed_dt_obj.date()

            if target_date:
                # Define time ranges based on time_of_day_preference
                if time_of_day_preference == "morning": # e.g., 6 AM to 12 PM
                    date_start_dt = datetime.combine(target_date, time(6, 0, 0))
                    date_end_dt = datetime.combine(target_date, time(11, 59, 59))
                elif time_of_day_preference == "afternoon": # e.g., 12 PM to 6 PM
                    date_start_dt = datetime.combine(target_date, time(12, 0, 0))
                    date_end_dt = datetime.combine(target_date, time(17, 59, 59))
                elif time_of_day_preference == "evening": # e.g., 6 PM to 11:59 PM
                    date_start_dt = datetime.combine(target_date, time(18, 0, 0))
                    date_end_dt = datetime.combine(target_date, time(23, 59, 59))
                else: # "any" time of day or default
                    date_start_dt = datetime.combine(target_date, time.min)
                    date_end_dt = datetime.combine(target_date, time.max)
                
                query_parts.append("updated_at BETWEEN ? AND ?") # Or created_at, depending on desired meaning
                params.append(date_start_dt.strftime('%Y-%m-%d %H:%M:%S'))
                params.append(date_end_dt.strftime('%Y-%m-%d %H:%M:%S'))
                _tool_log(f"Date filter: updated_at between {date_start_dt} and {date_end_dt}")
        
        except Exception as e_date:
            _tool_log(f"Could not parse date_reference '{date_reference}': {e_date}. Ignoring date filter.")
            # Optionally, inform LLM that date parsing failed. For now, just ignore.

    if not query_parts:
        # If still no filters, default to most recent N calls (e.g., last 3 updated)
        _tool_log("No specific query parameters provided, fetching most recent calls.")
        # order_by_clauses is already updated_at DESC
    
    # Construct the final query
    base_query = "SELECT id, contact_name, overall_status, initial_call_objective_description, current_call_objective_description, final_summary_for_main_agent, retries_attempted, max_retries, strftime('%Y-%m-%d %H:%M', next_retry_at) as next_retry_at_formatted, strftime('%Y-%m-%d %H:%M', updated_at) as last_updated_formatted FROM scheduled_calls"
    
    where_clause = ""
    if query_parts:
        where_clause = f"WHERE {' AND '.join(query_parts)}"
        
    order_by_sql = "ORDER BY " + ", ".join(list(set(order_by_clauses))) # Use set to avoid duplicate sort keys if "last call" added it
    
    # Limit results
    limit_sql = "LIMIT 5" 
    if date_reference and date_reference.lower() in ["last call", "most recent"] and not query_parts: # Only date_ref is "last call"
        limit_sql = "LIMIT 1"

    full_query = f"{base_query} {where_clause} {order_by_sql} {limit_sql}"

    try:
        cursor = conn.cursor()
        _tool_log(f"Executing status check query: {full_query} with params: {params}")
        cursor.execute(full_query, tuple(params))
        jobs = cursor.fetchall()

        if not jobs:
            return "I couldn't find any scheduled calls matching your criteria."

        results = []
        for job_row in jobs:
            job = dict(job_row) # Convert Row to dict
            status_msg = f"Call to {job.get('contact_name', 'N/A')} (ID: {job['id']}) regarding '{job.get('current_call_objective_description', job.get('initial_call_objective_description', 'N/A'))[:50]}...' (Last updated: {job.get('last_updated_formatted', 'N/A')}): "
            
            status = job.get('overall_status', 'UNKNOWN')
            if status == 'PENDING':
                status_msg += "This call is scheduled and awaiting processing."
            # ... (other status formatting from previous version) ...
            elif status == 'RETRY_SCHEDULED':
                status_msg += f"A retry for this call is scheduled for around {job.get('next_retry_at_formatted', 'soon')}."
                # Fetching reason from call_attempts can be added here if complex joins are acceptable or via a sub-query for each job.
            elif status in ['COMPLETED_SUCCESS', 'FAILED_MAX_RETRIES', 'COMPLETED_OBJECTIVE_NOT_MET', 'FAILED_PERMANENT_ERROR']:
                final_summary = job.get('final_summary_for_main_agent', 'No final summary recorded.')
                status_msg += f"This call has concluded. Status: {status}. Outcome: {final_summary}"
            else:
                status_msg += f"The call has an unknown status: {status}."
            results.append(status_msg)
        
        if len(results) == 1:
            return results[0]
        else:
            response = f"Found {len(results)} calls matching your criteria:\n" + "\n".join([f"- {res}" for res in results])
            return response

    except sqlite3.Error as e:
        _tool_log(f"ERROR: Database error while checking call status: {e}")
        return f"Error: A database error occurred: {e}"
    except Exception as e:
        _tool_log(f"ERROR: Unexpected error in handle_check_scheduled_call_status: {e}")
        return "Error: An unexpected error occurred."
    finally:
        if conn:
            conn.close()

def _format_history_for_summarizer(turns: List[Dict]) -> str:
    """Formats a list of turn dicts into a string for the summarizer LLM."""
    if not turns:
        return "No conversation history found for the given criteria."
    
    formatted_history = []
    now_utc_aware = datetime.now(timezone.utc) # Ensure timezone is imported in openai_client

    for turn in turns:
        try:
            ts_str = turn['timestamp']
            turn_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            if turn_time.tzinfo is None:
                turn_time = turn_time.replace(tzinfo=timezone.utc)

            time_diff_seconds = (now_utc_aware - turn_time).total_seconds()
            time_diff_seconds = max(0, time_diff_seconds)

            if time_diff_seconds < 60: time_ago = f"{int(time_diff_seconds)}s ago"
            elif time_diff_seconds < 3600: time_ago = f"{int(time_diff_seconds/60)}m ago"
            # For older history, absolute timestamps might be better if a date was specified
            # This is a simplification for now.
            else: time_ago = turn_time.strftime('%Y-%m-%d %H:%M UTC')


            role_display = turn['role'].capitalize()
            content_display = turn['content']
            if turn['role'] in ['tool_call', 'tool_result']:
                try: 
                    content_json = json.loads(turn['content'])
                    content_display = f"Tool: {content_json.get('name', 'N/A')}, Data: {str(content_json)[:70]}..."
                except: pass # Keep raw content if not valid JSON
            formatted_history.append(f"({time_ago}) {role_display}: {content_display}")
        except Exception as e_ts_format:
            _tool_log(f"WARN: Could not format timestamp for history tool: {turn.get('timestamp')}. Error: {e_ts_format}")
            formatted_history.append(f"(Time Unknown) {turn.get('role', 'UNK').capitalize()}: {turn.get('content', '')[:70]}...")
    
    return "\n".join(formatted_history)


def handle_get_conversation_history_summary(
    user_question_about_history: str,
    # config: dict, # We might not need config for this specific handler anymore if API key is direct
    date_reference: Optional[str] = None,
    time_of_day_reference: Optional[str] = None,
    keywords: Optional[str] = None,
    max_turns_to_scan: int = 100,
    config: Optional[dict] = None 
    ) -> str:
    _tool_log(f"Handling get_conversation_history_summary. Question: '{user_question_about_history}', Date: {date_reference}, Time: {time_of_day_reference}, Keywords: {keywords}")

    # --- Date/Time parsing logic remains the same ---
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    if date_reference:
        try:
            # (Your existing robust date/time parsing logic here)
            # Ensure start_dt and end_dt are timezone-aware (UTC) if your DB stores UTC
            # Example sketch:
            today = date.today()
            now = datetime.now()
            target_date_obj: Optional[date] = None
            if date_reference.lower() == "today": target_date_obj = today
            elif date_reference.lower() == "yesterday": target_date_obj = today - timedelta(days=1)
            else:
                parsed_dt_for_date = dateutil_parser.parse(date_reference, default=datetime(now.year, now.month, now.day))
                target_date_obj = parsed_dt_for_date.date()

            if target_date_obj:
                time_start = time.min
                time_end = time.max
                # Add logic for time_of_day_reference to refine time_start, time_end
                # ...
                start_dt = datetime.combine(target_date_obj, time_start)
                end_dt = datetime.combine(target_date_obj, time_end)
                # If your system deals with local times but DB is UTC, convert here:
                # start_dt = start_dt.astimezone(timezone.utc)
                # end_dt = end_dt.astimezone(timezone.utc)
                _tool_log(f"Date/Time filter: From {start_dt} to {end_dt}")
        except Exception as e_date:
            _tool_log(f"Could not parse date_reference or time: {e_date}. Ignoring date/time filter.")
            start_dt, end_dt = None, None
    # --- End of Date/Time parsing ---

    fetched_turns = get_filtered_turns(
        start_datetime=start_dt,
        end_datetime=end_dt,
        keywords=keywords,
        limit=max_turns_to_scan
    )

    if not fetched_turns:
        return f"I couldn't find any conversation history matching your criteria (Date: {date_reference}, Time: {time_of_day_reference}, Keywords: {keywords})."

    history_string_for_llm = _format_history_for_summarizer(fetched_turns)

    if not OPENAI_API_KEY_FOR_TOOL_SUMMARIZER:
        _tool_log("CRITICAL_ERROR: OPENAI_API_KEY not found in environment for history summarizer tool.")
        return "Error: History summarization service is not configured (missing API key)."

    try:
        sync_llm_client = openai.OpenAI(api_key=OPENAI_API_KEY_FOR_TOOL_SUMMARIZER)
        _tool_log(f"Initialized OpenAI client for history summarizer tool (model: {CONTEXT_SUMMARIZER_MODEL_FOR_TOOL}).")
    except Exception as e_client_init:
        _tool_log(f"ERROR: Failed to initialize OpenAI client for history tool: {e_client_init}")
        return "Error: Internal service for summarizing history is currently unavailable (client init failed)."

    summarizer_prompt_for_tool = f"""The user is asking about past conversations. Their specific question is:
    "{user_question_about_history}"

    Current UTC time is {datetime.now(timezone.utc).isoformat()}.
    Based ONLY on the following conversation history excerpt, provide a concise answer or summary that directly addresses the user's question.
    Quote relevant parts if helpful. If the history does not contain information to answer the question, explicitly state that.

    Conversation History Excerpt:
    ---
    {history_string_for_llm}
    ---

    Answer to the user's question ("{user_question_about_history}") based on the excerpt:
    """
    try:
        _tool_log(f"Sending to summarizer LLM ({CONTEXT_SUMMARIZER_MODEL_FOR_TOOL}) for history tool. Prompt length: {len(summarizer_prompt_for_tool)}")
        response = sync_llm_client.chat.completions.create(
            model=CONTEXT_SUMMARIZER_MODEL_FOR_TOOL,
            messages=[{"role": "user", "content": summarizer_prompt_for_tool}],
            temperature=0.0,
            max_tokens=300
        )
        summary_answer = response.choices[0].message.content.strip()
        _tool_log(f"History summarizer LLM response for tool: {summary_answer}")
        if not summary_answer:
            return f"I reviewed the history for '{user_question_about_history}' but found no specific details."
        return summary_answer
    except Exception as e:
        _tool_log(f"ERROR summarizing filtered history with LLM: {e}")
        return "Error: An issue occurred while trying to summarize the conversation history."

# tool_executor.py

# Find this function definition:
# def handle_generate_html_visualization(user_request: str, knowledge_base_source: str, title: Optional[str] = None, config: Optional[dict] = None) -> str:
# And replace its content with:

def handle_generate_html_visualization(user_request: str, knowledge_base_source: str, title: Optional[str] = None, config: Optional[dict] = None) -> str:
    _tool_log(f"Handling generate_html_visualization. Request: '{user_request[:70]}...', Source: {knowledge_base_source}, Title: {title}")


    if not config:
        _tool_log("ERROR: Config dictionary not provided to handle_generate_html_visualization.")
        # Return simple HTML error for frontend to render
        return "<!DOCTYPE html><html><head><title>Config Error</title></head><body><p>Error: Internal tool configuration missing. Cannot generate visualization.</p></body></html>"
    preferred_html_generator = config.get("PREFERRED_HTML_GENERATOR", "gemini").lower()
    anthropic_model_id = config.get("ANTHROPIC_MODEL_ID", "claude-3-opus-20240229")

  
    fastapi_url = config.get("FASTAPI_DISPLAY_API_URL")
    if not fastapi_url:
        _tool_log("ERROR: FASTAPI_DISPLAY_API_URL not found in config for HTML visualization.")
        return "<!DOCTYPE html><html><head><title>Config Error</title></head><body><p>Error: Display service URL is not configured. Cannot show visualization.</p></body></html>"

    if not GOOGLE_SERVICES_AVAILABLE:
        _tool_log("Error: Google Services not available for HTML generation.")
        # This HTML will be sent to the display service
        error_html = "<!DOCTYPE html><html><head><title>Service Unavailable</title><style>body{font-family:sans-serif;padding:20px;text-align:center;}p{font-size:1.2em;}</style></head><body><p>Error: The HTML visualization service (Google AI) is currently unavailable. Please check system configuration.</p></body></html>"
        # Attempt to display this error HTML
        error_payload_to_frontend = {"type": "html", "payload": {"content": error_html, "title": "Service Error"}}
        try:
            requests.post(fastapi_url, json=error_payload_to_frontend, timeout=5)
        except Exception as e_disp_err:
            _tool_log(f"Additionally, failed to send service unavailable HTML to display: {e_disp_err}")
        return "Sorry, the HTML visualization service is currently unavailable." # Message for LLM to speak


    knowledge_base_content = ""
    kb_source_for_prompt = "No specific knowledge base was used for this visualization."
    error_loading_kb = False

    if knowledge_base_source == "dtc":
        kb_content_full = _load_kb_content(DTC_KB_FILE)
        if kb_content_full.startswith("Error:"):
            _tool_log(f"Error loading DTC KB: {kb_content_full}")
            error_loading_kb = True
        else:
            knowledge_base_content = f"--- START OF DTC KNOWLEDGE BASE ---\n{kb_content_full}\n--- END OF DTC KNOWLEDGE BASE ---"
            kb_source_for_prompt = "Data from the DTC Knowledge Base."
    elif knowledge_base_source == "bolt":
        kb_content_full = _load_kb_content(BOLT_KB_FILE)
        if kb_content_full.startswith("Error:"):
            _tool_log(f"Error loading Bolt KB: {kb_content_full}")
            error_loading_kb = True
        else:
            knowledge_base_content = f"--- START OF BOLT KNOWLEDGE BASE ---\n{kb_content_full}\n--- END OF BOLT KNOWLEDGE BASE ---"
            kb_source_for_prompt = "Data from the Bolt Knowledge Base."
    elif knowledge_base_source == "both":
        dtc_content = _load_kb_content(DTC_KB_FILE)
        bolt_content = _load_kb_content(BOLT_KB_FILE)
        loaded_kb_parts = []
        if not dtc_content.startswith("Error:"):
            loaded_kb_parts.append(f"--- START OF DTC KNOWLEDGE BASE ---\n{dtc_content}\n--- END OF DTC KNOWLEDGE BASE ---")
        else:
            _tool_log(f"Error loading DTC KB for 'both': {dtc_content}")
            error_loading_kb = True # Mark error even if one loads
        if not bolt_content.startswith("Error:"):
            loaded_kb_parts.append(f"--- START OF BOLT KNOWLEDGE BASE ---\n{bolt_content}\n--- END OF BOLT KNOWLEDGE BASE ---")
        else:
            _tool_log(f"Error loading Bolt KB for 'both': {bolt_content}")
            error_loading_kb = True
         
        if loaded_kb_parts:
            knowledge_base_content = "\n\n".join(loaded_kb_parts)
            kb_source_for_prompt = "Data from both DTC and Bolt Knowledge Bases."
            if error_loading_kb: # If one failed but other succeeded
                kb_source_for_prompt += " (Note: There might have been issues loading parts of the KB data)."
        elif not loaded_kb_parts and error_loading_kb: # Both failed
              _tool_log("Error loading both DTC and Bolt KBs.")
        # If error_loading_kb is true, we'll handle it next.

    if error_loading_kb:
        error_html = f"<!DOCTYPE html><html><head><title>KB Error</title></head><body><p>Error loading the required Knowledge Base ('{knowledge_base_source}'). Cannot generate visualization.</p></body></html>"
        error_payload_to_frontend = {"type": "html", "payload": {"content": error_html, "title": "Knowledge Base Error"}}
        try:
            requests.post(fastapi_url, json=error_payload_to_frontend, timeout=5)
        except Exception as e_disp_err:
            _tool_log(f"Additionally, failed to send KB error HTML to display: {e_disp_err}")
        return f"Sorry, I couldn't access the required information from the '{knowledge_base_source}' knowledge base to create the visualization."


    # --- Gemini System Instruction ---
    gemini_system_instruction = """You are an expert HTML, CSS, and JavaScript developer specializing in creating rich, self-contained, and responsive data dashboards and visualizations.
        Your output MUST be a single, valid HTML5 document, starting with <!DOCTYPE html> and ending with </html>.

        **Core Requirements:**
        1.  **Self-Contained:**
        *   All CSS MUST be inline within `<style>` tags in the `<head>`.
        *   All JavaScript (for Chart.js configuration, any minor interactivity, or on-load animations) MUST be inline within `<script>` tags, preferably placed before the closing `</body>` tag.
        2.  **Chart.js Usage:**
        *   You MUST include Chart.js library using ONLY the following CDN link in the `<head>`: `<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>`.
        *   No other external CSS or JS libraries are permitted. Do not attempt to load Chart.js from any other source or embed its code directly.
        *   If charts are requested or appropriate for the data, use Chart.js. Configure charts extensively using inline JavaScript for data, type (bar, line, doughnut, radar, scatter, bubble etc.), colors, labels, axes, tooltips, and legends.
        *   Aim for visually appealing and informative charts. Consider dual-axis charts if appropriate for comparing different scales of data.
        3.  **No Charts Alternative:** If charts are not suitable or not explicitly requested for the data, use well-styled HTML tables, lists, cards, definition lists, or other semantic HTML elements to present the information clearly and professionally.
        4.  **Output Format:** Your entire response MUST be only the HTML code. Do NOT include any explanatory text, apologies, comments (except valid HTML comments <!-- ... --> if truly necessary for complex JS), or anything outside the valid HTML document itself.
        5.  **Fallback:** If the provided knowledge base data is insufficient or the user's request cannot be fulfilled as a meaningful visual HTML page (after genuinely trying), you MUST return the following simple HTML page ONLY:
        `<!DOCTYPE html><html><head><title>Request Unfulfilled</title><style>body{font-family:sans-serif;padding:20px;text-align:center;}p{font-size:1.2em;}</style></head><body><p>The requested visualization cannot be generated due to insufficient data or an unclear request.</p></body></html>`

        **Design & Styling Guidelines (Emulate a modern, clean, professional dashboard like the conceptual example):**
        1.  **Layout:**
        *   Employ a responsive grid-based layout (CSS Grid or Flexbox) for arranging multiple components like KPI cards and charts. Use `repeat(auto-fit, minmax(280px, 1fr))` or similar for adaptable grids.
        *   Ensure sections are clearly delineated. Use ample padding (e.g., `20px`) within sections and around elements for a clean, uncluttered look.
        2.  **Aesthetics:**
        *   **Font:** Use a clean, readable sans-serif font stack (e.g., `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`).
        *   **Color Palette:**
            *   Main Background: A light, neutral color (e.g., `#f8f9fa` or `#e9eff1`).
            *   Card/Container Backgrounds: White (e.g., `#ffffff`).
            *   Primary Text: Dark gray/off-black (e.g., `#333` or `#495057`).
            *   Secondary/Label Text: Medium gray (e.g., `#6c757d` or `#555`).
            *   Chart & Accent Colors: Use a professional and harmonious palette. Examples include blues (e.g., `#3b82f6`), greens (e.g., `#10b981`), oranges (e.g., `#f59e0b`), reds (e.g., `#ef4444`). Ensure good color contrast for accessibility.
        *   **Cards:** Style cards with rounded corners (e.g., `border-radius: 8px;`), subtle shadows (e.g., `box-shadow: 0 2px 5px rgba(0,0,0,0.1);`), and light borders (e.g., `1px solid #e0e0e0;`). Consider subtle hover effects.
        *   **Typography:** Use clear typographic hierarchy (differentiated font sizes/weights for headings (H1-H4), subheadings, values, labels).
        3.  **Component Styling Examples (Conceptual):**
        *   **KPI Cards:** Typically include a title/label (small, gray), a large prominent value (dark, bold), and often a secondary metric or percentage change (styled with color like green for positive, red for negative). Small, simple icons (Unicode characters or SVG if simple enough to be inline) can be used.
        *   **Charts:** Ensure chart titles are clear and prominent. Legends and tooltips should be styled for readability. Axes should have titles and formatted tick labels where appropriate.
        *   **Tables:** If using tables, style them for readability: `width: 100%; border-collapse: collapse;`. Use `<th>` for headers with a distinct background and bold text. Use `<td>` with adequate padding. Add alternating row colors (`tr:nth-child(even)`) for better scannability.
        4.  **Interactivity & Animations (Subtle):**
        *   Chart.js provides default interactivity (tooltips).
        *   If adding minor custom JavaScript for UI (e.g., simple tab switching, accordions for complex data), ensure it's minimal, efficient, and inline.
        *   Subtle on-load animations for elements (e.g., cards fading in) can be achieved with CSS transitions/animations if desired. Keep them brief and professional.

        IMPORTANT: You MUST ONLY use the data provided between the KNOWLEDGE BASE DATA markers. Do NOT add or generate any additional data points that are not explicitly present in the provided knowledge base. If the any particular field requested does not have the data you will mention that at the bottom of the html page.  
        *   **CRITICAL DISPLAY CONSTRAINT:** Your HTML MUST be optimized for a display area with a maximum width of 960px (centered). The main container area has horizontal margins of 160px on each side and inner padding of 20px. Design your content to look best within these constraints. All interactive elements and visualizations should be fully functional and properly sized within this 960px maximum width.
        """

    # --- Gemini User Prompt ---
    effective_title_for_page = title if title else "Dynamic Data Visualization" # Fallback title

    gemini_user_prompt = f"""
        Please generate a complete, self-contained HTML5 page based on the following user request.

        User's Core Request: "{user_request}"
        The desired title for the HTML page and its main visualization heading should be: "{effective_title_for_page}"

        The visualization should be based on: {kb_source_for_prompt}
        Knowledge Base Data Provided:
        --- KNOWLEDGE BASE DATA START ---
        {knowledge_base_content if knowledge_base_content.strip() else "N/A. The visualization should be based solely on the user's core request if it appears general (e.g., 'create a sample bar chart of monthly sales'), or you should use the fallback HTML if the request implies data is needed but none was provided from the KBs."}
        --- KNOWLEDGE BASE DATA END ---

        Strictly adhere to ALL requirements and guidelines provided in the System Instructions, especially regarding:
        1.  Outputting ONLY a single, valid HTML5 document.
        2.  Ensuring ALL CSS and ALL JavaScript are inline.
        3.  Using the specified Chart.js CDN link if creating charts: `<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>`.
        4.  Making the design responsive, professional, and clean.
        5.  Using the exact fallback HTML if a meaningful visualization cannot be generated.

        Generate the HTML code now.
        Begin HTML:
        """
    #_tool_log(f"Sending request to Gemini model: {DEFAULT_GEMINI_MODEL} for HTML generation. User request: '{user_request[:50]}...'")
    # For debugging, you might want to log parts of the prompt, but they can be very long.
    # _tool_log(f"First 200 chars of System Prompt to Gemini: {gemini_system_instruction[:200]}")
    # _tool_log(f"First 200 chars of User Prompt to Gemini: {gemini_user_prompt[:200]}")

    preferred_html_generator = config.get("PREFERRED_HTML_GENERATOR", "gemini").lower()
    model_used = ""
    generated_html_data = ""

    try:
        if preferred_html_generator == "anthropic" and ANTHROPIC_SERVICES_AVAILABLE:
            anthropic_model_id = config.get("ANTHROPIC_MODEL_ID", "claude-3-opus-20240229")
            model_used = anthropic_model_id

            _tool_log(f"Using Anthropic Claude (model: {anthropic_model_id}) to generate HTML.")
            #llm_generated_html = ""
            generated_html_data = anthropic_svc.get_claude_html_response(
                user_prompt=gemini_user_prompt,# Use the same user prompt designed for Gemini
                system_instruction=gemini_system_instruction, # Same
                model_name=anthropic_model_id
            )

        elif preferred_html_generator == "gemini":  # Explicit check for Gemini
            model_used = "gemini"
            _tool_log("Using Google Gemini to generate HTML.")
            generated_html_data = get_gemini_response(
                user_prompt_text=gemini_user_prompt,
                system_instruction_text=gemini_system_instruction,
                use_google_search_tool=False, # This tool relies on provided KBs or general instruction following
                model_name=DEFAULT_GEMINI_MODEL  # Or some appropriate Google model
            )

        else:
            raise Exception("Invalid PREFERRED_HTML_GENERATOR setting. Please use 'gemini' or 'anthropic'.")

    except Exception as e:
        print(f"HTML Generation Error: {str(e)}", file=sys.stderr)
        generated_html_data = f"Error: Invalid PREFERRED_HTML_GENERATOR setting. Please use 'gemini' or 'anthropic. or Error in models Please check API setting,Here is Error {str(e)}'"
        llm_feedback_message = f"Sorry Model not able to generate the visuals here is the reason {str(e)}"
        
        # We can use code here to send feedback






    #html_response_from_gemini = get_gemini_response(
    #    user_prompt_text=gemini_user_prompt,
    #    system_instruction_text=gemini_system_instruction,
    #    use_google_search_tool=False, # This tool should rely on provided KB or general generation
    #    model_name=DEFAULT_GEMINI_MODEL # Ensure this uses the imported constant
    #)

    # --- Process Gemini Response and Send to Frontend ---
    html_response_from_gemini = generated_html_data
    final_html_to_display = ""
    llm_feedback_message = ""

    if html_response_from_gemini.startswith("Error:"):
        _tool_log(f"Error received directly from get_gemini_response: {html_response_from_gemini}")
        final_html_to_display = f"<!DOCTYPE html><html><head><title>Service Error</title><style>body{{font-family:sans-serif;padding:20px;text-align:center;}}h1{{color:red;}}</style></head><body><h1>Visualization Service Error</h1><p>{html_response_from_gemini.replace('<', '<').replace('>', '>')}</p></body></html>"
        llm_feedback_message = f"Sorry, I encountered an issue with the visualization service: {html_response_from_gemini}"
    elif not (html_response_from_gemini.strip().lower().startswith("<!doctype html>") and html_response_from_gemini.strip().lower().endswith("</html>")):
        _tool_log(f"Warning: Gemini response does not appear to be a valid/complete HTML document. Snippet: {html_response_from_gemini[:250]}...")
        final_html_to_display = f"<!DOCTYPE html><html><head><title>Generation Error</title><style>body{{font-family:sans-serif;padding:20px;}}h1{{color:orange;}}pre{{white-space:pre-wrap;word-wrap:break-word;background:#f0f0f0;padding:10px;border:1px solid #ccc;}}</style></head><body><h1>Visualization Generation Issue</h1><p>The visualization service returned an unexpected format. Please try rephrasing your request or ask for a simpler display.</p><p><b>Service Response Snippet:</b></p><pre>{html_response_from_gemini.replace('<', '<').replace('>', '>')[:1000]}</pre></body></html>"
        llm_feedback_message = "It seems there was an issue formatting the visualization. You might want to try rephrasing your request."
    else:
        # It looks like valid HTML, use it.
        final_html_to_display = html_response_from_gemini
        # Check if it's the specific fallback message from Gemini
        if "<title>Request Unfulfilled</title>" in final_html_to_display and "insufficient data or an unclear request" in final_html_to_display:
            llm_feedback_message = f"I couldn't generate the '{effective_title_for_page}' visualization. It seems there wasn't enough data, or the request was a bit unclear for a visual display."
            _tool_log("Gemini returned its standard 'Request Unfulfilled' fallback HTML.")
        else:
            llm_feedback_message = f"Okay, I've generated and displayed the '{effective_title_for_page}' visualization for you."
            _tool_log(f"Successfully received valid HTML response from Gemini (length: {len(final_html_to_display)} bytes).")

    # Send to frontend
    payload_to_send_to_frontend = {
        "type": "html",
        "payload": {
            "content": final_html_to_display,
            "title": effective_title_for_page 
        }
    }
    try:
        _tool_log(f"Attempting to POST HTML (Type: {'Error/Fallback' if 'Error</title>' in final_html_to_display or 'Unfulfilled</title>' in final_html_to_display else 'Generated'}) to display service: {fastapi_url}")
        response = requests.post(fastapi_url, json=payload_to_send_to_frontend, timeout=10) # Increased timeout for potentially larger HTML
        response.raise_for_status()
        response_data = response.json()
        status = response_data.get("status", "unknown")
        message_from_display_server = response_data.get("message", "No specific message from display server.")

        if status == "success":
            _tool_log(f"Successfully sent HTML to display. Server response: {message_from_display_server}")
            # llm_feedback_message is already set
        elif status == "received_but_no_clients":
            _tool_log(f"HTML sent to display server, but no clients connected. Server: {message_from_display_server}")
            llm_feedback_message = f"I've prepared the '{effective_title_for_page}' visualization, but it seems no display screen is currently active to show it."
        else:
            _tool_log(f"Display service reported an issue for HTML. Status: {status}, Message: {message_from_display_server}")
            llm_feedback_message = f"I prepared the '{effective_title_for_page}' visualization, but there was an issue sending it to the display: {message_from_display_server}"
    except requests.exceptions.RequestException as e:
        _tool_log(f"ERROR: Failed to send generated HTML to display service {fastapi_url}: {e}")
        llm_feedback_message = f"Sorry, I generated the '{effective_title_for_page}' visualization, but couldn't send it to the display due to a connection error."
    except Exception as e_display:
        _tool_log(f"ERROR: Unexpected error while trying to display generated HTML: {e_display}")
        llm_feedback_message = f"Sorry, an unexpected error occurred after generating the '{effective_title_for_page}' visualization, while trying to display it."
    
    return llm_feedback_message






# Dispatch dictionary to map function names to handler functions
TOOL_HANDLERS = {
    SEND_EMAIL_SUMMARY_TOOL_NAME: handle_send_email_discussion_summary,
    RAISE_TICKET_TOOL_NAME: handle_raise_ticket_for_missing_knowledge,
    GET_BOLT_KB_TOOL_NAME: handle_get_bolt_knowledge_base_info,
    GET_DTC_KB_TOOL_NAME: handle_get_dtc_knowledge_base_info,
    DISPLAY_ON_INTERFACE_TOOL_NAME: handle_display_on_interface,
    GET_TAXI_IDEAS_FOR_TODAY_TOOL_NAME: handle_get_taxi_ideas_for_today,
    GENERAL_GOOGLE_SEARCH_TOOL_NAME: handle_general_google_search,
    # Add new handlers for Phase 1
    SCHEDULE_OUTBOUND_CALL_TOOL_NAME: handle_schedule_outbound_call,
    CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME: handle_check_scheduled_call_status,
    GET_CONVERSATION_HISTORY_SUMMARY_TOOL_NAME: handle_get_conversation_history_summary,
    GENERATE_HTML_VISUALIZATION_TOOL_NAME: handle_generate_html_visualization 
}