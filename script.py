#!/usr/bin/env python3
"""
AI-Agent (MVP) – Grosse Dächer um Au SG

Funktion:
•⁠  ⁠Holt Gebäude-Footprints via Overpass API (OpenStreetMap) im Kreis um Au SG
•⁠  ⁠Berechnet Dachfläche (≈ Gebäude-Footprint) in m²
•⁠  ⁠Filtert ab minimaler Fläche (Default 100 m²)
•⁠  ⁠Heuristische Priorisierung (Fläche + Kompaktheit)
•⁠  ⁠Exportiert CSV und GeoJSON

Nutzung:
  pip install -r requirements.txt  # siehe unten
  python big_roofs_au_sg.py --radius-km 10 --min-area 100 --limit 500

Outputs:
  ./out/au_sg_big_roofs.csv
  ./out/au_sg_big_roofs.geojson

Hinweis:
•⁠  ⁠MVP verarbeitet primär OSM-Ways (Gebäudeumrisse). Multipolygone (Relations) werden teilweise ignoriert.
•⁠  ⁠Für die Flächenberechnung wird nach EPSG:2056 (CH1903+ / LV95) projiziert, passend für die Schweiz.
•⁠  ⁠PV-Score ist eine einfache Heuristik und dient nur zur Priorisierung.
"""

import argparse
import json
import math
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import requests
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid
from pyproj import Transformer
import pandas as pd

# -------------------------
# Konfiguration
# -------------------------
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Zentrum Au SG – Koordinaten (WGS84)
# Quelle: approximiert (Gemeinde Au, Kanton St. Gallen)
AU_SG_LAT = 47.4319
AU_SG_LON = 9.6397

# Transformer: WGS84 -> LV95 (EPSG:2056)
_transformer_to_lv95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
_transformer_to_wgs84 = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)


def to_lv95(lon: float, lat: float) -> Tuple[float, float]:
    x, y = _transformer_to_lv95.transform(lon, lat)
    return x, y


def to_wgs84(x: float, y: float) -> Tuple[float, float]:
    lon, lat = _transformer_to_wgs84.transform(x, y)
    return lon, lat


@dataclass
class RoofCandidate:
    osm_type: str  # 'way' oder 'relation'
    osm_id: int
    name: Optional[str]
    building: Optional[str]
    area_m2: float
    compactness: float
    score: float
    centroid_lat: float
    centroid_lon: float
    google_maps: str
    osm_url: str


