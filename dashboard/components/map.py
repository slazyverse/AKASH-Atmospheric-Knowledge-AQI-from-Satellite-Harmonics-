"""
dashboard/components/map.py — Reusable GIS Mapping Components for VAYU-DRISHTI.

Implements folium-based mapping components for:
  - Surface AQI (cpcb station circle markers, colored by category, with detailed popups)
  - HCHO Hotspots (hotspot boundary circles and density overlays)
  - Active Fires (location markers scaled and colored by Fire Radiative Power (FRP))
  - ML Forecast Coverage

All maps support CartoDB DarkMatter, OpenStreetMap, and Esri World Imagery tiles,
with coordinate display via plugins.MousePosition, and pre-integrated raster layer toggles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

import folium
from folium import plugins
from branca.element import Element
from streamlit_folium import st_folium

from dashboard.core.gis_interfaces import (
    AQIRasterInterface,
    HCHORasterInterface,
    FireRasterInterface,
)
from dashboard.core.theme import (
    AQI_GOOD,
    AQI_MODERATE,
    AQI_POOR,
    AQI_SATISFACTORY,
    AQI_SEVERE,
    AQI_VERY_POOR,
    ACCENT_ORANGE,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BG_SURFACE,
    BORDER_DEFAULT,
)


def _get_cpcb_color(category: str) -> str:
    """Helper to map a category name to the correct brand color code."""
    colors = {
        "Good": AQI_GOOD,
        "Satisfactory": AQI_SATISFACTORY,
        "Moderate": AQI_MODERATE,
        "Poor": AQI_POOR,
        "Very Poor": AQI_VERY_POOR,
        "Severe": AQI_SEVERE,
    }
    return colors.get(category, PRIMARY)


def create_base_map(
    center: list[float] = [22.5, 78.5],
    zoom: int = 5,
) -> folium.Map:
    """
    Create a folium Map initialized with multiple tilesets and standard GIS controls.
    CartoDB DarkMatter is default to align with the application theme.
    """
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,  # Handled below
        zoom_control=True,
    )

    # 1. Base Layer Tile Providers
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        name="CartoDB DarkMatter (Default)",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains="abcd",
        max_zoom=20,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        name="OpenStreetMap Standard",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        max_zoom=19,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="Esri World Imagery (Satellite)",
        attr="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        max_zoom=18,
        control=True,
    ).add_to(m)

    # 2. Add Leaflet Plugins (Fullscreen, Mouse coordinates position)
    plugins.Fullscreen(
        position="topright",
        title="Fullscreen View",
        title_cancel="Exit Fullscreen",
        force_separate_button=True,
    ).add_to(m)

    # Display hover coordinates at the bottom right corner
    plugins.MousePosition(
        position="bottomright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=4,
        prefix="Coordinate: ",
    ).add_to(m)

    return m


# ── Map 1: Surface AQI Spatial Distribution ──────────────────────────────────

def render_aqi_spatial_map(readings: list[Any], key: str = "aqi_map") -> None:
    """
    Render a map showing monitoring stations as markers colored by their AQI categories.
    Includes popup cards and a placeholder layer for future satellite raster overlays.
    """
    m = create_base_map(center=[22.8, 79.0], zoom=5)

    # 1. Concrete GIS Overlay Layer Group for Stations
    station_group = folium.FeatureGroup(name="CPCB Ground Stations", overlay=True, control=True)

    for r in readings:
        color = _get_cpcb_color(r.aqi_category)

        # Style a beautiful, custom dark HTML card for the marker popup
        popup_html = f"""
        <div style="
            width:240px; 
            background-color: {BG_SURFACE}; 
            color: {TEXT_PRIMARY}; 
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            padding: 8px;
            font-size: 12px;
        ">
            <h5 style="color: {PRIMARY}; margin: 0 0 6px 0; font-size: 13px; font-weight:600;">📍 {r.station_name}</h5>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color: {TEXT_SECONDARY};">AQI Value:</span>
                <span style="
                    background-color: {color}22; 
                    color: {color}; 
                    border: 1px solid {color}66;
                    padding: 1px 6px;
                    border-radius: 10px;
                    font-weight: bold;
                ">{r.aqi_value} ({r.aqi_category})</span>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead>
                    <tr style="border-bottom: 1px solid {BORDER_DEFAULT}; text-align:left; color:{TEXT_SECONDARY};">
                        <th>Pollutant</th>
                        <th style="text-align:right;">Val</th>
                        <th style="text-align:right;">Unit</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>PM2.5</td><td style="text-align:right; font-weight:bold;">{r.pm25}</td><td style="text-align:right;">µg/m³</td></tr>
                    <tr><td>PM10</td><td style="text-align:right; font-weight:bold;">{r.pm10}</td><td style="text-align:right;">µg/m³</td></tr>
                    <tr><td>NO2</td><td style="text-align:right; font-weight:bold;">{r.no2}</td><td style="text-align:right;">µg/m³</td></tr>
                    <tr><td>SO2</td><td style="text-align:right; font-weight:bold;">{r.so2}</td><td style="text-align:right;">µg/m³</td></tr>
                    <tr><td>O3</td><td style="text-align:right; font-weight:bold;">{r.o3}</td><td style="text-align:right;">µg/m³</td></tr>
                    <tr><td>CO</td><td style="text-align:right; font-weight:bold;">{r.co}</td><td style="text-align:right;">mg/m³</td></tr>
                </tbody>
            </table>
            <div style="font-size:9px; color:{TEXT_SECONDARY}; margin-top:8px; border-top: 1px solid {BORDER_DEFAULT}; padding-top:4px; text-align:right;">
                Updated: {r.recorded_at.strftime('%Y-%m-%d %H:%M UTC')}
            </div>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=260)

        # We use circle markers for cleaner vector representations
        folium.CircleMarker(
            location=[r.latitude, r.longitude],
            radius=8,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1.5,
            tooltip=f"{r.station_name} — AQI: {r.aqi_value}",
        ).add_to(station_group)

    station_group.add_to(m)
    if readings:
        bounds = [[r.latitude, r.longitude] for r in readings]
        m.fit_bounds(bounds, padding=(20, 20))

    # 2. Satellite / COG Raster Integration Layer (Future Day 5 Expansion Point)
    aqi_raster = AQIRasterInterface()
    tile_url = aqi_raster.get_tile_url(datetime.utcnow())
    folium.raster_layers.TileLayer(
        tiles=tile_url,
        attr="VAYU-DRISHTI Kriging Interpolation Model",
        name="Interpolated AQI Raster (COG Overlay)",
        overlay=True,
        control=True,
        opacity=0.6,
        show=False,  # Hidden by default, toggled via Leaflet controls
    ).add_to(m)

    # 3. Add Floating AQI Legend
    _add_aqi_legend_element(m)

    # 4. Layer control toggles
    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    # 5. Render via streamlit-folium
    st_folium(m, height=450, use_container_width=True, key=key)


