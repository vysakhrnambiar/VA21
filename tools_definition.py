# tools_definition.py

# --- Tool Names (Constants) ---
END_CONVERSATION_TOOL_NAME = "end_conversation_and_listen_for_wakeword"
SEND_EMAIL_SUMMARY_TOOL_NAME = "send_email_discussion_summary"
RAISE_TICKET_TOOL_NAME = "raise_ticket_for_missing_knowledge"
GET_BOLT_KB_TOOL_NAME = "get_bolt_knowledge_base_info"
GET_DTC_KB_TOOL_NAME = "get_dtc_knowledge_base_info"
DISPLAY_ON_INTERFACE_TOOL_NAME = "display_on_interface"
GET_TAXI_IDEAS_FOR_TODAY_TOOL_NAME = "get_taxi_ideas_for_today"
GENERAL_GOOGLE_SEARCH_TOOL_NAME = "general_google_search"

# New Tool Names for Phase 1
SCHEDULE_OUTBOUND_CALL_TOOL_NAME = "schedule_outbound_call"
CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME = "check_scheduled_call_status"

GENERATE_HTML_VISUALIZATION_TOOL_NAME = "generate_html_visualization" # <<<< NEW TOOL NAME

GET_CONVERSATION_HISTORY_SUMMARY_TOOL_NAME = "get_conversation_history_summary"


TOOL_GET_CONVERSATION_HISTORY_SUMMARY = {
    "type": "function",
    "name": GET_CONVERSATION_HISTORY_SUMMARY_TOOL_NAME,
    "description": (
        "Retrieves and summarizes past conversation history to answer user questions about previous discussions. "
        "Use this if the user asks about specific past topics, what was said on a certain day/time, or refers to past "
        "interactions not immediately in the current short-term context."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date_reference": {
                "type": "string",
                "description": "Optional. A specific date (e.g., 'yesterday', '2024-05-29', 'last Tuesday') to filter history. If referring to 'today', use the current date."
            },
            "time_of_day_reference": {
                "type": "string",
                "description": "Optional. A time of day (e.g., 'morning', 'around 2 PM', 'evening') to combine with the date_reference for more specific filtering."
            },
            "keywords": {
                "type": "string",
                "description": "Optional. Specific keywords, phrases, or topics to search for within the historical conversation content (e.g., 'Dubai limo rates', 'Bolt payment')."
            },
            "user_question_about_history": {
                "type": "string",
                "description": "Mandatory. The user's actual question about the history, which will guide the summarization (e.g., 'What did we discuss about project alpha last week?')."
            },
            "max_turns_to_scan": { # Renamed from turns_limit for clarity
                "type": "integer",
                "description": "Optional. Maximum number of recent historical turns to scan if no specific date/keywords narrow it down significantly. Default is a system value (e.g., 100)."
            }
        },
        "required": ["user_question_about_history"] # Make the user's question mandatory
    }
}

# --- Tool Definitions ---

TOOL_END_CONVERSATION = {
    "type": "function",
    "name": END_CONVERSATION_TOOL_NAME,
    "description": (
        "Call this function when the current conversation topic or user's immediate query has been fully addressed, "
        "and the assistant should return to a passive state, listening for its wake word to be reactivated. "
        "Also use this if the user explicitly ends the conversation (e.g., 'thank you, that's all', 'goodbye', "
        "'stop listening', 'go to sleep')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "A brief reason why the conversation is ending or why the assistant is returning to listen mode. "
                    "For example: 'User said goodbye', 'User's query resolved', 'User requested to stop'."
                )
            }
        },
        "required": ["reason"]
    }
}

