#!/bin/bash

echo "Starting Home Assistant Live service manager..."
echo "This script ensures services run in the proper virtual environment"

# Check if the virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found in current directory."
    echo "Please run this script from the project root where the virtual environment is located"
    echo "or manually activate your virtual environment before running the process_manager.py script."
    exit 1
fi

# Run the process manager
python process_manager.py

# Deactivate the virtual environment when done
deactivate