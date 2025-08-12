#!/usr/bin/env python3
"""
Script to create a standalone HTML file with embedded CSV data.
This eliminates the need for a web server.
"""

import csv
import json
from pathlib import Path

def create_standalone_html():
    # Read the CSV data
    csv_path = Path("out/au_sg_big_roofs.csv")
    buildings_data = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            buildings_data.append(row)
    
    # Convert to JSON string for embedding
    buildings_json = json.dumps(buildings_data, indent=2)
    
    # Read the current HTML template
    html_path = Path("roof_viewer.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create standalone version
    standalone_html = html_content.replace(
        "// Load and parse CSV data",
        f"""// Embedded data (no server required)
        const embeddedData = {buildings_json};
        
        // Load and parse CSV data (now using embedded data)"""
    )
    
    standalone_html = standalone_html.replace(
        """async function loadData() {
            try {
                const response = await fetch('out/au_sg_big_roofs.csv');
                const csvText = await response.text();
                const data = parseCSV(csvText);
                buildingsData = data;""",
        """async function loadData() {
            try {
                // Use embedded data instead of fetching
                buildingsData = embeddedData;"""
    )
    
    # Write standalone version
    standalone_path = Path("roof_viewer_standalone.html")
    with open(standalone_path, 'w', encoding='utf-8') as f:
        f.write(standalone_html)
    
    print(f"✅ Created standalone HTML file: {standalone_path}")
    print(f"📁 File size: {standalone_path.stat().st_size / 1024:.1f} KB")
    print(f"🌐 You can now open this file directly in any browser!")
    print(f"📂 No web server required - just double-click the file.")

if __name__ == "__main__":
    create_standalone_html()