def overpass_query(lat: float, lon: float, radius_m: int) -> Dict:
    """Fragt Overpass nach Gebäuden im Umkreis ab und liefert raw JSON zurück."""
    q = f"""
    [out:json][timeout:120];
    (
      way["building"](around:{radius_m},{lat},{lon});
      relation["building"](around:{radius_m},{lat},{lon});
    );
    out tags geom;
    """
    last_exc = None
    for ep in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(ep, data={"data": q}, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            continue
    raise RuntimeError(f"Overpass nicht erreichbar: {last_exc}")


def polygon_from_geom(geom: List[Dict[str, float]]) -> Optional[Polygon]:
    """Erzeugt ein Shapely-Polygon aus Overpass 'geom' (Liste von Punkten mit lat/lon)."""
    if not geom or len(geom) < 3:
        return None
    # Overpass liefert lat/lon; wir brauchen lon/lat Reihenfolge für Shapely (x=lon, y=lat)
    coords = [(pt["lon"], pt["lat"]) for pt in geom]
    # Schliessen, falls nötig
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = make_valid(poly)
        # Einige building ways sind Linien (keine Fläche)
        if poly.is_empty or poly.area == 0:
            return None
        return poly
    except Exception:
        return None


def area_m2_in_lv95(poly_wgs84: Polygon) -> float:
    # Transformiere alle Koordinaten nach LV95 und berechne Fläche in m²
    xys = [to_lv95(lon, lat) for lon, lat in poly_wgs84.exterior.coords]
    p_lv95 = Polygon(xys)
    return abs(p_lv95.area)


def perimeter_m_in_lv95(poly_wgs84: Polygon) -> float:
    xys = [to_lv95(lon, lat) for lon, lat in poly_wgs84.exterior.coords]
    p_lv95 = Polygon(xys)
    return p_lv95.length


def calc_compactness(area: float, perimeter: float) -> float:
    if perimeter == 0:
        return 0.0
    # Polsby-Popper: 4πA / P²  -> 1 = Kreis, ~0 = sehr zerklüftet
    return float((4 * math.pi * area) / (perimeter * perimeter))


def guess_building_class(tags: Dict[str, str]) -> Optional[str]:
    b = (tags or {}).get("building")
    if not b:
        return None
    b = b.lower()
    mapping_guess = {
        "industrial": "industrial",
        "warehouse": "warehouse",
        "retail": "retail",
        "commercial": "commercial",
        "supermarket": "retail",
        "school": "public",
        "university": "public",
        "hospital": "public",
        "kindergarten": "public",
        "public": "public",
        "garage": "industrial",
        "manufacture": "industrial",
        "factory": "industrial",
    }
    for k, v in mapping_guess.items():
        if k in b:
            return v
    # Default grob klassieren
    return "other"


def build_candidate(el: Dict) -> Optional[RoofCandidate]:
    osm_type = el.get("type")  # 'way' oder 'relation'
    osm_id = el.get("id")
    tags = el.get("tags", {})

    geom = el.get("geometry") or el.get("geom")  # Overpass liefert 'geometry'
    poly = polygon_from_geom(geom)
    if poly is None:
        return None

    area_m2 = area_m2_in_lv95(poly)
    perim_m = perimeter_m_in_lv95(poly)
    compact = calc_compactness(area_m2, perim_m)

    centroid = poly.centroid
    centroid_lon, centroid_lat = centroid.x, centroid.y

    name = tags.get("name")
    bcls = tags.get("building")

    # Einfache Score-Heuristik: Fläche (70%) + Kompaktheit (30%)
    # Kompaktheit ~0..1, skaliert
    score = 0.7 * (area_m2) + 0.3 * (compact * 10000)  # Kompaktheit schwächer skaliert

    gmaps = f"https://www.google.com/maps/search/?api=1&query={centroid_lat:.6f}%2C{centroid_lon:.6f}"
    osm_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

    return RoofCandidate(
        osm_type=osm_type,
        osm_id=osm_id,
        name=name,
        building=bcls,
        area_m2=float(area_m2),
        compactness=float(compact),
        score=float(score),
        centroid_lat=float(centroid_lat),
        centroid_lon=float(centroid_lon),
        google_maps=gmaps,
        osm_url=osm_url,
    )


def rank_and_filter(cands: List[RoofCandidate], min_area: float, limit: int) -> List[RoofCandidate]:
    rows = [c for c in cands if c.area_m2 >= min_area]
    rows.sort(key=lambda x: (-x.area_m2, -x.score))
    return rows[:limit]


def export_csv(cands: List[RoofCandidate], path: str) -> None:
    df = pd.DataFrame([
        {
            "osm_type": c.osm_type,
            "osm_id": c.osm_id,
            "name": c.name,
            "building_tag": c.building,
            "area_m2": round(c.area_m2, 1),
            "compactness": round(c.compactness, 4),
            "score": round(c.score, 1),
            "lat": round(c.centroid_lat, 6),
            "lon": round(c.centroid_lon, 6),
            "google_maps": c.google_maps,
            "osm_url": c.osm_url,
        }
        for c in cands
    ])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def export_geojson(cands: List[RoofCandidate], path: str) -> None:
    features = []
    for c in cands:
        # Re-konstruiere ein (kleines) Quadrat um den Zentroiden als Platzhalter-Geometrie
        # (Für echte Footprints müsste man die Original-Polygone mitschreiben; hier MVP.)
        # Optional: In Zukunft Original-Polygon speichern.
        lon, lat = c.centroid_lon, c.centroid_lat
        # winziges Quadrat (5m) im LV95, dann zurückprojizieren
        x, y = to_lv95(lon, lat)
        d = 2.5  # 5 m Kantenlänge
        square_lv95 = [(x-d, y-d), (x+d, y-d), (x+d, y+d), (x-d, y+d), (x-d, y-d)]
        coords = [to_wgs84(px, py) for (px, py) in square_lv95]
        poly = {
            "type": "Polygon",
            "coordinates": [[(lng, lat) for (lng, lat) in coords]]
        }
        features.append({
            "type": "Feature",
            "geometry": poly,
            "properties": {
                "osm_type": c.osm_type,
                "osm_id": c.osm_id,
                "name": c.name,
                "building_tag": c.building,
                "area_m2": round(c.area_m2, 1),
                "compactness": round(c.compactness, 4),
                "score": round(c.score, 1),
                "google_maps": c.google_maps,
                "osm_url": c.osm_url,
            }
        })
    fc = {"type": "FeatureCollection", "features": features}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Grosse Dächer um Au SG finden (OSM/Overpass)")
    ap.add_argument("--lat", type=float, default=AU_SG_LAT, help="Zentrum Latitude (WGS84)")
    ap.add_argument("--lon", type=float, default=AU_SG_LON, help="Zentrum Longitude (WGS84)")
    ap.add_argument("--radius-km", type=float, default=10.0, help="Radius in km")
    ap.add_argument("--min-area", type=float, default=100.0, help="minimale Dachfläche in m²")
    ap.add_argument("--limit", type=int, default=1000, help="max. Anzahl Ergebnisse")
    ap.add_argument("--out-prefix", type=str, default="out/au_sg_big_roofs", help="Pfadpräfix für Exporte")
    args = ap.parse_args()

    radius_m = int(args.radius_km * 1000)
    print(f"Hole OSM-Daten: lat={args.lat}, lon={args.lon}, radius={radius_m} m ...")
    data = overpass_query(args.lat, args.lon, radius_m)

    elements = data.get("elements", [])
    print(f"Empfangen: {len(elements)} Elemente. Verarbeite …")

    candidates: List[RoofCandidate] = []
    for el in elements:
        c = build_candidate(el)
        if c is not None:
            candidates.append(c)

    print(f"Gebäude mit Fläche berechnet: {len(candidates)}")
    ranked = rank_and_filter(candidates, args.min_area, args.limit)
    print(f"Gefiltert (>= {args.min_area} m²): {len(ranked)}")

    csv_path = f"{args.out_prefix}.csv"
    geojson_path = f"{args.out_prefix}.geojson"
    export_csv(ranked, csv_path)
    export_geojson(ranked, geojson_path)

    print("\nFertig. Dateien:")
    print(" - ", csv_path)
    print(" - ", geojson_path)


if __name__ == "__main__":
    main()

"""
requirements.txt (als Referenz):
requests
shapely
pyproj
pandas
"""