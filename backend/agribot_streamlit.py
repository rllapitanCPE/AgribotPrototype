import streamlit as st
import pandas as pd
import joblib
import gspread
import numpy as np
import os
import io
import base64
import json
import requests
from PIL import Image as PILImage
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
from streamlit_autorefresh import st_autorefresh


# ============================================================
# NOTE: Gemini is NOT called from Streamlit.
# The Pi runs Gemini 2.5 Flash, writes:
#   ai_status  -> full per-plant Gemini block (one row per plant)
#   ai_summary -> ONE overall greenhouse summary on the P8 row
# Streamlit reads BOTH columns — zero Gemini quota used here.
# ============================================================
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    DRIVE_API_OK = True
except ImportError:
    DRIVE_API_OK = False


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH  = os.path.join(SCRIPT_DIR, "agribotailogo.png")
BG_PATH    = os.path.join(SCRIPT_DIR, "background.jpg")
PI_LOGO    = os.path.expanduser("~/env/Thesis code/backend/agribotailogo.png")
PI_BG      = os.path.expanduser("~/env/Thesis code/backend/background.jpg")
WIN_LOGO   = r"C:\Users\admin\Downloads\AgribotPrototype\backend\agribotailogo.png"
WIN_BG     = r"C:\Users\admin\Downloads\AgribotPrototype\backend\background.jpg"

LANDING_BG_PATH = os.path.join(SCRIPT_DIR, "landpage.png")
PI_LANDING_BG   = os.path.expanduser("~/env/Thesis code/backend/landpage.png")
WIN_LANDING_BG  = r"C:\Users\admin\Downloads\AgribotPrototype\backend\landpage.png"

ACTUAL_LOGO       = next((p for p in [LOGO_PATH, PI_LOGO, WIN_LOGO]                    if os.path.exists(p)), "")
ACTUAL_BG         = next((p for p in [BG_PATH,   PI_BG,   WIN_BG]                     if os.path.exists(p)), "")
ACTUAL_LANDING_BG = next((p for p in [LANDING_BG_PATH, PI_LANDING_BG, WIN_LANDING_BG] if os.path.exists(p)), "")

CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "..", "credentials.json")
if not os.path.exists(CREDENTIALS_FILE):
    CREDENTIALS_FILE = os.path.expanduser("~/env/Thesis code/credentials.json")

SPREADSHEET_ID   = "1mYScsUkoZn84FIoO_QMaku3gZT3Z9df72kPE3ray9-A"
DRIVE_FOLDER_ID  = "1g6Tg0UZSuFrJchPyRJLgcJmM_X4Ggatm"
DRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"
STREAMLIT_URL    = "https://agribotai.streamlit.app"

_page_icon = "🌱"
if ACTUAL_LOGO:
    try:
        _page_icon = PILImage.open(ACTUAL_LOGO)
    except Exception:
        pass