def _add_aqi_legend_element(m: folium.Map) -> None:
    """Floating card legend injected directly into the map wrapper."""
    legend_html = f"""
    <div style="
        position: fixed; 
        bottom: 20px; left: 20px; width: 140px; 
        background-color: rgba(22, 27, 34, 0.85);
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 8px;
        z-index:9999; font-size:11px;
        color: {TEXT_PRIMARY};
        padding: 10px;
        font-family: 'Inter', sans-serif;
    ">
        <div style="font-weight:600; margin-bottom:6px; color:{PRIMARY};">AQI Category</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_GOOD}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Good</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_SATISFACTORY}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Satisfactory</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_MODERATE}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Moderate</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_POOR}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Poor</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_VERY_POOR}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Very Poor</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{AQI_SEVERE}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Severe</div>
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))


# ── Map 2: HCHO Hotspots Map ─────────────────────────────────────────────────

def render_hcho_spatial_map(hotspots: list[Any], key: str = "hcho_map") -> None:
    """
    Render a map displaying formaldehyde hotspots as circles sized by radius_km.
    Includes placeholder layers for both satellite density COG and interactive HeatMap.
    """
    m = create_base_map(center=[21.0, 81.0], zoom=5)

    # 1. Hotspot circles overlay
    hotspot_group = folium.FeatureGroup(name="Detected Hotspots (Sentinel-5P)", overlay=True, control=True)

    for h in hotspots:
        # Style details card
        popup_html = f"""
        <div style="
            width:220px; 
            background-color: {BG_SURFACE}; 
            color: {TEXT_PRIMARY}; 
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            padding: 8px;
            font-size: 11px;
        ">
            <h5 style="color: #D3436C; margin: 0 0 6px 0; font-size: 12px; font-weight:600;">⚗️ Hotspot: {h.hotspot_id}</h5>
            <div style="margin-bottom:4px;"><b>Latitude:</b> {h.latitude:.4f}</div>
            <div style="margin-bottom:4px;"><b>Longitude:</b> {h.longitude:.4f}</div>
            <div style="margin-bottom:4px;"><b>Column Density:</b> {h.column_density:.2f} ×10¹⁵ mol/cm²</div>
            <div style="margin-bottom:4px;"><b>Radius:</b> {h.radius_km} km</div>
            <div style="margin-bottom:4px;"><b>Source:</b> <span style="text-transform: capitalize; color:{PRIMARY}; font-weight:bold;">{h.source_type}</span></div>
            <div style="margin-bottom:4px;"><b>Confidence:</b> {h.confidence:.0%}</div>
            <div style="font-size:8px; color:{TEXT_SECONDARY}; margin-top:6px; border-top: 1px solid {BORDER_DEFAULT}; padding-top:4px;">
                Detected: {h.detected_at.strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=240)

        # Radius in folium.Circle expects METERS, so radius_km * 1000
        folium.Circle(
            location=[h.latitude, h.longitude],
            radius=h.radius_km * 1000,
            popup=popup,
            color="#D3436C",
            fill=True,
            fill_color="#D3436C",
            fill_opacity=0.3,
            weight=1.5,
            tooltip=f"{h.hotspot_id} — Density: {h.column_density}",
        ).add_to(hotspot_group)

    hotspot_group.add_to(m)
    if hotspots:
        bounds = [[h.latitude, h.longitude] for h in hotspots]
        m.fit_bounds(bounds, padding=(20, 20))

    # 2. Sentinel-5P HCHO Raster Overlay (Future Day 5 Expansion Point)
    hcho_raster = HCHORasterInterface()
    tile_url = hcho_raster.get_tile_url(datetime.utcnow())
    folium.raster_layers.TileLayer(
        tiles=tile_url,
        attr="Sentinel-5P TROPOMI HCHO Column Density",
        name="Sentinel-5P HCHO Raster (COG Overlay)",
        overlay=True,
        control=True,
        opacity=0.55,
        show=False,
    ).add_to(m)

    # 3. Dynamic HeatMap Layer (Placeholder)
    # Day 5 can fill this with a real folium.plugins.HeatMap from active density grid points
    if hotspots:
        plugins.HeatMap(
            data=[[h.latitude, h.longitude, h.column_density] for h in hotspots],
            name="HCHO Density Heatmap (Placeholder)",
            min_opacity=0.2,
            radius=25,
            blur=15,
            show=False,
        ).add_to(m)

    # Add Floating Legend for HCHO Column Density
    _add_hcho_legend_element(m)

    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    st_folium(m, height=450, use_container_width=True, key=key)


