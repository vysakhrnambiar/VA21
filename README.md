# Home Assistant Live

A real-time voice assistant with OpenAI integration, wake word detection, and tool capabilities.

## Project Overview

This project implements a voice assistant that:
- Listens for a wake word (using OpenWakeWord)
- Streams audio to OpenAI's real-time API
- Processes responses with text and audio
- Executes various tools based on assistant commands
- Provides a web interface for visual display

## Quick Start

### For Windows Users (Easiest Method)

1. Navigate to the `Install Guide` folder and double-click the `setup_environment.bat` file to automatically:
   - Check Python installation
   - Create a virtual environment
   - Install all required packages

2. Create a `.env` file with your API keys (see `.env.example`)

3. Activate the virtual environment (if not already activated):
   ```
   venv\Scripts\activate
   ```

4. Run the main application:
   ```
   python main.py
   ```

5. In separate terminal windows, also run:
   ```
   # Start the web server for the user interface
   python web_server.py
   
   # Start the call manager for outbound call processing
   python calling_agent.py
   ```

   Note: All three components (main application, web server, and call manager) need to be running simultaneously for the system to work properly.

### Manual Setup

If you prefer to set up manually or are using a different operating system:

1. Install Python 3.10 or newer
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install required packages:
   ```
   pip install -r "Install Guide\requirements.txt"
   ```
5. Create a `.env` file with your API keys
6. Run the main application:
   ```
   python main.py
   ```

7. In separate terminal windows, also run:
   ```
   # Start the web server for the user interface
   python web_server.py
   
   # Start the call manager for outbound call processing
   python calling_agent.py
   ```

   Note: All three components (main application, web server, and call manager) need to be running simultaneously for the system to work properly.

For detailed setup instructions, see `Install Guide\python_setup_guide.md`.

## Installation Files

All installation-related files are located in the `Install Guide` folder:
- `requirements.txt` - List of required Python packages
- `python_setup_guide.md` - Detailed installation instructions
- `setup_environment.bat` - Automated setup script for Windows
- `install_and_run.cmd` - Command reference guide

## Project Structure

### Core Components
- `main.py` - Main application entry point with audio processing and OpenAI integration
- `openai_client.py` - Handles OpenAI API communication and real-time audio streaming
- `web_server.py` - FastAPI server for web interface and UI notifications
- `wake_word_detector.py` - Wake word detection using OpenWakeWord

### Call Management System
- `calling_agent.py` - Outbound call processing manager
- `call_analyzer_and_strategist.py` - Analyzes call outcomes and determines next steps
- `conversation_history_db.py` - Database utilities for conversation history
- `dbsetup.py` - Database initialization and setup

### Tools and Integrations
- `tools_definition.py` - Defines available tools for the assistant
- `tool_executor.py` - Executes tools requested by the assistant
- `kb_llm_extractor.py` - Knowledge base extraction utilities
- `google_llm_services.py` - Google AI integration

### Frontend and Resources
- `frontend/` - Web interface files and user interaction
- `knowledge_bases/` - Knowledge base text files
- `static/` - Static assets like sounds and images
- `Install Guide/` - Installation and setup files
- `logs/` - Application log files

## Environment Variables

Create a `.env` file with the following variables:

### Required Variables
```
OPENAI_API_KEY=your_openai_api_key
OPENAI_REALTIME_MODEL_ID=gpt-4o
OPENAI_VOICE=alloy
WAKE_WORD_MODEL=hey_jarvis
WAKE_WORD_THRESHOLD=0.5
FASTAPI_DISPLAY_API_URL=http://localhost:8001/api/display
```

