#!/bin/bash

# Braunschweig Events Automation Script
# Set the project directory
PROJECT_DIR="/home/joern/Schreibtisch/Antigravity_Projects/Braunschweig-Events"

echo "======================================"
echo "Starte Braunschweig Event Scraper..."
echo "======================================"

cd "$PROJECT_DIR" || exit

# Activate Virtual Environment (if it exists)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the python script
echo "[1/3] Scraping und KI-Verarbeitung läuft..."
python main.py

# Check if main.py succeeded
if [ $? -eq 0 ]; then
    echo "[2/3] Script erfolgreich beendet! Prüfe auf neue .ics Dateien..."
    
    # Git add and commit
    git add output/*.ics
    
    # Check if there are changes to commit
    if git diff-index --quiet HEAD --; then
        echo "[3/3] Keine Änderungen in den .ics Dateien festgestellt. Git commit übersprungen."
    else
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
        git commit -m "Automatisiertes Kalender-Update: $TIMESTAMP"
        echo "[3/3] Neue Dateien in Git committet: $TIMESTAMP"
        
        # Git push (only if a remote is configured)
        if git remote | grep -q 'origin'; then
            echo "Pushe Änderungen zu Git Remote..."
            git push origin main
        else
            echo "Kein Git Remote (origin) konfiguriert. Push wird übersprungen."
            echo "Tipp: 'git remote add origin <url>' ausführen um automatischen Upload zu aktivieren."
        fi
    fi
else
    echo "Fehler beim Ausführen von main.py!"
    echo "Beliebige Taste drücken um dieses Fenster zu schließen..."
    read -n 1 -s
    exit 1
fi

echo "======================================"
echo "Vorgang abgeschlossen!"
echo "Beliebige Taste drücken um dieses Fenster zu schließen..."
read -n 1 -s
