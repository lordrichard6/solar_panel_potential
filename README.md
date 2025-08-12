# Solar Panel Potential - Au, St. Gallen

An AI-powered tool for identifying large rooftops with solar panel installation potential in the Au, St. Gallen region of Switzerland.

## 🌟 Features

- **Data Collection**: Automatically fetches building footprints from OpenStreetMap via Overpass API
- **Area Calculation**: Calculates precise roof areas using Swiss coordinate system (EPSG:2056 - CH1903+ / LV95)
- **Smart Filtering**: Filters buildings by minimum area and building type
- **Heuristic Scoring**: Prioritizes buildings based on area and compactness
- **Interactive Visualization**: Web-based UI with interactive map and building details
- **Export Options**: Outputs data as CSV and GeoJSON formats

## 🚀 Quick Start

### Option 1: View Results (No Setup Required)
Simply open `roof_viewer_standalone.html` in any web browser to explore the data interactively.

### Option 2: Generate New Data
1. Install dependencies:
   ```bash
   pip install requests shapely pyproj pandas
   ```

2. Run the data collection script:
   ```bash
   python script.py --radius-km 10 --min-area 100 --limit 1000
   ```

3. Create standalone viewer:
   ```bash
   python create_standalone.py
   ```

## 📊 Current Dataset

- **Region**: 10km radius around Au, St. Gallen (47.4319°N, 9.6397°E)
- **Total Buildings Analyzed**: 86,252
- **Large Roofs (≥100m²)**: 1,000 buildings
- **Data Source**: OpenStreetMap (via Overpass API)
- **Last Updated**: August 2025

## 🗂️ Files

- `script.py` - Main data collection script
- `roof_viewer_standalone.html` - Interactive web viewer (self-contained)
- `create_standalone.py` - Creates standalone HTML with embedded data
- `serve_ui.py` - Local web server for development

## 🎯 Use Cases

- **Solar Panel Installation Planning**: Identify buildings with large roof areas
- **Energy Planning**: Assess solar potential in the region
- **Urban Development**: Understand building distribution and characteristics
- **Research**: Study building patterns and roof characteristics

## 🔧 Configuration

The script supports various command-line options:

```bash
python script.py --help
```

Options:
- `--lat`, `--lon`: Center coordinates (default: Au SG)
- `--radius-km`: Search radius in kilometers (default: 10)
- `--min-area`: Minimum roof area in m² (default: 100)
- `--limit`: Maximum number of results (default: 1000)

## 📈 Scoring Algorithm

Buildings are scored using a heuristic combining:
- **Area (70% weight)**: Larger roofs score higher
- **Compactness (30% weight)**: More regular shapes score higher (better for panel installation)

## 🗺️ Interactive Map Features

- **Color-coded markers**: Green (small), Orange (medium), Red (large), Purple (extra large)
- **Filtering**: By area, building type, and name
- **Real-time statistics**: Total area, average area, building count
- **External links**: Direct links to Google Maps and OpenStreetMap
- **Responsive design**: Works on desktop and mobile

## 📄 License

This project uses OpenStreetMap data, which is available under the Open Database License.

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the tool.

---

*Generated with AI assistance for solar energy potential assessment in Switzerland*
