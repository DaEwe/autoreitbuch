#!/bin/bash
cd ~/autoreitbuch
# Load env vars
export $(grep -v '^#' .env | xargs)
# Run script
/usr/bin/python3 src/main.py --book >> booking.log 2>&1