TOOL_SEND_EMAIL_SUMMARY = {
    "type": "function",
    "name": SEND_EMAIL_SUMMARY_TOOL_NAME,
    "description": "Sends an email summary of the current or recent discussion to pre-configured recipients. Use this when the user explicitly asks to email the conversation or key points discussed.",
    "parameters": {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "A concise and relevant subject line for the email, summarizing the content."
            },
            "body_summary": {
                "type": "string",
                "description": "The main content of the email, summarizing the key points of the discussion. This will be formatted into an HTML email."
            }
        },
        "required": ["subject", "body_summary"]
    }
}

TOOL_RAISE_TICKET = {
    "type": "function",
    "name": RAISE_TICKET_TOOL_NAME,
    "description": "If the user asks a question and the information is not found in the available knowledge bases (Bolt KB, DTC KB), first ask the user if they want to raise a ticket to request this information be added. If they agree, call this function to send an email to the admin.",
    "parameters": {
        "type": "object",
        "properties": {
            "user_query": {
                "type": "string",
                "description": "The specific question or topic the user asked about that was not found in the knowledge base."
            },
            "additional_context": {
                "type": "string",
                "description": "Any relevant context from the conversation that might help the admin understand the user's need for this missing information. Be concise."
            }
        },
        "required": ["user_query"]
    }
}

TOOL_GET_BOLT_KB = {
    "type": "function",
    "name": GET_BOLT_KB_TOOL_NAME,
    "description": "Retrieves information specifically about Bolt services, operations, or data from the Bolt knowledge base. Use this when the user's query is clearly about Bolt. Provide the specific user query or topic to search for.",
    "parameters": {
        "type": "object",
        "properties": {
            "query_topic": {
                "type": "string",
                "description": "The specific topic or keywords from the user's question about Bolt to search for in the knowledge base (e.g., 'Bolt revenue yesterday', 'Bolt promotions', 'Bolt total orders March'). Be specific."
            }
        },
        "required": ["query_topic"]
    }
}

TOOL_GET_DTC_KB = {
    "type": "function",
    "name": GET_DTC_KB_TOOL_NAME,
    "description": "Retrieves information specifically about DTC services, limousine operations, or general DTC data from the DTC knowledge base. Use this when the user's query is clearly about DTC or limousines. Provide the specific user query or topic to search for.",
    "parameters": {
        "type": "object",
        "properties": {
            "query_topic": {
                "type": "string",
                "description": "The specific topic or keywords from the user's question about DTC to search for in the knowledge base (e.g., 'DTC fleet size', 'DTC airport transfer revenue', 'DTC contact'). Be specific."
            }
        },
        "required": ["query_topic"]
    }
}

TOOL_DISPLAY_ON_INTERFACE = {
    "type": "function",
    "name": DISPLAY_ON_INTERFACE_TOOL_NAME,
    "description": (
        "Sends structured data to a connected web interface for visual display. "
        "Use this tool when a visual representation (text, markdown, or graph) would enhance the user's understanding. "
        "The web interface can display markdown (including tables), and various chart types (bar, line, pie)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "display_type": {
                "type": "string",
                "enum": ["markdown", "graph_bar", "graph_line", "graph_pie"],
                "description": "The type of content to display. 'markdown' for text, lists, and tables. 'graph_bar', 'graph_line', or 'graph_pie' for charts."
            },
            "title": {
                "type": "string",
                "description": "An optional title for the content. For graphs, this is the chart title. For markdown, it can be a main heading (e.g., '## My Title')."
            },
            "data": {
                "type": "object",
                "description": "The actual data payload, structured according to the 'display_type'. See examples for each type.",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "For 'markdown' display_type: The full markdown string. Can include headings, lists, bold/italic text, and tables (e.g., '| Header1 | Header2 |\\n|---|---|\\n| Val1 | Val2 |')."
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For graph types: An array of strings for the X-axis labels (bar, line) or segment labels (pie)."
                    },
                    "datasets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "Name of this dataset (e.g., 'Sales Q1', 'Temperature')."},
                                "values": {"type": "array", "items": {"type": "number"}, "description": "Array of numerical data points corresponding to 'labels'."}
                            },
                            "required": ["label", "values"]
                        },
                        "description": "For graph types: An array of dataset objects. Each object contains a label for the dataset and its corresponding values. For pie charts, typically only one dataset is used."
                    },
                    "options": {
                        "type": "object",
                        "properties": {
                            "animated": {"type": "boolean", "description": "Suggest if the graph should be animated (if supported by the frontend). Default: true."},
                            "x_axis_label": {"type": "string", "description": "Optional label for the X-axis of bar or line charts."},
                            "y_axis_label": {"type": "string", "description": "Optional label for the Y-axis of bar or line charts."}
                        },
                        "description": "Optional: General display options or hints for the frontend, like animation or axis labels for graphs."
                    }
                },
                "description_detailed_examples": ( 
                    "Example for 'markdown': data: { 'content': '# Report Title\\n- Point 1\\n- Point 2\\n| Col A | Col B |\\n|---|---|\\n| 1 | 2 |' }\n"
                    "Example for 'graph_bar': data: { 'labels': ['Jan', 'Feb'], 'datasets': [{'label': 'Revenue', 'values': [100, 150]}], 'options': {'x_axis_label': 'Month'} }\n"
                    "Example for 'graph_pie': data: { 'labels': ['Slice A', 'Slice B'], 'datasets': [{'label': 'Distribution', 'values': [60, 40]}] }"
                )
            }
        },
        "required": ["display_type", "data"]
    }
}