### Optional Variables
```
# Email functionality
RESEND_API_KEY=your_resend_api_key
DEFAULT_FROM_EMAIL=your_default_sender@example.com
RESEND_RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
RESEND_RECIPIENT_EMAILS_BCC=bcc1@example.com,bcc2@example.com
TICKET_EMAIL=ticket@example.com
RESEND_API_URL=https://api.resend.com/emails

# Google integration
GOOGLE_API_KEY=your_google_api_key

# Voice Activity Detection (VAD) settings for barge-in
LOCAL_VAD_ENABLED=true
LOCAL_VAD_ACTIVATION_THRESHOLD_MS=100
MIN_SPEECH_FRAMES_FOR_LOCAL_INTERRUPT=12
LOCAL_INTERRUPT_COOLDOWN_FRAMES=66
MIN_SILENCE_FRAMES_TO_RESET_LOCAL_VAD_STATE=3

# Audio and connection settings
TSM_PLAYBACK_SPEED=1.0
TSM_WINDOW_CHUNKS=8
END_CONV_AUDIO_FINISH_DELAY_S=2.0
OPENAI_RECONNECT_DELAY_S=5
OPENAI_PING_INTERVAL_S=20
OPENAI_PING_TIMEOUT_S=10

# Database monitor settings
DB_MONITOR_POLL_INTERVAL_S=20
FASTAPI_UI_STATUS_UPDATE_URL=http://localhost:8001/api/ui_status_update
FASTAPI_NOTIFY_CALL_UPDATE_URL=http://localhost:8001/api/notify_call_update_available

# Outbound calling (Twilio/Ultravox)
ULTRAVOX_API_KEY=your_ultravox_api_key
ULTRAVOX_AGENT_ID=your_ultravox_agent_id
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
CALLING_AGENT_POLLING_INTERVAL_SECONDS=10
CALLING_AGENT_MAX_RETRIES=3
CALLING_AGENT_COMPANY_NAME=Your Company Name
STRATEGIST_LLM_MODEL=gpt-4-turbo-preview
```

## Features

### Voice and Speech
- **Wake Word Detection**: Listens for a wake word to activate the assistant
- **Real-time Voice Interaction**: Streams audio to and from OpenAI with minimal latency
- **Voice Activity Detection (VAD)**: Allows for barge-in capability, letting users interrupt the assistant
- **Speaker Customization**: Configurable voice selection for the assistant

### Tools and Integrations
- **Tool Integration**: Executes various tools like email sending, knowledge base queries
- **Web Interface**: Displays visual content like charts and formatted text
- **Google AI Integration**: Optional integration with Google's Gemini model
- **Knowledge Base Access**: Query and extract information from local knowledge bases

### Outbound Calling System
- **Automated Outbound Calls**: Schedule and place automated calls using Twilio and Ultravox
- **Call Analysis**: AI-powered analysis of call outcomes to determine success or failure
- **Call Strategist**: Makes intelligent decisions about retry attempts based on call analysis
- **Database Integration**: Tracks call history and status updates

### Web Dashboard
- **Real-time Updates**: View live updates during conversations
- **Call Status Notifications**: Receive notifications about call completions and updates
- **TTS Announcements**: Get voice announcements about important events when in passive mode

## Troubleshooting

### General Issues
1. Check the `.env` file has all required API keys
2. Ensure your microphone is working and properly configured
3. For PyAudio issues on Windows, try:
   ```
   pip install pipwin
   pipwin install pyaudio
   ```
4. Check the log files in the `logs/` directory for detailed error messages
5. Verify all three components are running: main app, web server, and call manager

### Voice Assistant Issues
1. If wake word detection isn't working, adjust the `WAKE_WORD_THRESHOLD` value in `.env`
2. For issues with VAD (barge-in), try adjusting the VAD parameters in `.env`
3. If audio quality is poor, ensure your microphone isn't being used by another application

### Outbound Calling Issues
1. Verify Twilio and Ultravox credentials are correctly set in `.env`
2. Check the `calling_agent.log` for detailed error messages
3. Ensure the database is properly initialized using `dbsetup.py`
4. Make sure your Twilio account has sufficient funds for outbound calls

### Web Interface Issues
1. Confirm the web server is running on the expected port (default: 8001)
2. Check that the FASTAPI URLs in `.env` match your network configuration
3. Clear your browser cache if you're experiencing UI issues

For more detailed troubleshooting tips, see `Install Guide\python_setup_guide.md`.