def _add_hcho_legend_element(m: folium.Map) -> None:
    legend_html = f"""
    <div style="
        position: fixed; 
        bottom: 20px; left: 20px; width: 150px; 
        background-color: rgba(22, 27, 34, 0.85);
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 8px;
        z-index:9999; font-size:11px;
        color: {TEXT_PRIMARY};
        padding: 10px;
        font-family: 'Inter', sans-serif;
    ">
        <div style="font-weight:600; margin-bottom:6px; color:#D3436C;">Column Density</div>
        <div style="font-size:10px; color:{TEXT_SECONDARY}; margin-bottom:6px;">(×10¹⁵ molecules/cm²)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#220050; width:10px; height:10px; display:inline-block; border-radius:20%; margin-right:8px;"></span>Low (0–5)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#781C6B; width:10px; height:10px; display:inline-block; border-radius:20%; margin-right:8px;"></span>Moderate (5–10)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#D3436C; width:10px; height:10px; display:inline-block; border-radius:20%; margin-right:8px;"></span>High (10–15)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#FBB07A; width:10px; height:10px; display:inline-block; border-radius:20%; margin-right:8px;"></span>Extreme (15+)</div>
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))


# ── Map 3: Fire Location Map ──────────────────────────────────────────────────

def render_fire_spatial_map(fires: list[Any], key: str = "fire_map") -> None:
    """
    Render active fire points colored by FRP intensity and sized proportionally.
    Includes popup cards detailing fire properties and future raster layers.
    """
    m = create_base_map(center=[22.0, 80.0], zoom=5)

    fire_group = folium.FeatureGroup(name="MODIS/VIIRS Active Fires", overlay=True, control=True)

    for f in fires:
        # Scaled radius: map FRP to a reasonable pixel radius range (e.g., 5 to 20 pixels)
        pixel_radius = min(max(f.frp / 15, 6), 22)

        # Scale color based on FRP severity
        if f.frp >= 200:
            color = "#B71C1C"  # Dark Red (Severe)
        elif f.frp >= 100:
            color = ACCENT_ORANGE
        elif f.frp >= 30:
            color = "#FFD600"  # Yellow
        else:
            color = PRIMARY     # Low intensity

        popup_html = f"""
        <div style="
            width:210px; 
            background-color: {BG_SURFACE}; 
            color: {TEXT_PRIMARY}; 
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            padding: 8px;
            font-size: 11px;
        ">
            <h5 style="color: {ACCENT_ORANGE}; margin: 0 0 6px 0; font-size: 12px; font-weight:600;">🔥 Event: {f.event_id}</h5>
            <div style="margin-bottom:4px;"><b>Location:</b> {f.district}, {f.state}</div>
            <div style="margin-bottom:4px;"><b>Power (FRP):</b> <span style="color:#FFD600; font-weight:bold;">{f.frp:.1f} MW</span></div>
            <div style="margin-bottom:4px;"><b>Temp (Brightness):</b> {f.brightness:.1f} K</div>
            <div style="margin-bottom:4px;"><b>Satellite:</b> {f.satellite}</div>
            <div style="margin-bottom:4px;"><b>Confidence:</b> <span style="text-transform: capitalize;">{f.confidence}</span></div>
            <div style="margin-bottom:4px;"><b>Land Cover:</b> <span style="text-transform: capitalize;">{f.land_cover}</span></div>
            <div style="font-size:8px; color:{TEXT_SECONDARY}; margin-top:6px; border-top: 1px solid {BORDER_DEFAULT}; padding-top:4px;">
                Detected: {f.detected_at.strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=230)

        folium.CircleMarker(
            location=[f.latitude, f.longitude],
            radius=pixel_radius,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1.5,
            tooltip=f"{f.satellite} Fire ({f.district}) — FRP: {f.frp:.1f} MW",
        ).add_to(fire_group)

    fire_group.add_to(m)
    if fires:
        bounds = [[f.latitude, f.longitude] for f in fires]
        m.fit_bounds(bounds, padding=(20, 20))

    # Satellite Fire Raster Overlay (Future Day 5 Expansion Point)
    fire_raster = FireRasterInterface()
    tile_url = fire_raster.get_tile_url(datetime.utcnow())
    folium.raster_layers.TileLayer(
        tiles=tile_url,
        attr="MODIS/VIIRS Active Fires Power Density",
        name="MODIS/VIIRS Fire Raster (COG Overlay)",
        overlay=True,
        control=True,
        opacity=0.6,
        show=False,
    ).add_to(m)

    # Floating Fire Intensity Legend
    _add_fire_legend_element(m)

    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    st_folium(m, height=450, use_container_width=True, key=key)