TOOL_GET_TAXI_IDEAS = {
    "type": "function",
    "name": GET_TAXI_IDEAS_FOR_TODAY_TOOL_NAME,
    "description": (
        "Fetches actionable ideas, relevant news, and event information for taxi services in Dubai for the current day. "
        "Use this when specifically asked for daily taxi deployment suggestions, event-based opportunities, local news relevant to transport, "
        "or operational ideas for today. The tool requires the current date."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "current_date": {
                "type": "string",
                "description": "The current date in 'Month DD, YYYY' format (e.g., 'May 24, 2025'). This is mandatory to get relevant information for today."
            },
            "specific_focus": {
                "type": "string",
                "description": "Optional: A specific focus for the ideas, like 'airport demand', 'major sporting events', or 'shopping mall traffic'."
            }
        },
        "required": ["current_date"]
    }
}

TOOL_GENERAL_GOOGLE_SEARCH = {
    "type": "function",
    "name": GENERAL_GOOGLE_SEARCH_TOOL_NAME,
    "description": (
        "Searches the internet using Google for information on general topics, current events, business news, "
        "competitor information, or other subjects not covered by internal knowledge bases. "
        "Primarily for queries related to Dubai, professional contexts, or general knowledge. "
        "Use for questions like 'What is the weather in Dubai today?', 'Latest news on autonomous taxis in UAE', "
        "or 'Who is the CEO of Company X?'"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "search_query": {
                "type": "string",
                "description": "The specific and concise query to search on Google. Example: 'current fuel prices in Dubai', 'traffic conditions Sheikh Zayed Road now'."
            }
        },
        "required": ["search_query"]
    }
}

# --- New Tool Definitions for Phase 1 ---

TOOL_SCHEDULE_OUTBOUND_CALL = {
    "type": "function",
    "name": SCHEDULE_OUTBOUND_CALL_TOOL_NAME,
    "description": "Schedules an outbound call to be made by the automated calling system. Provide the phone number, contact name, and a detailed objective for the call.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone_number": {
                "type": "string",
                "description": "The international phone number to call (e.g., '+1234567890')."
            },
            "contact_name": {
                "type": "string",
                "description": "The name of the person or entity to be called."
            },
            "call_objective": {
                "type": "string",
                "description": "A detailed description of what the call aims to achieve. This will be used by the automated agent to conduct the call."
            }
        },
        "required": ["phone_number", "contact_name", "call_objective"]
    }
}

# In tools_definition.py