st.set_page_config(
    page_title="AgriBot-AI | Dashboard",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS SPLIT: BASE (always safe) + SIDEBAR (only when logged in)
# ============================================================

BASE_CSS = """
<style>
/* ══════════════════════════════════════════════
   CSS CUSTOM PROPERTIES  (dark = default)
   ══════════════════════════════════════════════ */
:root {
    --sidebar-w:      230px;

    /* Dark palette */
    --bg-app:          #0a0d12;
    --bg-sidebar:      #023f23;
    --bg-card:         rgba(13,17,23,0.9);
    --bg-metric:       #023f23;
    --bg-form:         linear-gradient(160deg, rgba(27,94,32,0.65) 0%, rgba(46,125,50,0.55) 100%);
    --bg-input:        rgba(255,255,255,0.1);
    --bg-btn-nav:      rgba(46,125,50,0.12);
    --bg-btn-hover:    rgba(76,175,80,0.12);
    --bg-sensor-sum:   rgba(46,125,50,0.08);
    --bg-alert-item:   rgba(183,28,28,0.10);
    --bg-rec-item:     rgba(46,125,50,0.10);
    --bg-ph-card:      #023f23;
    --bg-placeholder:  rgba(46,125,50,0.04);

    --border-card:     rgba(46,125,50,0.4);
    --border-metric:   rgba(76,175,80,0.3);
    --border-form:     rgba(165,214,167,0.35);
    --border-input:    rgba(165,214,167,0.45);
    --border-sidebar:  rgba(46,125,50,0.5);
    --border-placeholder: rgba(46,125,50,0.3);

    --txt-primary:     #ffffff;
    --txt-secondary:   #c8e6c9;
    --txt-accent:      #66bb6a;
    --txt-accent2:     #81c784;
    --txt-muted:       #888888;
    --txt-label:       #a5d6a7;
    --txt-finding:     #e8f5e9;
    --txt-alert:       #ef9a9a;
    --txt-warn:        #ffb74d;
    --txt-info:        #90CAF9;
    --txt-input:       #ffffff;
    --txt-placeholder: rgba(200,230,200,0.6);
    --txt-link:        #81c784;
    --txt-section-ttl: #66bb6a;

    --green-primary:   #4CAF50;
    --green-dark:      #2e7d32;
    --green-deep:      #1b5e20;

    /* Fluid type scale */
    --fs-page-title:  clamp(15px, 2vw, 21px);
    --fs-section-ttl: clamp(11px, 1.1vw, 13px);
    --fs-body:        clamp(14px, 1.4vw, 16px);
    --fs-body-small:  clamp(12px, 1.1vw, 14px);
    --fs-metric-val:  clamp(20px, 2.4vw, 26px);
    --fs-metric-lbl:  clamp(10px, 0.9vw, 12px);
    --fs-badge:       clamp(9px,  0.85vw, 11px);
    --fs-nav-btn:     clamp(13px, 1.3vw, 16px);
    --fs-card-hdr:    clamp(11px, 1.1vw, 13px);
    --fs-finding:     clamp(10px, 0.95vw, 11px);
    --fs-rec:         clamp(10px, 0.95vw, 11px);
    --touch-min:      44px;
}

/* ══════════════════════════════════════════════
   LIGHT THEME OVERRIDES
   ══════════════════════════════════════════════ */
body.agribot-light, .agribot-light {
    --bg-app:          #f4f7f0;
    --bg-sidebar:      #1b5e20;
    --bg-card:         #ffffff;
    --bg-metric:       #ffffff;
    --bg-form:         linear-gradient(160deg, #e8f5e9 0%, #c8e6c9 100%);
    --bg-input:        #ffffff;
    --bg-btn-nav:      rgba(27,94,32,0.08);
    --bg-btn-hover:    rgba(46,125,50,0.15);
    --bg-sensor-sum:   rgba(76,175,80,0.08);
    --bg-alert-item:   rgba(198,40,40,0.07);
    --bg-rec-item:     rgba(46,125,50,0.08);
    --bg-ph-card:      #ffffff;
    --bg-placeholder:  #f1f8e9;

    --border-card:     rgba(46,125,50,0.25);
    --border-metric:   rgba(46,125,50,0.3);
    --border-form:     rgba(46,125,50,0.4);
    --border-input:    rgba(46,125,50,0.5);
    --border-sidebar:  rgba(27,94,32,0.6);
    --border-placeholder: rgba(76,175,80,0.4);

    --txt-primary:     #0d1f0a;
    --txt-secondary:   #1b5e20;
    --txt-accent:      #2e7d32;
    --txt-accent2:     #388e3c;
    --txt-muted:       #555555;
    --txt-label:       #2e7d32;
    --txt-finding:     #1a2a17;
    --txt-alert:       #b71c1c;
    --txt-warn:        #e65100;
    --txt-info:        #0d47a1;
    --txt-input:       #0d1f0a;
    --txt-placeholder: rgba(30,80,30,0.5);
    --txt-link:        #2e7d32;
    --txt-section-ttl: #1b5e20;
}

/* ══════════════════════════════════════════════
   RESET
   ══════════════════════════════════════════════ */
html, body {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100% !important;
    width: 100% !important; font-size: var(--fs-body) !important;
}
.stApp {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100vh !important;
    width: 100vw !important; max-height: 100vh !important;
    background-color: var(--bg-app) !important;
    color: var(--txt-primary) !important;
}
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    overflow: hidden !important; padding: 0 !important;
    margin: 0 !important; height: 100vh !important;
}
.main, section.main > div {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100vh !important;
}
.main .block-container {
    padding: 0 !important; margin: 0 !important;
    max-width: 100% !important; width: 100% !important;
    overflow: hidden !important; height: 100vh !important;
    max-height: 100vh !important;
    display: flex; flex-direction: column; box-sizing: border-box;
}
.main .block-container > div:first-child { margin-top: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 5px !important; }
[data-testid="column"] { height: 100%; padding: 0 4px !important; }

/* Kill Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="collapsedControl"], .stDeployButton,
button[title="View App"], button[title="Manage app"],
button[kind="headerNoSpacing"], a[href*="streamlit.io"],
.viewerBadge_container__1QSob, .styles_viewerBadge__CvC9N,
#GithubIcon, .css-1dp5vir {
    display: none !important; visibility: hidden !important;
}

/* ══════════════════════════════════════════════
   METRICS
   ══════════════════════════════════════════════ */
div[data-testid="stMetric"] {
    background: var(--bg-metric) !important;
    border: 1px solid var(--border-metric) !important;
    border-radius: 10px !important;
    padding: 8px 6px !important; text-align: center !important;
}
div[data-testid="stMetricLabel"] {
    font-weight: 700 !important; font-size: var(--fs-metric-lbl) !important;
    color: var(--txt-accent) !important; letter-spacing: 1.2px !important;
    text-transform: uppercase !important; justify-content: center !important;
}
div[data-testid="stMetricValue"] {
    font-size: var(--fs-metric-val) !important;
    font-weight: 900 !important; color: var(--txt-primary) !important;
    margin-top: 1px !important;
}

/* Wrapping metric row (for small screens) */
.metric-responsive-row {
    display: flex; flex-wrap: wrap; gap: 6px; width: 100%; margin-bottom: 6px;
}
.metric-responsive-row > div { flex: 1 1 130px; min-width: 90px; }

/* pH custom metric */
.ph-metric-wrap {
    background: var(--bg-ph-card); border: 1px solid var(--border-metric);
    border-radius: 10px; padding: 8px 6px; text-align: center;
}
.ph-metric-label {
    font-weight: 700; font-size: var(--fs-metric-lbl);
    color: var(--txt-accent); letter-spacing: 1.2px; text-transform: uppercase;
}
.ph-metric-value {
    font-size: var(--fs-metric-val); font-weight: 900;
    color: var(--txt-primary); margin-top: 1px;
}

/* ══════════════════════════════════════════════
   CARDS & PANELS
   ══════════════════════════════════════════════ */
.cam-card {
    background: var(--bg-card); border: 1px solid var(--border-card);
    border-radius: 12px; padding: 10px; height: 100%;
}
.section-title {
    font-size: var(--fs-section-ttl) !important; font-weight: 700 !important;
    color: var(--txt-section-ttl) !important; letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    margin-bottom: 15px !important; margin-top: 0 !important;
    border-left: 3px solid var(--green-primary); padding-left: 7px;
}
.alert-item {
    padding: 8px 12px; background: rgba(183,28,28,0.12);
    border: 1px solid rgba(183,28,28,0.3); color: var(--txt-alert);
    border-radius: 8px; margin: 10px 0;
    font-size: var(--fs-body-small) !important;
    min-height: var(--touch-min); display: flex; align-items: center;
}
.sched-badge {
    display: inline-block; background: rgba(21,101,192,0.2);
    border: 1px solid rgba(21,101,192,0.5); border-radius: 5px;
    padding: 2px 8px; font-size: var(--fs-badge) !important;
    color: var(--txt-info); font-weight: 700; margin: 0 2px;
}
.cam-meta {
    font-size: var(--fs-body-small) !important;
    color: var(--txt-accent); margin-top: 15px; line-height: 1.5;
}
.drive-link {
    display: inline-flex; align-items: center; margin-top: 5px;
    background: var(--bg-btn-nav); border: 1px solid var(--border-metric);
    border-radius: 7px; padding: 6px 12px; color: var(--txt-link);
    font-size: var(--fs-body-small) !important; text-decoration: none;
    min-height: var(--touch-min);
}
.cam-placeholder {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 200px;
    background: var(--bg-placeholder);
    border: 2px dashed var(--border-placeholder);
    border-radius: 10px; text-align: center; padding: 20px;
}

/* ══════════════════════════════════════════════
   pH BADGES
   ══════════════════════════════════════════════ */
.ph-badge {
    display: inline-block; border-radius: 6px; padding: 2px 10px;
    font-size: var(--fs-badge) !important; font-weight: 700;
    letter-spacing: 1px; text-transform: uppercase;
    margin-left: 6px; vertical-align: middle;
}
.ph-acidic   { background: rgba(239,83,80,0.18);  border: 1px solid rgba(239,83,80,0.5);  color: #ef9a9a; }
.ph-neutral  { background: rgba(76,175,80,0.18);  border: 1px solid rgba(76,175,80,0.5);  color: #81c784; }
.ph-alkaline { background: rgba(66,165,245,0.18); border: 1px solid rgba(66,165,245,0.5); color: #90CAF9; }

/* ══════════════════════════════════════════════
   PLOTS & TABLES
   ══════════════════════════════════════════════ */
.js-plotly-plot, .plotly, .plot-container { max-height: 210px !important; }
[data-testid="stPlotlyChart"] { height: 210px !important; overflow: hidden !important; }
[data-testid="stDataFrame"] {
    max-height: 300px !important; overflow-y: auto !important;
    font-size: var(--fs-body-small) !important;
}

/* ══════════════════════════════════════════════
   INPUTS & SELECTS
   ══════════════════════════════════════════════ */
[data-testid="stAlert"] {
    padding: 10px 14px !important; font-size: var(--fs-body) !important;
    border-radius: 8px !important; margin: 4px 0 !important;
}
[data-testid="stSelectbox"] { margin-bottom: 4px !important; }
[data-baseweb="select"] {
    min-height: var(--touch-min) !important; font-size: var(--fs-body) !important;
}
.stSelectbox label {
    font-size: var(--fs-body-small) !important;
    color: var(--txt-accent) !important; margin-bottom: 2px !important;
}
.stTextInput label {
    color: var(--txt-secondary) !important; font-weight: 600 !important;
    font-size: var(--fs-body) !important;
}
.stTextInput input {
    font-size: var(--fs-body) !important;
    min-height: var(--touch-min) !important;
}

/* ══════════════════════════════════════════════
   LANDING & LOGIN
   ══════════════════════════════════════════════ */
.landing-btn-wrapper button {
    background: linear-gradient(135deg, #2e7d32, #66bb6a) !important;
    border: 2px solid rgba(255,255,255,0.3) !important;
    border-radius: 50px !important; color: white !important;
    font-size: clamp(18px, 2.5vw, 24px) !important; font-weight: 700 !important;
    padding: 14px 48px !important; cursor: pointer !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    min-height: 64px !important; min-width: 200px !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}
.landing-btn-wrapper button:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 12px 32px rgba(76,175,80,0.7) !important;
}
.landing-page section[data-testid="stSidebar"] { display: none !important; }

[data-testid="stForm"] {
    background: var(--bg-form) !important;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 18px; border: 1px solid var(--border-form);
    box-shadow: 0 12px 40px rgba(0,0,0,0.35);
    padding: 26px 36px 34px !important;
}
[data-testid="stForm"] input {
    background: var(--bg-input) !important; color: var(--txt-input) !important;
    border: 1px solid var(--border-input) !important; border-radius: 10px !important;
    font-size: var(--fs-body) !important; min-height: var(--touch-min) !important;
}
[data-testid="stForm"] input::placeholder { color: var(--txt-placeholder) !important; }
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(90deg, #2e7d32, #66bb6a) !important;
    border: none !important; color: #fff !important; font-weight: 700 !important;
    border-radius: 10px !important; letter-spacing: 1.5px;
    font-size: var(--fs-body) !important; padding: 12px !important;
    min-height: var(--touch-min) !important; margin-top: 4px !important;
}

/* ══════════════════════════════════════════════
   IMAGES
   ══════════════════════════════════════════════ */
[data-testid="stImage"] { margin: 0 !important; }
[data-testid="stImage"] img {
    border-radius: 8px !important; max-height: 260px !important;
    object-fit: cover !important; width: 100% !important;
}

/* ══════════════════════════════════════════════
   AI SUMMARY CARD
   ══════════════════════════════════════════════ */
.gh-summary-card {
    border-radius: 11px; padding: 14px 16px; margin: 4px 0 8px;
    font-size: var(--fs-finding); line-height: 1.8;
    overflow-x: hidden; word-break: break-word;
}
.gh-summary-healthy  { background: rgba(46,125,50,0.18);  border: 1px solid #81c784; }
.gh-summary-warning  { background: rgba(230,81,0,0.18);   border: 1px solid #ffb74d; }
.gh-summary-critical { background: rgba(183,28,28,0.18);  border: 1px solid #ef9a9a; }
.gh-summary-pending  { background: rgba(33,33,33,0.35);   border: 1px solid #555; }
.gh-summary-unknown  { background: rgba(21,101,192,0.12); border: 1px solid #90CAF9; }

.gh-finding-row {
    display: flex; gap: 6px; align-items: baseline;
    font-size: var(--fs-finding); margin: 2px 0; padding: 2px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.gh-finding-label {
    color: var(--txt-label); font-weight: 700; min-width: 110px;
    letter-spacing: 0.3px; text-transform: uppercase;
    font-size: var(--fs-badge);
}
.gh-finding-value  { color: var(--txt-finding); flex: 1; }
.gh-finding-high   { color: var(--txt-alert) !important; }
.gh-finding-low    { color: var(--txt-warn)  !important; }
.gh-finding-normal { color: var(--txt-accent2) !important; }

/* ══════════════════════════════════════════════
   TALLY PILLS
   ══════════════════════════════════════════════ */
.tally-pill {
    display: inline-block; border-radius: 20px; padding: 3px 12px;
    font-size: var(--fs-badge); font-weight: 700; margin: 0 3px;
    letter-spacing: 0.5px; min-height: 24px; line-height: 1.8;
}
.tally-healthy  { background: rgba(46,125,50,0.3);  border: 1px solid #81c784; color: #81c784; }
.tally-warning  { background: rgba(230,81,0,0.3);   border: 1px solid #ffb74d; color: #ffb74d; }
.tally-critical { background: rgba(183,28,28,0.3);  border: 1px solid #ef9a9a; color: #ef9a9a; }

/* ══════════════════════════════════════════════
   SMS BADGES
   ══════════════════════════════════════════════ */
.sms-sent-badge {
    display: inline-block; background: rgba(21,101,192,0.25);
    border: 1px solid #90CAF9; border-radius: 4px;
    padding: 2px 8px; font-size: var(--fs-badge); color: #90CAF9;
    font-weight: 700; margin-left: 6px; vertical-align: middle;
}
.sms-no-badge {
    display: inline-block; background: rgba(66,66,66,0.25);
    border: 1px solid #888; border-radius: 4px;
    padding: 2px 8px; font-size: var(--fs-badge); color: var(--txt-muted);
    font-weight: 700; margin-left: 6px; vertical-align: middle;
}

/* ══════════════════════════════════════════════
   SENSOR SUMMARY / ALERTS / RECS
   ══════════════════════════════════════════════ */
.gh-sensor-summary {
    font-size: var(--fs-finding); color: var(--txt-secondary); line-height: 1.7;
    background: var(--bg-sensor-sum); border-radius: 6px;
    padding: 6px 8px; margin-bottom: 8px;
    border-left: 3px solid rgba(76,175,80,0.4);
}
.gh-alert-item {
    padding: 5px 10px; margin: 3px 0;
    background: var(--bg-alert-item);
    border-left: 3px solid var(--txt-alert);
    border-radius: 0 6px 6px 0;
    font-size: var(--fs-finding); color: var(--txt-alert); line-height: 1.5;
}
.gh-alert-none {
    font-size: var(--fs-finding); color: var(--txt-accent2);
    font-style: italic; padding: 2px 0;
}
.gh-rec-item {
    padding: 3px 0; font-size: var(--fs-rec); color: var(--txt-finding);
    line-height: 1.6; border-bottom: 1px solid rgba(255,255,255,0.04);
    display: flex; gap: 6px; align-items: flex-start;
}
.gh-rec-bullet { color: #4CAF50; font-weight: 900; flex-shrink: 0; margin-top: 1px; }

/* ══════════════════════════════════════════════
   MOBILE TOP-NAV BAR (≤800px only)
   ══════════════════════════════════════════════ */
.mobile-nav-bar {
    display: none;
    background: #023f23;
    padding: 7px 12px;
    border-bottom: 1px solid rgba(76,175,80,0.3);
    align-items: center;
    justify-content: space-between;
    width: 100%; box-sizing: border-box;
    position: sticky; top: 0; z-index: 100;
}
.mobile-nav-title  { font-size: 16px; font-weight: 900; color: #fff; }
.mobile-nav-status { font-size: 12px; color: #81c784; }

/* ══════════════════════════════════════════════
   LIGHT MODE SOLID OVERRIDES
   ══════════════════════════════════════════════ */
.agribot-light .stApp,
.agribot-light [data-testid="stAppViewContainer"],
.agribot-light [data-testid="stAppViewBlockContainer"],
.agribot-light .main .block-container {
    background-color: #f4f7f0 !important;
    color: #0d1f0a !important;
}
.agribot-light .stApp::before { display: none !important; }
.agribot-light div[data-testid="stMetric"] {
    background: #ffffff !important;
    border-color: rgba(46,125,50,0.3) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.10);
}
.agribot-light div[data-testid="stMetricLabel"] { color: #2e7d32 !important; }
.agribot-light div[data-testid="stMetricValue"] { color: #0d1f0a !important; }
.agribot-light .ph-metric-wrap   { background: #ffffff !important; }
.agribot-light .ph-metric-label  { color: #2e7d32 !important; }
.agribot-light .ph-metric-value  { color: #0d1f0a !important; }
.agribot-light .section-title    { color: #1b5e20 !important; }
.agribot-light .gh-sensor-summary { color: #1b5e20 !important; }
.agribot-light .gh-finding-row { border-bottom-color: rgba(0,0,0,0.05) !important; }
.agribot-light .gh-finding-label { color: #2e7d32 !important; }
.agribot-light .gh-finding-value { color: #1a2a17 !important; }
.agribot-light .gh-rec-item { color: #1a2a17 !important; border-bottom-color: rgba(0,0,0,0.04) !important; }
.agribot-light .gh-alert-item { color: #b71c1c !important; background: rgba(198,40,40,0.06) !important; border-left-color: #b71c1c !important; }
.agribot-light .gh-alert-none { color: #1b5e20 !important; }
.agribot-light .gh-summary-healthy  { background: rgba(200,230,201,0.5) !important; border-color: #388e3c !important; }
.agribot-light .gh-summary-warning  { background: rgba(255,224,178,0.5) !important; border-color: #e65100 !important; }
.agribot-light .gh-summary-critical { background: rgba(255,205,210,0.5) !important; border-color: #b71c1c !important; }
.agribot-light .gh-summary-pending  { background: rgba(240,240,240,0.8) !important; border-color: #bbb !important; }
.agribot-light .gh-summary-unknown  { background: rgba(187,222,251,0.4) !important; border-color: #0d47a1 !important; }
.agribot-light .tally-healthy { color: #1b5e20 !important; }
.agribot-light .tally-warning { color: #e65100 !important; }
.agribot-light .tally-critical { color: #b71c1c !important; }
.agribot-light .ph-acidic   { color: #b71c1c !important; }
.agribot-light .ph-neutral  { color: #1b5e20 !important; }
.agribot-light .ph-alkaline { color: #0d47a1 !important; }
.agribot-light .cam-meta  { color: #2e7d32 !important; }
.agribot-light .drive-link { color: #2e7d32 !important; background: rgba(46,125,50,0.08) !important; }
/* Sidebar stays dark even in light mode */
.agribot-light section[data-testid="stSidebar"] { background: #1b5e20 !important; }

/* ══════════════════════════════════════════════
   MEDIA QUERIES
   ══════════════════════════════════════════════ */

/* ── ≤ 1024px : small laptop / tablet landscape ── */
@media screen and (max-width: 1024px) {
    :root {
        --sidebar-w:      200px;
        --fs-body:        clamp(13px, 1.5vw, 15px);
        --fs-metric-val:  clamp(18px, 2vw, 22px);
    }
    [data-testid="stImage"] img { max-height: 220px !important; }
}

/* ── ≤ 800px : 7-inch LCD / tablet portrait ──────── */
@media screen and (max-width: 800px) {
    :root {
        --sidebar-w:      0px;
        --fs-body:        16px;
        --fs-body-small:  14px;
        --fs-metric-val:  22px;
        --fs-metric-lbl:  12px;
        --fs-nav-btn:     15px;
        --fs-section-ttl: 13px;
        --fs-card-hdr:    13px;
        --fs-badge:       12px;
        --fs-finding:     13px;
        --fs-rec:         13px;
        --touch-min:      48px;
    }

    /* Hide sidebar — show mobile nav bar instead */
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="stAppViewContainer"] { margin-left: 0 !important; }

    /* Stack columns */
    [data-testid="column"] {
        flex: 0 0 100% !important;
        max-width: 100% !important;
        width: 100% !important;
    }

    /* 2 × 2 metrics */
    .metric-responsive-row > div { flex: 1 1 calc(50% - 6px); }

    /* AI summary must never scroll horizontally */
    .gh-summary-card  { overflow-x: hidden; }

    /* Taller select/inputs for touch */
    [data-baseweb="select"] { min-height: 48px !important; }

    /* Charts fill width nicely */
    .js-plotly-plot, .plotly, .plot-container { max-height: 240px !important; }
    [data-testid="stPlotlyChart"] { height: 240px !important; }

    /* Allow vertical scroll on the main pane */
    .main .block-container,
    [data-testid="stAppViewContainer"],
    .stApp { overflow-y: auto !important; }

    /* Show mobile nav */
    .mobile-nav-bar { display: flex !important; }

    [data-testid="stImage"] img { max-height: 200px !important; }
}

/* ── ≤ 480px : very compact / vertical orientation ── */
@media screen and (max-width: 480px) {
    :root {
        --fs-body:        15px;
        --fs-body-small:  13px;
        --fs-metric-val:  20px;
        --touch-min:      52px;
    }

    /* 1-column metric stacking on very small screens */
    .metric-responsive-row > div { flex: 1 1 100%; }

    [data-testid="stImage"] img { max-height: 170px !important; }
}

/* ══════════════════════════════════════════════
   ANIMATION
   ══════════════════════════════════════════════ */
@keyframes pulse {
    0%,100% { box-shadow: 0 0 5px #4CAF50; }
    50%      { box-shadow: 0 0 14px #4CAF50; opacity: 0.7; }
}
</style>
"""

# ── Sidebar‑specific CSS (only for logged‑in pages) ──────────────────────────
SIDEBAR_CSS = """
<style>
/* Sidebar fixed width and positioning */
section[data-testid="stSidebar"] {
    width: var(--sidebar-w) !important;
    min-width: var(--sidebar-w) !important;
    max-width: var(--sidebar-w) !important;
    position: fixed !important; left: 0 !important;
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-sidebar) !important;
    overflow: hidden !important; height: 100vh !important;
    padding-top: 0 !important; transition: none !important;
    animation: none !important; transform: none !important;
    z-index: 999;
}
[data-testid="stAppViewContainer"] {
    margin-left: var(--sidebar-w) !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    display: flex !important; flex-direction: column !important;
    align-items: center !important; padding: 0 4px 4px !important;
}
[data-testid="stSidebar"] [data-testid="stElementToolbar"] { display: none !important; }
[data-testid="stSidebarResizer"],
section[data-testid="stSidebar"] > div:last-child { display: none !important; }
section[data-testid="stSidebar"] > div:first-child > div:first-child {
    display: none !important; height: 0 !important;
}
[data-testid="collapsedControl"],
button[title="Collapse sidebar"],
button[aria-label="Collapse sidebar"] {
    display: none !important; opacity: 0 !important;
    pointer-events: none !important; width: 0 !important; height: 0 !important;
}

/* Nav radio inside sidebar */
.stRadio > div {
    gap: 20px !important; width: 100% !important;
    flex-direction: column !important; margin-bottom: 8px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: var(--fs-nav-btn) !important; font-weight: 700 !important;
    color: #ffffff !important; letter-spacing: 0.8px !important;
    text-transform: uppercase !important; background: var(--bg-btn-nav) !important;
    border: none !important; border-radius: 8px !important;
    padding: 6px 8px !important; width: 100% !important;
    cursor: pointer !important; transition: all 0.2s !important;
    min-height: var(--touch-min) !important;
    display: flex !important; align-items: center !important;
    margin-top: -15px !important;
}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--bg-btn-hover) !important; color: #ffffff !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"]
label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(46,125,50,0.22) !important;
    border-left: 3px solid #4CAF50 !important;
    color: #ffffff !important; padding-left: 9px !important;
}
section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    margin: 0 !important; color: #ffffff !important;
    font-size: var(--fs-nav-btn) !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    font-size: var(--fs-nav-btn) !important; font-weight: 700 !important;
    color: #ffffff !important; letter-spacing: 0.8px !important;
    text-transform: uppercase !important; background: var(--bg-btn-nav) !important;
    border: none !important; border-radius: 8px !important;
    padding: 6px 8px !important; width: 100% !important;
    min-height: var(--touch-min) !important;
    transition: all 0.2s !important; margin-top: 8px !important;
    cursor: pointer !important; display: flex !important;
    align-items: center !important; justify-content: center !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(198,40,40,0.15) !important;
}

/* Sidebar toggle (light/dark) */
[data-testid="stSidebar"] .stToggle {
    width: 100%; margin: 4px 0;
}
[data-testid="stSidebar"] .stToggle label {
    color: #ffffff !important;
    font-size: var(--fs-nav-btn) !important;
    font-weight: 600 !important;
    min-height: var(--touch-min) !important;
    display: flex !important; align-items: center !important;
}
[data-testid="stSidebar"] .stToggle [role="switch"] {
    min-width: 44px !important; min-height: 28px !important;
}
</style>
"""

# Inject base CSS (always safe)
st.markdown(BASE_CSS, unsafe_allow_html=True)

# ── Theme injection (runs every render) ────────────────────────────────────────
_is_light = st.session_state.get("light_mode", False)
_theme_js = "agribot-light" if _is_light else ""
st.markdown(
    f"""<script>
    (function() {{
        var app = window.parent.document.querySelector(".stApp");
        if (app) {{
            app.classList.remove("agribot-light");
            if ("{_theme_js}") app.classList.add("{_theme_js}");
        }}
    }})();
    </script>""",
    unsafe_allow_html=True,
)
if _is_light:
    st.markdown("""<style>
    .stApp,[data-testid="stAppViewContainer"],[data-testid="stAppViewBlockContainer"],
    .main,.main .block-container{background-color:#f4f7f0!important;color:#0d1f0a!important;}
    .stApp::before{display:none!important;}
    </style>""", unsafe_allow_html=True)

# ============================================================
# HELPERS  (unchanged from original)
# ============================================================
def file_to_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def ph_label(ph_val: float) -> tuple:
    if ph_val < 5.5:   return "Acidic",   "ph-acidic"
    elif ph_val <= 7.0: return "Neutral",  "ph-neutral"
    else:               return "Alkaline", "ph-alkaline"

def gdrive_direct_url(url: str) -> str:
    if not url: return ""
    try:
        fid = None
        if "id=" in url:
            fid = url.split("id=")[1].split("&")[0].strip()
        elif "/file/d/" in url:
            fid = url.split("/file/d/")[1].split("/")[0].strip()
        if fid:
            return f"https://drive.google.com/uc?export=view&id={fid}"
    except Exception:
        pass
    return url

def fetch_drive_image(url: str):
    if not url: return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 1000:
            return PILImage.open(io.BytesIO(resp.content))
        return None
    except Exception:
        return None

def set_background(path: str):
    b64 = file_to_b64(path)
    if not b64: return
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    # In light mode, skip the dark overlay
    overlay = "rgba(0,0,0,0.52)" if not st.session_state.get("light_mode") else "rgba(255,255,255,0.15)"
    st.markdown(f"""<style>
    .stApp {{
        background-image: url("data:{mime};base64,{b64}");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }}
    .stApp::before {{
        content: ""; position: fixed; inset: 0;
        background: {overlay}; z-index: 0; pointer-events: none;
    }}
    </style>""", unsafe_allow_html=True)

def safe_read_sheet(sheet_obj) -> pd.DataFrame:
    try:
        data = sheet_obj.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame()
        raw_headers = data[0]
        seen = {}; headers = []
        for h in raw_headers:
            h = h.strip()
            if h in seen:
                seen[h] += 1; headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0; headers.append(h)
        df = pd.DataFrame(data[1:], columns=headers)
        expected = ['timestamp','plant_id','temp_c','humidity',
                    'soil_moisture','ph','image_url','ai_status','ai_summary']
        df = df[[c for c in expected if c in df.columns]]
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        for col in ['temp_c','humidity','soil_moisture','ph']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'plant_id' in df.columns:
            df['plant_id'] = pd.to_numeric(df['plant_id'], errors='coerce')
        df = df.dropna(subset=['timestamp','plant_id'])
        return df
    except Exception as e:
        st.error(f"Sheet read error: {e}")
        return pd.DataFrame()


# ============================================================
# DRIVE IMAGE HELPERS  (unchanged)
# ============================================================
def _get_drive_service_private():
    if not DRIVE_API_OK: return None
    scope = ["https://www.googleapis.com/auth/drive.readonly"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                dict(st.secrets["gcp_service_account"]), scope)
        elif os.path.exists(CREDENTIALS_FILE):
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                CREDENTIALS_FILE, scope)
        else:
            return None
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"[Drive Private] Service build error: {e}"); return None