def _add_fire_legend_element(m: folium.Map) -> None:
    legend_html = f"""
    <div style="
        position: fixed; 
        bottom: 20px; left: 20px; width: 140px; 
        background-color: rgba(22, 27, 34, 0.85);
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 8px;
        z-index:9999; font-size:11px;
        color: {TEXT_PRIMARY};
        padding: 10px;
        font-family: 'Inter', sans-serif;
    ">
        <div style="font-weight:600; margin-bottom:6px; color:{ACCENT_ORANGE};">FRP Intensity</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#B71C1C; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Critical (200+)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{ACCENT_ORANGE}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>High (100–200)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:#FFD600; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Moderate (30–100)</div>
        <div style="display:flex; align-items:center; margin-bottom:3px;"><span style="background-color:{PRIMARY}; width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:8px;"></span>Low (0–30)</div>
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))


# ── Map 4: Forecast Coverage Map ─────────────────────────────────────────────

def render_forecast_coverage_map(readings: list[Any], key: str = "forecast_map") -> None:
    """
    Render a map showing monitoring stations colored by their FORECAST AQI category.
    Includes popup cards displaying current vs forecast parameters.
    """
    m = create_base_map(center=[22.8, 79.0], zoom=5)

    forecast_group = folium.FeatureGroup(name="Forecast Station Indicators", overlay=True, control=True)

    for r in readings:
        color = _get_cpcb_color(r.aqi_category)

        popup_html = f"""
        <div style="
            width:220px; 
            background-color: {BG_SURFACE}; 
            color: {TEXT_PRIMARY}; 
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            padding: 8px;
            font-size: 11px;
        ">
            <h5 style="color: {PRIMARY}; margin: 0 0 6px 0; font-size: 12px; font-weight:600;">🔮 Forecast: {r.station_name}</h5>
            <div style="margin-bottom:6px;">
                <b>Baseline AQI:</b> {r.aqi_value} ({r.aqi_category})
            </div>
            <div style="border-top:1px solid {BORDER_DEFAULT}; padding-top:6px; margin-bottom:6px;">
                <b>72h Predicted AQI:</b> <span style="color:{color}; font-weight:bold;">{int(r.aqi_value * 0.95)}</span>
            </div>
            <div style="font-size:9px; color:{TEXT_SECONDARY}; text-align:right;">
                Model: VAYU-DRISHTI XGBoost v1
            </div>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=240)

        folium.CircleMarker(
            location=[r.latitude, r.longitude],
            radius=8,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1.5,
            tooltip=f"{r.station_name} — Click for Forecast Summary",
        ).add_to(forecast_group)

    forecast_group.add_to(m)
    if readings:
        bounds = [[r.latitude, r.longitude] for r in readings]
        m.fit_bounds(bounds, padding=(20, 20))

    _add_aqi_legend_element(m)

    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    st_folium(m, height=450, use_container_width=True, key=key)