# (SCHEDULE_OUTBOUND_CALL_TOOL_NAME and CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME already defined)

TOOL_CHECK_SCHEDULED_CALL_STATUS = {
    "type": "function",
    "name": CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME, # Assuming CHECK_SCHEDULED_CALL_STATUS_TOOL_NAME is already defined
    "description": (
        "Checks the status of a previously scheduled outbound call. "
        "You can query by contact name, a snippet of the call's objective, or the approximate date/time of the call or its expected completion. "
        "The system will try to find the most relevant call."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "contact_name": {
                "type": "string",
                "description": "Optional: The name of the contact for the call you want to check (e.g., 'Mr. Akhil')."
            },
            "call_objective_snippet": {
                "type": "string",
                "description": "Optional: A keyword or phrase from the objective of the call (e.g., 'fleet deployment', 'Q3 report')."
            },
            "date_reference": {
                "type": "string",
                "description": (
                    "Optional: A specific date (e.g., 'May 20th', '2024-05-20', 'yesterday', 'today') or a relative time reference "
                    "(e.g., 'last call', 'most recent', 'two days back', 'this morning', 'yesterday afternoon')."
                )
            },
            "time_of_day_preference": {
                "type": "string",
                "enum": ["any", "morning", "afternoon", "evening"],
                "description": "Optional: If a date is specified, further refine by time of day (e.g., 'morning', 'afternoon'). Defaults to 'any' if not specified."
            },
            "job_id": { # Keep for system use, but deprioritize for user-facing LLM instructions
                "type": "integer",
                "description": "Optional: The specific internal ID of the scheduled call job. Less common for users to know."
            }
        },
        # No parameters strictly required by schema; handler will manage.
    }
}



# New Tool Definition for HTML Visualization Generation
TOOL_GENERATE_HTML_VISUALIZATION = {
    "type": "function",
    "name": GENERATE_HTML_VISUALIZATION_TOOL_NAME,
    "description": ( # <<<< UPDATED DESCRIPTION
        "Generates and **displays** a self-contained HTML visualization on the user's screen based on the user's request and "
        "optionally, data from internal knowledge bases (DTC, Bolt, or both). "
        "This tool handles both the creation of the HTML and sending it for display."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "user_request": {
                "type": "string",
                "description": "The user's original request or a detailed description of the desired visualization (e.g., 'Show me last month's Bolt ride types as a pie chart', 'Create a dashboard of DTC key performance indicators from the knowledge base')."
            },
            "knowledge_base_source": {
                "type": "string",
                "enum": ["dtc", "bolt", "both", "none"],
                "description": "Specifies which knowledge base content should be provided to generate the visualization. Use 'none' if the visualization is based solely on the user_request and does not require specific KB data."
            },
            "title": {
                "type": "string",
                "description": "Optional: A title for the visualization. This title will be used for the HTML page and may be displayed prominently."
            }
        },
        "required": ["user_request", "knowledge_base_source"]
    }
}

# Ensure ALL_TOOLS list includes this updated definition.


# List of all tools to be passed to OpenAI
ALL_TOOLS = [
    TOOL_END_CONVERSATION,
    TOOL_SEND_EMAIL_SUMMARY,
    TOOL_RAISE_TICKET,
    TOOL_GET_BOLT_KB,
    TOOL_GET_DTC_KB,
    TOOL_DISPLAY_ON_INTERFACE,
    TOOL_GET_TAXI_IDEAS,
    TOOL_GENERAL_GOOGLE_SEARCH,
    # Add new tools for Phase 1
    TOOL_SCHEDULE_OUTBOUND_CALL,
    TOOL_CHECK_SCHEDULED_CALL_STATUS,
    TOOL_GET_CONVERSATION_HISTORY_SUMMARY,
    TOOL_GENERATE_HTML_VISUALIZATION # <<<< ADDED NEW TOOL TO THE LIST

]