def _get_file_id_from_url(url: str) -> str:
    if not url: return ""
    if "id=" in url:        return url.split("id=")[1].split("&")[0].strip()
    if "/file/d/" in url:   return url.split("/file/d/")[1].split("/")[0].strip()
    return ""

def fetch_drive_image_private(file_id: str):
    if not file_id or not DRIVE_API_OK: return None
    try:
        svc = _get_drive_service_private()
        if not svc: return None
        request = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl  = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        return PILImage.open(buf)
    except Exception as e:
        print(f"[Drive Private] Download error: {e}"); return None


# ============================================================
# PARSERS  (unchanged)
# ============================================================
def parse_ai_status(ai_status_str: str) -> dict:
    if not ai_status_str or str(ai_status_str).strip() in ("", "nan", "N/A"):
        return {}
    s = str(ai_status_str).strip()
    if s == "Wait for Batch...":
        return {"__pending__": True}
    def _find(pattern, default="N/A"):
        m = re.search(pattern, s, re.IGNORECASE)
        return m.group(1).strip() if m else default
    status_m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
    status   = status_m.group(1).strip().capitalize() if status_m else "Unknown"
    disease_raw  = _find(r'Disease\s*:\s*(.+)')
    disease_name = disease_raw.split('--')[0].strip() if disease_raw != 'N/A' else 'N/A'
    disease_is_healthy = (
        'healthy' in disease_name.lower() or
        'no visible' in disease_name.lower() or
        disease_name == 'N/A'
    )
    rec_m = re.search(r'Recommendation:\s*\n([\s\S]+?)(?=\nSMS Sent:|\Z)', s)
    rec   = rec_m.group(1).strip() if rec_m else _find(r'Recommendation:\s*(.+)', 'N/A')
    rec   = re.sub(r'\n\s+', ' ', rec)
    sms_sent = _find(r'SMS Sent:\s*(Yes|No)', 'No')
    return {
        'status':             status,
        'finding_image':      _find(r'Image\s*:\s*(.+)'),
        'disease_raw':        disease_raw,
        'disease_name':       disease_name,
        'disease_is_healthy': disease_is_healthy,
        'finding_soil':       _find(r'Soil Moisture\s*:\s*(.+)'),
        'finding_temp':       _find(r'Temperature\s*:\s*(.+)'),
        'finding_humidity':   _find(r'Humidity\s*:\s*(.+)'),
        'finding_ph':         _find(r'pH Level\s*:\s*(.+)'),
        'recommendation':     rec,
        'sms_sent':           sms_sent,
    }

def parse_ai_summary(ai_summary_str: str) -> dict:
    if not ai_summary_str or str(ai_summary_str).strip() in ("", "nan", "N/A"):
        return {}
    s = str(ai_summary_str).strip()
    if s == "Wait for Batch...":
        return {"__pending__": True}
    if "OVERALL GREENHOUSE STATUS:" in s:
        result = {"__new_format__": True}
        def _find_new(pattern, default=""):
            m = re.search(pattern, s, re.IGNORECASE)
            return m.group(1).strip() if m else default
        result['status_label'] = _find_new(r'OVERALL GREENHOUSE STATUS:\s*\n?(.+)', "Unknown")
        sl = result['status_label'].lower()
        if 'high' in sl:       result['status'] = 'Critical'
        elif 'moderate' in sl: result['status'] = 'Warning'
        elif 'healthy' in sl:  result['status'] = 'Healthy'
        else:                  result['status'] = 'Unknown'
        sens_m = re.search(r'SENSOR SUMMARY:\s*\n([\s\S]+?)(?=\nALERT LIST:|\Z)', s, re.IGNORECASE)
        result['sensor_summary'] = sens_m.group(1).strip() if sens_m else ""
        alert_m = re.search(r'ALERT LIST:\s*\n([\s\S]+?)(?=\nRECOMMENDATIONS:|\Z)', s, re.IGNORECASE)
        if alert_m:
            raw_alerts = alert_m.group(1).strip()
            result['alert_list'] = [] if raw_alerts.lower() == 'none' else [
                ln.lstrip('- ').strip()
                for ln in raw_alerts.splitlines()
                if ln.strip() and ln.strip().lower() != 'none'
            ]
        else:
            result['alert_list'] = []
        rec_m = re.search(r'RECOMMENDATIONS:\s*\n([\s\S]+?)(?=\nSMS ALERT:|\Z)', s, re.IGNORECASE)
        result['recommendations'] = [
            ln.lstrip('- ').strip() for ln in rec_m.group(1).splitlines() if ln.strip()
        ] if rec_m else []
        sms_m = re.search(r'SMS ALERT:\s*\n?(.+)', s, re.IGNORECASE)
        result['sms_line'] = sms_m.group(1).strip() if sms_m else ""
        return result
    # Old format fallback
    def _find(pattern, default="N/A"):
        m = re.search(pattern, s, re.IGNORECASE)
        return m.group(1).strip() if m else default
    result = {}
    result['status']           = _find(r'Status:\s*(Healthy|Warning|Critical|Unknown)', "Unknown")
    result['finding_image']    = _find(r'\*\s*Image\s*:\s*(.+)')
    result['finding_disease']  = _find(r'\*\s*Disease\s*:\s*(.+)', "None detected")
    result['finding_soil']     = _find(r'\*\s*Soil Moisture\s*:\s*(.+)')
    result['finding_temp']     = _find(r'\*\s*Temperature\s*:\s*(.+)')
    result['finding_humidity'] = _find(r'\*\s*Humidity\s*:\s*(.+)')
    result['finding_ph']       = _find(r'\*\s*pH Level\s*:\s*(.+)')
    result['critical_plants']  = _find(r'Critical Plants:\s*(.+)', "")
    result['warning_plants']   = _find(r'Warning Plants\s*:\s*(.+)', "")
    rec_m = re.search(r'Recommendation:\s*\n([\s\S]+?)(?=\n\nSMS:|\nSMS:|\Z)', s)
    if rec_m:
        raw_rec = rec_m.group(1).strip()
        per_plant_lines = re.findall(r'(P\d+\s*\(\w+\)\s*:.+)', raw_rec)
        if per_plant_lines:
            result['per_plant_recs'] = per_plant_lines
            result['recommendation'] = "\n".join(per_plant_lines)
        else:
            result['per_plant_recs'] = []
            result['recommendation'] = " ".join(ln.lstrip() for ln in raw_rec.splitlines() if ln.strip())
    else:
        result['per_plant_recs'] = []
        result['recommendation'] = _find(r'Recommendation:\s*(.+)', "N/A")
    result['sms_line'] = _find(r'SMS:\s*(.+)', "")
    return result

def _finding_class(value_str: str) -> str:
    v = value_str.lower()
    if v.startswith("high"):   return "gh-finding-high"
    if v.startswith("low"):    return "gh-finding-low"
    if v.startswith("normal"): return "gh-finding-normal"
    return ""


# ============================================================
# DATA FRESHNESS
# ============================================================
def get_data_freshness(all_df: pd.DataFrame) -> tuple:
    if all_df.empty or 'timestamp' not in all_df.columns:
        return ("No data", "#888")
    try:
        latest_ts = pd.to_datetime(all_df['timestamp']).max()
        diff_secs = max((datetime.now() - latest_ts).total_seconds(), 0)
        if diff_secs < 90:
            return (f"{int(diff_secs)}s ago", "#81c784")
        elif diff_secs < 3600:
            return (f"{int(diff_secs // 60)}m ago", "#81c784")
        elif diff_secs < 7200:
            return (f"{int(diff_secs // 3600)}h ago", "#ffb74d")
        else:
            return (f"{int(diff_secs // 3600)}h ago — check Pi", "#ef9a9a")
    except Exception:
        return ("Unknown", "#888")


# ============================================================
# GREENHOUSE SUMMARY PANEL (UPDATED - Now displays per-plant details)
# ============================================================
def render_greenhouse_summary_panel(df: pd.DataFrame):
    if df.empty or 'ai_summary' not in df.columns:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 No AI summary yet — add the <b>ai_summary</b> column to your Google Sheet '
            'and run the next camera session.</div>', unsafe_allow_html=True)
        return
    summary_df = df[
        df['ai_summary'].astype(str).str.strip().replace('nan', '') != ''
    ].copy()
    if summary_df.empty:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 Greenhouse summary not available yet.<br><br>'
            'The Pi writes a summary after each camera session '
            '(<span class="sched-badge">7:00 AM</span>'
            '<span class="sched-badge">12:00 NN</span>'
            '<span class="sched-badge">5:00 PM</span>).</div>', unsafe_allow_html=True)
        return
    latest_row  = summary_df.sort_values('timestamp').iloc[-1]
    raw_summary = str(latest_row['ai_summary']).strip()
    ts          = pd.to_datetime(latest_row['timestamp']).strftime("%b %d, %Y · %I:%M %p")
    parsed      = parse_ai_summary(raw_summary)
    if not parsed:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 No AI summary yet — waiting for next camera session.</div>',
            unsafe_allow_html=True)
        return
    if parsed.get("__pending__"):
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🔄 AI analyzing batch... greenhouse summary will appear shortly.</div>',
            unsafe_allow_html=True)
        return
    status = parsed.get('status', 'Unknown')
    color_map = {
        "Healthy":  ("#81c784", "gh-summary-healthy",  "✅"),
        "Warning":  ("#ffb74d", "gh-summary-warning",  "⚠️"),
        "Critical": ("#ef9a9a", "gh-summary-critical", "🔴"),
        "Unknown":  ("#90CAF9", "gh-summary-unknown",  "ℹ️"),
    }
    txt_c, css_cls, icon = color_map.get(status, ("#90CAF9", "gh-summary-unknown", "ℹ️"))

    if parsed.get('__new_format__'):
        status_label = parsed.get('status_label', status)
        sensor_sum   = parsed.get('sensor_summary', '')
        alert_list   = parsed.get('alert_list', [])
        recs         = parsed.get('recommendations', [])
        sms_line     = parsed.get('sms_line', '')
        sensor_html  = f'<div class="gh-sensor-summary">{sensor_sum}</div>' if sensor_sum else ""
        alerts_html  = "".join(f'<div class="gh-alert-item">⚡ {i}</div>' for i in alert_list) if alert_list else '<div class="gh-alert-none">✅ No plants require immediate attention.</div>'
        recs_html    = "".join(f'<div class="gh-rec-item"><span class="gh-rec-bullet">▸</span><span>{r}</span></div>' for r in recs) if recs else '<div style="font-size:var(--fs-finding);color:#888;">No recommendations.</div>'
        sms_html     = (f'<div style="margin-top:8px;padding:6px 8px;background:rgba(21,101,192,0.12);border:1px solid rgba(144,202,249,0.3);border-radius:6px;font-size:var(--fs-badge);color:#90CAF9;"><span style="font-weight:700;letter-spacing:0.5px;">📨 SMS ALERT: </span>{sms_line}</div>' if sms_line else "")
        st.markdown(
            f'<div class="gh-summary-card {css_cls}">'
            f'<div style="font-weight:900;color:{txt_c};font-size:var(--fs-card-hdr);margin-bottom:6px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">'
            f'{icon} Overall Status: <b>{status_label}</b>'
            f'<span style="font-size:var(--fs-badge);color:#888;font-weight:400;margin-left:6px;">{ts}</span></div>'
            f'<div style="margin-bottom:6px;"><div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-label);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">SENSOR SUMMARY</div>{sensor_html}</div>'
            f'<div style="margin-bottom:6px;"><div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-alert);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">ALERT LIST</div>{alerts_html}</div>'
            f'<div style="padding-top:6px;border-top:1px solid rgba(255,255,255,0.07);"><div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-accent);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">RECOMMENDATIONS</div>{recs_html}</div>'
            f'{sms_html}</div>', unsafe_allow_html=True)
        
        # ── Display per-plant AI status details ──
        st.markdown('<div style="margin-top:12px;"><div class="section-title">🌿 Individual Plant Analysis</div></div>', unsafe_allow_html=True)
        plant_details_found = False
        if not df.empty and 'ai_status' in df.columns:
            for plant_id in sorted(df['plant_id'].unique()):
                if pd.isna(plant_id) or plant_id <= 0:
                    continue
                plant_df = df[
                    (df['plant_id'] == plant_id) &
                    (df['ai_status'].astype(str).str.strip()
                        .replace('nan','').replace('Wait for Batch...','') != '')
                ].copy()
                if not plant_df.empty:
                    plant_details_found = True
                    row = plant_df.sort_values('timestamp').iloc[-1]
                    p_parsed = parse_ai_status(str(row['ai_status']))
                    if p_parsed and not p_parsed.get('__pending__'):
                        p_status = p_parsed.get('status', 'Unknown')
                        p_color_map = {
                            "Healthy":  ("#81c784", "✅"),
                            "Warning":  ("#ffb74d", "⚠️"),
                            "Critical": ("#ef9a9a", "🔴"),
                            "Unknown":  ("#90CAF9", "ℹ️"),
                        }
                        p_txt_c, p_icon = p_color_map.get(p_status, ("#90CAF9", "ℹ️"))
                        disease_name       = p_parsed.get('disease_name', 'N/A')
                        disease_is_healthy = p_parsed.get('disease_is_healthy', True)
                        disease_badge_cls  = "disease-healthy" if disease_is_healthy else "disease-detected"
                        disease_label      = "No Disease" if disease_is_healthy else disease_name
                        
                        # Build plant findings
                        plant_findings = [
                            ("Soil Moisture", p_parsed.get('finding_soil', 'N/A')),
                            ("Temperature", p_parsed.get('finding_temp', 'N/A')),
                            ("Humidity", p_parsed.get('finding_humidity', 'N/A')),
                            ("pH Level", p_parsed.get('finding_ph', 'N/A')),
                        ]
                        findings_html = ""
                        for lbl, val in plant_findings:
                            findings_html += (
                                f'<div class="gh-finding-row">'
                                f'<span class="gh-finding-label" style="min-width:80px;">{lbl}</span>'
                                f'<span class="gh-finding-value {_finding_class(val)}">{val}</span>'
                                f'</div>'
                            )
                        
                        rec = p_parsed.get('recommendation', 'N/A')
                        sms_sent = p_parsed.get('sms_sent', 'No')
                        sms_badge = (
                            '<span class="sms-sent-badge">📨 SMS SENT</span>'
                            if sms_sent == 'Yes' else
                            '<span class="sms-no-badge">SMS: No</span>'
                        )
                        st.markdown(
                            f'<div class="gh-summary-card" style="margin-top:8px;background:rgba(13,17,23,0.6);border-left:4px solid {p_txt_c};">'
                            f'<div style="font-weight:700;color:{p_txt_c};font-size:var(--fs-card-hdr);margin-bottom:6px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
                            f'{p_icon} Plant {int(plant_id)} — {p_status}'
                            f'<span class="disease-badge {disease_badge_cls}">🦠 {disease_label}</span>'
                            f'{sms_badge}</div>'
                            f'{findings_html}'
                            f'<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.06);padding-top:6px;">'
                            f'<div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-accent);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:2px;">Recommendation</div>'
                            f'<div class="plant-rec-block">▸ {rec}</div></div>'
                            f'</div>',
                            unsafe_allow_html=True)
        
        if not plant_details_found:
            st.markdown(
                '<div style="font-size:var(--fs-finding);color:#888;margin-top:8px;">'
                '🕒 Per-plant AI analysis pending — waiting for camera session.</div>',
                unsafe_allow_html=True)
        return

    # Old format
    crit_pids  = parsed.get('critical_plants', '').strip()
    warn_pids  = parsed.get('warning_plants',  '').strip()
    tally_html = ""
    if crit_pids: tally_html += f'<span class="tally-pill tally-critical">🔴 Critical: {crit_pids}</span> '
    if warn_pids: tally_html += f'<span class="tally-pill tally-warning">⚠️ Warning: {warn_pids}</span>'
    if not tally_html and status == "Healthy":
        tally_html = '<span class="tally-pill tally-healthy">✅ All plants healthy</span>'
    disease_val   = parsed.get('finding_disease', 'None detected')
    disease_is_ok = ('none detected' in disease_val.lower() or disease_val == 'N/A')
    disease_cls   = 'disease-healthy' if disease_is_ok else 'disease-detected'
    disease_icon  = '✅' if disease_is_ok else '🦠'
    findings = [
        ("Image",         parsed.get('finding_image',    'N/A')),
        ("Disease",       disease_val),
        ("Soil Moisture", parsed.get('finding_soil',     'N/A')),
        ("Temperature",   parsed.get('finding_temp',     'N/A')),
        ("Humidity",      parsed.get('finding_humidity', 'N/A')),
        ("pH Level",      parsed.get('finding_ph',       'N/A')),
    ]
    findings_html = ""
    for lbl, val in findings:
        if lbl == "Disease":
            findings_html += f'<div class="gh-finding-row"><span class="gh-finding-label">Disease</span><span class="gh-finding-value"><span class="disease-badge {disease_cls}">{disease_icon} {val}</span></span></div>'
        else:
            findings_html += f'<div class="gh-finding-row"><span class="gh-finding-label">{lbl}</span><span class="gh-finding-value {_finding_class(val)}">{val}</span></div>'
    per_plant_recs = parsed.get('per_plant_recs', [])
    if per_plant_recs:
        recs_html = "".join(f'<div class="gh-rec-item"><span class="gh-rec-bullet">▸</span><span>{ln}</span></div>' for ln in per_plant_recs)
    else:
        rec = parsed.get('recommendation', 'N/A')
        recs_html = (f'<div class="gh-rec-item"><span class="gh-rec-bullet">▸</span><span>{rec}</span></div>' if rec and rec != 'N/A' else '<div style="font-size:var(--fs-finding);color:#888;">No recommendations.</div>')
    sms_line = parsed.get('sms_line', '')
    sms_html = (f'<div style="margin-top:8px;padding:6px 8px;background:rgba(21,101,192,0.12);border:1px solid rgba(144,202,249,0.3);border-radius:6px;font-size:var(--fs-badge);color:#90CAF9;"><span style="font-weight:700;letter-spacing:0.5px;">📨 SMS ALERT: </span>{sms_line}</div>' if sms_line else "")
    st.markdown(
        f'<div class="gh-summary-card {css_cls}">'
        f'<div style="font-weight:900;color:{txt_c};font-size:var(--fs-card-hdr);margin-bottom:6px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">'
        f'{icon} Overall Status: <b>{status}</b><span style="font-size:var(--fs-badge);color:#888;font-weight:400;margin-left:6px;">{ts}</span></div>'
        f'<div style="margin-bottom:8px;">{tally_html}</div>'
        f'<div style="margin-bottom:8px;"><div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-label);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:4px;">FINDINGS (Greenhouse Average)</div>{findings_html}</div>'
        f'<div style="padding-top:6px;border-top:1px solid rgba(255,255,255,0.07);"><div style="font-size:var(--fs-badge);font-weight:700;color:var(--txt-accent);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">RECOMMENDATION</div>{recs_html}</div>'
        f'{sms_html}</div>', unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role      = None
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "light_mode" not in st.session_state:
    st.session_state.light_mode = False

USERS = {
    "admin@agribot.ai": {"password": "admin123", "role": "admin"},
    "user@agribot.ai":  {"password": "user123",  "role": "user"},
}


# ============================================================
# PAGE: LANDING
# ============================================================
def show_landing():
    if ACTUAL_LANDING_BG:
        set_background(ACTUAL_LANDING_BG)
    else:
        st.markdown("<style>.stApp { background: #0a0d12 !important; }</style>",
                    unsafe_allow_html=True)
    st.markdown("""<style>
    section[data-testid="stSidebar"] { display: none !important; }
    .stApp::before { display: none !important; }
    </style>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 9])
    with col2:
        st.markdown("<div style='margin-top: 30vh;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="landing-btn-wrapper">', unsafe_allow_html=True)
        if st.button("Let's Start", use_container_width=True, key="landing_btn"):
            st.session_state.page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ============================================================
# PAGE: LOGIN
# ============================================================
def show_login():
    set_background(ACTUAL_BG)
    st.markdown("""<style>
    section[data-testid="stSidebar"] { display: none !important; }
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden !important; height: 100vh !important;
        position: fixed; width: 100vw;
    }
    header { visibility: hidden; }
    .main .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
    ::-webkit-scrollbar { display: none; }
    </style>""", unsafe_allow_html=True)
    logo_b64  = file_to_b64(ACTUAL_LOGO)
    logo_html = (
        f'<div style="display:flex;justify-content:center;margin-bottom:16px;">'
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="width:clamp(70px,10vw,100px);height:clamp(70px,10vw,100px);'
        f'border-radius:50%;border:3px solid #4CAF50;object-fit:cover;'
        f'box-shadow:0 0 28px rgba(76,175,80,0.5);"/></div>'
    ) if logo_b64 else ""
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;margin-top:-90px;">'
        f'{logo_html}'
        f'<div style="text-align:center;font-size:clamp(24px,3.5vw,34px);font-weight:900;color:#fff;'
        f'letter-spacing:1px;text-shadow:0 2px 12px rgba(0,0,0,0.6);margin-bottom:4px;">'
        f'AgriBot-AI</div>'
        f'<div style="text-align:center;color:#81c784;font-size:clamp(10px,1.2vw,12px);'
        f'letter-spacing:3px;text-transform:uppercase;margin-bottom:20px;">'
        f'Smart Farming &middot; Intelligent Monitoring</div>'
        f'</div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        with st.form("login_form"):
            email    = st.text_input("Email",    placeholder="admin@agribot.ai")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            if st.form_submit_button("LOGIN", use_container_width=True):
                if email in USERS and USERS[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.role      = USERS[email]["role"]
                    st.session_state.page      = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid email or password")
        if st.button("← Back to Landing", use_container_width=True, key="back_btn"):
            st.session_state.page = "landing"
            st.rerun()
    st.stop()


# ============================================================
# ROUTING
# ============================================================
if st.session_state.page == "landing":
    show_landing()
if st.session_state.page == "login":
    show_login()
if not st.session_state.logged_in and st.session_state.page == "dashboard":
    st.session_state.page = "login"
    st.rerun()

# ============================================================
# CONDITIONAL SIDEBAR CSS INJECTION (only when logged in)
# ============================================================
if st.session_state.logged_in:
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

# ============================================================
# DATA FUNCTIONS  (unchanged)
# ============================================================
@st.cache_resource
def load_assets():
    try:
        model  = joblib.load(os.path.join(SCRIPT_DIR, 'anomaly_model.pkl'))
        scaler = joblib.load(os.path.join(SCRIPT_DIR, 'anomaly_scaler.pkl'))
        return model, scaler
    except Exception:
        return None, None

@st.cache_resource
def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                dict(st.secrets["gcp_service_account"]), scope)
        elif os.path.exists(CREDENTIALS_FILE):
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                CREDENTIALS_FILE, scope)
        else:
            st.error("credentials.json not found.")
            return None
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

@st.cache_data(ttl=30)
def get_latest_readings():
    if sheet is None: return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty: return df
    df = df[df['plant_id'] > 0]
    return df.sort_values('timestamp').groupby('plant_id').last().reset_index()

@st.cache_data(ttl=60)
def get_historical_data(plant_id=None, hours=24):
    if sheet is None: return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty: return df
    df = df[df['plant_id'] > 0]
    df = df[df['timestamp'] >= datetime.now() - timedelta(hours=hours)]
    if plant_id is not None:
        df = df[df['plant_id'] == plant_id]
    return df.sort_values('timestamp')

@st.cache_data(ttl=30)
def get_latest_plant_image() -> dict:
    if sheet is None: return {}
    df = safe_read_sheet(sheet)
    if df.empty or 'image_url' not in df.columns: return {}
    df = df[df['plant_id'] > 0]
    df_img = df[df['image_url'].astype(str).str.contains("id=", na=False)]
    if df_img.empty: return {}
    row   = df_img.sort_values('timestamp', ascending=False).iloc[0]
    plant = int(row['plant_id'])
    return {
        "url":       gdrive_direct_url(str(row['image_url']).strip()),
        "plant_id":  plant,
        "timestamp": pd.to_datetime(row['timestamp']).strftime("%b %d, %Y · %I:%M %p"),
    }


# ============================================================
# SIDEBAR
# ============================================================
sheet    = get_sheet()
logo_b64 = file_to_b64(ACTUAL_LOGO)

with st.sidebar:
    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;'
        f'padding-top:8px;width:100%;">'
        f'<div style="padding:2px;border-radius:50%;'
        f'background:linear-gradient(145deg,#388e3c,#1b5e20);'
        f'box-shadow:0 0 12px rgba(76,175,80,0.3);margin-bottom:2px;">'
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="border-radius:50%;width:90px;height:90px;'
        f'display:block;object-fit:cover;background:#0a0d12;"/></div>'
        f'<div style="font-size:18px;font-weight:900;color:#ffffff;'
        f'letter-spacing:0.5px;margin-bottom:3px;">AgriBot-AI</div>'
        f'<div style="font-size:12px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;padding:1px 8px;border-radius:20px;'
        f'background:rgba(46,125,50,0.15);border:1px solid rgba(76,175,80,0.25);'
        f'color:#ffffff;margin-bottom:7px;">'
        f'{"👑 Admin" if st.session_state.role == "admin" else "🌿 Field User"}'
        f'</div>'
        f'<div style="font-size:14px;font-weight:700;color:#ffffff;'
        f'letter-spacing:2px;text-transform:uppercase;width:100%;'
        f'text-align:center;padding:0 2px;margin-bottom:2px;">Navigation</div>',
        unsafe_allow_html=True)

    # ── Light / Dark mode toggle ─────────────────────────────
    light_on = st.toggle(
        "☀️ Light Mode",
        value=st.session_state.get("light_mode", False),
        key="theme_toggle",
        help="High-contrast light theme for bright environments (WCAG AA)",
    )
    if light_on != st.session_state.get("light_mode", False):
        st.session_state.light_mode = light_on
        st.rerun()
    st.markdown(
        '<div style="border-top:1px solid rgba(76,175,80,0.25);margin:4px 0 8px;"></div>',
        unsafe_allow_html=True)

    nav_opts = (
        ["Live Dashboard", "Analysis", "System Logs", "Users"]
        if st.session_state.role == "admin"
        else ["Live Dashboard", "Analysis"]
    )
    raw_page = st.radio("", nav_opts, label_visibility="hidden", key="nav_radio")
    page_map = {
        "Live Dashboard": "DASHBOARD",
        "Analysis":       "ANALYSIS",
        "System Logs":    "LOGS",
        "Users":          "USERS",
    }
    page = page_map.get(raw_page, "DASHBOARD")

    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role      = None
        st.session_state.page      = "landing"
        st.rerun()

    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# SHARED DATA + THRESHOLDS
# ============================================================
model, scaler = load_assets()
latest        = get_latest_readings()

PH_LOW,   PH_HIGH   = 5.5, 7.0
SOIL_DRY, SOIL_WET  = 30,  85
TEMP_LOW, TEMP_HIGH = 15,  35
HUM_LOW,  HUM_HIGH  = 50,  90

st_autorefresh(interval=30000, key="autorefresh")


# ============================================================
# PAGE: LIVE DASHBOARD (SIMPLIFIED - No Plant Detail or Status Grid)
# ============================================================
if page == "DASHBOARD":
    # ── Mobile-only nav bar (CSS hides it on desktop) ─────────
    all_df_top = safe_read_sheet(sheet) if sheet else pd.DataFrame()
    fresh_label_top, fresh_color_top = get_data_freshness(all_df_top)
    st.markdown(
        f'<div class="mobile-nav-bar">'
        f'<span class="mobile-nav-title">🌱 AgriBot-AI</span>'
        f'<span class="mobile-nav-status" style="color:{fresh_color_top};">'
        f'🔄 {fresh_label_top}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Desktop page heading ──────────────────────────────────
    st.markdown(
        '<div style="padding:6px 12px 2px;">'
        f'<div style="font-size:var(--fs-page-title);font-weight:900;color:var(--txt-primary);line-height:1.2;">'
        'Real-Time Monitoring</div>'
        f'<div style="font-size:var(--fs-page-title);color:var(--txt-accent);letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        'Greenhouse Overview — AgriBot-AI</div>'
        '</div>', unsafe_allow_html=True)

    if latest.empty:
        st.warning("No sensor data yet — waiting for the Pi...")
        st.stop()

    avg_temp = float(latest['temp_c'].mean())
    avg_hum  = float(latest['humidity'].mean())
    avg_ph   = float(latest['ph'].mean())
    avg_soil = float(latest['soil_moisture'].mean())

    # ── Four metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TEMP",     f"{avg_temp:.1f} °C")
    m2.metric("HUMIDITY", f"{avg_hum:.0f} %")
    ph_lbl, ph_cls = ph_label(avg_ph)
    with m3:
        st.markdown(
            f'<div class="ph-metric-wrap">'
            f'<div class="ph-metric-label">PH</div>'
            f'<div class="ph-metric-value">'
            f'{avg_ph:.2f}<span class="ph-badge {ph_cls}">{ph_lbl}</span>'
            f'</div></div>', unsafe_allow_html=True)
    m4.metric("SOIL", f"{avg_soil:.0f} %")

    img_data = get_latest_plant_image()
    all_df   = safe_read_sheet(sheet) if sheet else pd.DataFrame()

    # ── Single column layout: Plant Health Feed + Greenhouse Summary ──
    st.markdown('<div style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-title">📷 Plant Health Feed</div>',
        unsafe_allow_html=True)

    if img_data.get("url"):
        file_id = _get_file_id_from_url(img_data["url"])
        pil_img = fetch_drive_image_private(file_id) if file_id else None
        if pil_img is None:
            pil_img = fetch_drive_image(img_data["url"])
        if pil_img:
            st.image(pil_img, use_container_width=True)
        else:
            st.markdown(
                '<div class="cam-placeholder">'
                '<div style="font-size:28px;">⚠️</div>'
                '<div style="font-size:var(--fs-body-small);color:var(--txt-alert);margin-top:6px;">'
                'Image could not be loaded.<br>'
                'Check Drive sharing permissions or credentials.json.</div>'
                '</div>', unsafe_allow_html=True)
        pid_txt = f"🥬 Plant {img_data['plant_id']}" if img_data.get("plant_id") else ""
        ts_txt  = f"🕒 {img_data['timestamp']}"       if img_data.get("timestamp") else ""
        st.markdown(
            f'<div class="cam-meta">{pid_txt}&nbsp;&nbsp;{ts_txt}<br>'
            f'Captured at '
            f'<span class="sched-badge">7:00 AM</span>'
            f'<span class="sched-badge">12:00 NN</span>'
            f'<span class="sched-badge">5:00 PM</span></div>'
            f'<a href="{DRIVE_FOLDER_URL}" target="_blank" class="drive-link">'
            f'☁️ View all in Drive ↗</a>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="cam-placeholder">'
            '<div style="font-size:36px;margin-bottom:8px;">📷</div>'
            '<div style="font-size:var(--fs-body-small);font-weight:700;color:#4CAF50;">No image yet</div>'
            '<div style="font-size:var(--fs-body-small);color:#2e7d32;margin-top:100px;">'
            'Captures at '
            '<span class="sched-badge">7:00 AM</span>'
            '<span class="sched-badge">12:00 NN</span>'
            '<span class="sched-badge">5:00 PM</span></div>'
            '</div>', unsafe_allow_html=True)

    # ── AI Greenhouse Summary (now includes per-plant details) ──
    fresh_label, fresh_color = get_data_freshness(all_df)
    last_ai_ts = ""
    if not all_df.empty and 'ai_summary' in all_df.columns:
        ai_rows = all_df[
            all_df['ai_summary'].astype(str).str.strip().replace('nan', '') != ''
        ]
        if not ai_rows.empty:
            last_ai_ts = pd.to_datetime(
                ai_rows['timestamp']).max().strftime("%b %d · %I:%M %p")

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:6px;margin-top:12px;">'
        f'<span style="font-size:var(--fs-badge);color:{fresh_color};">'
        f'🔄 Sensors: <b>{fresh_label}</b></span>'
        + (f'<span style="font-size:var(--fs-badge);color:var(--txt-muted);">Last AI: {last_ai_ts}</span>' if last_ai_ts else '') +
        f'</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="section-title">🤖 AI Greenhouse Summary & Plant Details</div>',
                unsafe_allow_html=True)
    render_greenhouse_summary_panel(all_df)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# PAGE: ANALYSIS (unchanged)
# ============================================================
elif page == "ANALYSIS":
    st.markdown(
        f'<div style="padding:6px 12px 4px;">'
        f'<div style="font-size:var(--fs-page-title);font-weight:900;color:var(--txt-primary);">Historical Trends</div>'
        f'<div style="font-size:var(--fs-page-title);color:var(--txt-accent);letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        f'Sensor data over time</div></div>', unsafe_allow_html=True)

    if latest.empty:
        st.warning("No data available yet.")
        st.stop()

    sc1, sc2 = st.columns([1, 1])
    with sc1:
        sensor_choice = st.selectbox("Sensor", [
            "Temperature (°C)", "Humidity (%)", "pH", "Soil Moisture (%)"])
    with sc2:
        time_range = st.selectbox("Range", ["24 hours", "7 days", "30 days"])
        hours = {"24 hours": 24, "7 days": 168, "30 days": 720}[time_range]

    col_map = {
        "Temperature (°C)": ("temp_c",        "°C"),
        "Humidity (%)":     ("humidity",       "%"),
        "pH":               ("ph",             "pH"),
        "Soil Moisture (%)":("soil_moisture",  "%"),
    }
    y_col, y_label = col_map[sensor_choice]
    _chart_bg = "#f4f7f0" if st.session_state.get("light_mode") else "rgba(13,17,23,0.85)"
    _font_c   = "#1b5e20" if st.session_state.get("light_mode") else "#a5d6a7"

    if sensor_choice == "Soil Moisture (%)":
        plant_sel = st.selectbox(
            "Select Plant", list(range(1, 9)),
            format_func=lambda x: f"Plant {x}")
        hist_df = get_historical_data(plant_id=plant_sel, hours=hours)
        chart_title = f"Soil Moisture — Plant {plant_sel}"
        if not hist_df.empty:
            fig = px.line(hist_df, x='timestamp', y=y_col, title=chart_title)
            fig.update_layout(
                height=210, margin=dict(t=32, b=20, l=30, r=10),
                yaxis_title=y_label,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor=_chart_bg,
                font_color=_font_c,
                title_font_color=('#0d1f0a' if st.session_state.get("light_mode") else '#fff'),
                title_font_size=12,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data for this plant in the selected time range.")

        st.markdown('<div class="section-title">🌱 All Plants — Current Soil Moisture</div>',
                    unsafe_allow_html=True)
        soil_rows = []
        for _, row in latest.iterrows():
            soil_rows.append({
                "Plant":  f"P{int(row['plant_id'])}",
                "Soil %": float(row['soil_moisture']),
                "Status": "Dry" if float(row['soil_moisture']) < SOIL_DRY
                          else ("Wet" if float(row['soil_moisture']) > SOIL_WET else "OK")
            })
        soil_df = pd.DataFrame(soil_rows)
        bar = px.bar(
            soil_df, x='Plant', y='Soil %',
            color='Soil %', color_continuous_scale='Greens',
            text='Soil %')
        bar.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        bar.update_layout(
            height=200, margin=dict(t=10, b=20, l=30, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor=_chart_bg,
            font_color=_font_c, coloraxis_showscale=False,
        )
        st.plotly_chart(bar, use_container_width=True)

    else:
        hist_df = get_historical_data(plant_id=None, hours=hours)
        chart_title = f"{sensor_choice} — Greenhouse Overall"
        if not hist_df.empty:
            overall = (
                hist_df.groupby('timestamp')[y_col]
                .mean().reset_index().sort_values('timestamp')
            )
            fig = px.line(overall, x='timestamp', y=y_col, title=chart_title)
            if sensor_choice == "pH":
                fig.add_hline(y=5.5, line_dash="dot", line_color="#ef9a9a",
                              annotation_text="Low threshold (5.5)",
                              annotation_position="bottom right",
                              annotation_font_color="#ef9a9a")
                fig.add_hline(y=7.0, line_dash="dot", line_color="#90CAF9",
                              annotation_text="High threshold (7.0)",
                              annotation_position="top right",
                              annotation_font_color="#90CAF9")
                fig.add_hrect(y0=5.5, y1=7.0, fillcolor="rgba(76,175,80,0.07)",
                              line_width=0, annotation_text="Optimal zone",
                              annotation_font_color="#66bb6a")
            fig.update_layout(
                height=210, margin=dict(t=32, b=20, l=30, r=10),
                yaxis_title=y_label,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor=_chart_bg,
                font_color=_font_c,
                title_font_color=('#0d1f0a' if st.session_state.get("light_mode") else '#fff'),
                title_font_size=12,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data in the selected time range.")


# ============================================================
# PAGE: SYSTEM LOGS (unchanged)
# ============================================================
elif page == "LOGS":
    st.markdown(
        f'<div style="padding:6px 12px 4px;">'
        f'<div style="font-size:var(--fs-page-title);font-weight:900;color:var(--txt-primary);">System Logs</div>'
        f'<div style="font-size:var(--fs-page-title);color:var(--txt-accent);letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        f'Last 24 hours</div></div>', unsafe_allow_html=True)

    logs = get_historical_data(plant_id=None, hours=24)
    if not logs.empty:
        def extract_status_only(ai_str):
            if not ai_str or str(ai_str).strip() in ("", "nan", "N/A"): return ""
            s = str(ai_str).strip()
            if s == "Wait for Batch...": return "⏳ Pending"
            if "Quota Limit Reached" in s: return "⏭ Quota Skipped"
            status_m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
            if not status_m: return s[:40]
            status = status_m.group(1).capitalize()
            icons  = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴", "Unknown": "ℹ️"}
            label  = f"{icons.get(status, '')} {status}"
            disease_m = re.search(r'Disease\s*:\s*(.+)', s, re.IGNORECASE)
            if disease_m:
                disease_raw  = disease_m.group(1).strip()
                disease_name = disease_raw.split('--')[0].strip()
                if ('healthy' not in disease_name.lower()
                        and 'no visible' not in disease_name.lower()
                        and disease_name != 'N/A'):
                    label += f" | 🦠 {disease_name}"
            return label

        def extract_summary_flag(ai_summary_str):
            if not ai_summary_str or str(ai_summary_str).strip() in ("", "nan"): return ""
            s = str(ai_summary_str).strip()
            new_m = re.search(r'OVERALL GREENHOUSE STATUS:\s*\n?(.+)', s, re.IGNORECASE)
            if new_m:
                label = new_m.group(1).strip(); sl = label.lower()
                if 'high' in sl:     return "🏡 🔴 High Risk"
                if 'moderate' in sl: return "🏡 ⚠️ Moderate Risk"
                if 'healthy' in sl:  return "🏡 ✅ Healthy"
                return f"🏡 {label}"
            m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
            if m:
                status = m.group(1).capitalize()
                icons  = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴", "Unknown": "ℹ️"}
                return f"🏡 {icons.get(status,'')} {status}"
            return "🏡 Summary"

        logs['ai_result']    = logs['ai_status'].apply(extract_status_only) if 'ai_status' in logs.columns else ""
        logs['summary_flag'] = logs['ai_summary'].apply(extract_summary_flag) if 'ai_summary' in logs.columns else ""

        display_cols = ['timestamp','plant_id','temp_c','humidity','soil_moisture','ph','ai_result','summary_flag']
        if 'image_url' in logs.columns:
            display_cols.insert(-2, 'image_url')

        cfg = {
            "timestamp":     st.column_config.TextColumn("Time"),
            "plant_id":      st.column_config.NumberColumn("Plant"),
            "temp_c":        st.column_config.NumberColumn("Temp (°C)"),
            "humidity":      st.column_config.NumberColumn("Hum (%)"),
            "soil_moisture": st.column_config.NumberColumn("Soil %"),
            "ph":            st.column_config.NumberColumn("pH"),
            "ai_result":     st.column_config.TextColumn("🤖 AI Status", width="small"),
            "summary_flag":  st.column_config.TextColumn("🏡 Overall",   width="small"),
            "image_url":     st.column_config.LinkColumn("📸 Image"),
        }
        display_cols = [c for c in display_cols if c in logs.columns]
        st.dataframe(
            logs[display_cols].sort_values('timestamp', ascending=False),
            column_config=cfg,
            use_container_width=True,
            hide_index=True)
    else:
        st.info("No logs available for the last 24 hours.")


# ============================================================
# PAGE: USER MANAGEMENT (unchanged)
# ============================================================
elif page == "USERS":
    st.markdown(
        f'<div style="padding:6px 12px 4px;">'
        f'<div style="font-size:var(--fs-page-title);font-weight:900;color:var(--txt-primary);">Admin Panel</div>'
        f'<div style="font-size:var(--fs-page-title);color:var(--txt-accent);letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        f'Registered accounts</div></div>', unsafe_allow_html=True)
    st.table(pd.DataFrame({
        "Username": ["admin@agribot.ai", "user@agribot.ai"],
        "Role":     ["Administrator",    "Standard User"]
    }))
    st.info("Future feature: add / remove users via database.")