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
#   ai_summary -> ONE overall greenhouse summary written on the
#                 last plant row (P8) after every camera session
# Streamlit reads both columns — zero Gemini quota used here.
#
# SUMMARY PANEL (UPDATED):
#   Now reads the Pi's new structured output:
#     OVERALL STATUS: <Healthy / Moderate Risk / High Risk>
#     SENSOR SUMMARY: <text>
#     DISEASE ALERTS: - P<ID>: <issue> ...
#     RECOMMENDATIONS: - <step> ...
#   Backward-compatible with the old format.
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

ACTUAL_LOGO       = next((p for p in [LOGO_PATH, PI_LOGO, WIN_LOGO]           if os.path.exists(p)), "")
ACTUAL_BG         = next((p for p in [BG_PATH,   PI_BG,   WIN_BG]             if os.path.exists(p)), "")
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

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                  MASTER STYLESHEET — AgriBot-AI                     ║
# ║                                                                      ║
# ║  HOW TO EDIT THIS CSS:                                               ║
# ║  • Fonts / colors / sizes  →  edit SECTION 1 · DESIGN TOKENS only   ║
# ║  • Sidebar width           →  change --sidebar-w in SECTION 1        ║
# ║  • Metric card values      →  change --fs-value in SECTION 1         ║
# ║  • A specific component    →  find its SECTION comment below         ║
# ║  • Fix mobile layout       →  scroll to SECTION 8 · MOBILE           ║
# ║  • Fix desktop layout      →  scroll to SECTION 9 · DESKTOP          ║
# ║                                                                      ║
# ║  DISPLAY TARGETS:                                                    ║
# ║  • BASE (sections 1-7)  →  7-inch IPS 1024×600 (Raspberry Pi)       ║
# ║  • SECTION 8            →  Mobile phones  (< 768 px wide)            ║
# ║  • SECTION 9            →  Desktop / laptop  (≥ 1025 px wide)        ║
# ╚══════════════════════════════════════════════════════════════════════╝
OPTIMIZED_CSS = """
<style>

/* ══════════════════════════════════════════════════════════════════════
   SECTION 1 · DESIGN TOKENS
   ► EDIT THIS BLOCK to restyle the entire app in one place.
   ► All variables here are referenced by the component styles below.
   ► CSS var( ) references update everywhere when you change them here.
══════════════════════════════════════════════════════════════════════ */
:root {

  /* ── BRAND / ACCENT COLORS ──────────────────────────────────────── */
  --c-brand:        #4CAF50;              /* main green accent          */
  --c-brand-dark:   #2e7d32;              /* darker green               */
  --c-brand-mid:    #388e3c;              /* mid green (logo ring)      */
  --c-brand-light:  #81c784;              /* light green text           */
  --c-brand-xlight: #a5d6a7;             /* very light green labels    */

  /* ── STATUS / HEALTH COLORS ─────────────────────────────────────── */
  /* Chosen for WCAG-AA contrast on both dark and light backgrounds.   */
  --c-healthy:   #4CAF50;   /* ✅ green  — healthy status              */
  --c-warning:   #F57C00;   /* ⚠️ amber  — moderate risk  (AA-safe)   */
  --c-critical:  #D32F2F;   /* 🔴 red    — high risk      (AA-safe)   */
  --c-info:      #1565C0;   /* ℹ️  blue  — informational  (AA-safe)   */

  /* Lighter variants used for backgrounds / pills on dark screens     */
  --c-healthy-light:   #81c784;
  --c-warning-light:   #ffb74d;
  --c-critical-light:  #ef9a9a;
  --c-info-light:      #90CAF9;

  /* ── FONT FAMILY ────────────────────────────────────────────────── */
  --ff: 'Segoe UI', system-ui, -apple-system, sans-serif;

  /* ── FONT SIZES  ◄ CHANGE THESE TO SCALE TEXT ───────────────────── */
  --fs-xs:     10px;   /* tiny: timestamps, badge text                 */
  --fs-sm:     11px;   /* small: metadata, cam captions                */
  --fs-base:   13px;   /* body / default paragraph text                */
  --fs-md:     14px;   /* slightly larger body (form text, tables)     */
  --fs-nav:    16px;   /* sidebar navigation labels                    */
  --fs-label:  11px;   /* metric card LABEL row (TEMP, HUM, etc.)      */
  --fs-value:  24px;   /* metric card VALUE row (the big number)       */
  --fs-sub:    16px;   /* page sub-heading (e.g. "Real-Time Monitor")  */
  --fs-title:  28px;   /* page main title (e.g. "Greenhouse Overview") */

  /* ── FONT WEIGHTS ───────────────────────────────────────────────── */
  --fw-normal: 400;
  --fw-semi:   600;
  --fw-bold:   700;
  --fw-black:  900;

  /* ── SPACING ────────────────────────────────────────────────────── */
  --sp-xs:  4px;
  --sp-sm:  8px;
  --sp-md: 12px;
  --sp-lg: 20px;

  /* ── BORDER RADIUS ──────────────────────────────────────────────── */
  --r-sm:  6px;
  --r-md: 10px;
  --r-lg: 18px;

  /* ── SIDEBAR ────────────────────────────────────────────────────── */
  --sidebar-w: 230px;    /* change this + the margin-left injection below */

  /* ── CHART & IMAGE HEIGHTS ──────────────────────────────────────── */
  --chart-h:  210px;   /* Plotly chart max-height                      */
  --img-h:    260px;   /* Health-feed image max-height                 */

  /* ── COMPONENT BACKGROUND ALPHA ─────────────────────────────────── */
  --alpha-low:  0.08;
  --alpha-mid:  0.18;
  --alpha-high: 0.35;
}


/* ══════════════════════════════════════════════════════════════════════
   SECTION 2 · BASE RESET & LAYOUT
   ► Removes Streamlit default padding, locks app to viewport.
   ► Tuned for 7-inch 1024×600 display. Do not touch unless
     you know what you're doing — responsive overrides are in
     SECTION 8 (mobile) and SECTION 9 (desktop) at the bottom.
══════════════════════════════════════════════════════════════════════ */
:root {
    --page-margin-top: 0px;
    --page-margin-bottom: 0px;
    --page-margin-left: 0px;
    --page-margin-right: 0px;
    --login-margin-top: -20px;
}
html, body {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100% !important;
    width: 100% !important; font-size: var(--fs-base) !important;
    font-family: var(--ff) !important;
}
.stApp {
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important; height: 100vh !important;
    width: 100vw !important; max-height: 100vh !important;
}
[data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"], .main {
    overflow: hidden !important; padding: 0 !important; margin: 0 !important;
    height: 100vh !important; max-height: 100vh !important;
}
.main .block-container {
    padding: var(--page-margin-top) var(--page-margin-right)
             var(--page-margin-bottom) var(--page-margin-left) !important;
    margin: 0 !important; max-width: 100% !important; width: 100% !important;
    overflow: hidden !important; height: 100vh !important; max-height: 100vh !important;
    display: flex; flex-direction: column; box-sizing: border-box;
}
.main .block-container > div:first-child { margin-top: 0 !important; padding-top: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 5px !important; }

/* Hide Streamlit chrome elements */
#MainMenu, footer, header, [data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="collapsedControl"] {
    display: none !important; visibility: hidden !important;
}
.main .block-container { display: flex; flex-direction: column; overflow: hidden; }
.main .block-container > [data-testid="stVerticalBlock"] { flex: 1; overflow: hidden; }


/* ══════════════════════════════════════════════════════════════════════
   SECTION 3 · SIDEBAR
   ► Width: change --sidebar-w in SECTION 1 (keeps margin-left in sync).
   ► Nav label font: change --fs-nav in SECTION 1.
   ► Nav label color: they inherit var(--text-color) from Streamlit.
   ► Active nav highlight uses --c-brand border & background.
══════════════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    width: var(--sidebar-w) !important;
    min-width: var(--sidebar-w) !important;
    max-width: var(--sidebar-w) !important;
    background: var(--secondary-background-color) !important;
    border-right: 1px solid rgba(46,125,50,0.5) !important;
    overflow: hidden !important; height: 100vh !important; padding-top: 0 !important;
    /* Fixed to left edge — no animation */
    position: fixed !important;
    left: 0 !important;
    margin-left: 0 !important;
    transition: none !important;
    animation: none !important;
    transform: none !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    display: flex !important; flex-direction: column !important;
    align-items: center !important; padding: 0 4px 4px !important;
}
[data-testid="stSidebar"] [data-testid="stElementToolbar"] { display: none !important; }

/* — Nav radio items — */
.stRadio > div {
    gap: 20px !important; width: 100% !important;
    flex-direction: column !important; margin-bottom: 8px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: var(--fs-nav) !important;
    font-weight: var(--fw-bold) !important;
    color: var(--text-color) !important;
    letter-spacing: 0.8px !important; text-transform: uppercase !important;
    background: rgba(46,125,50,0.12) !important; border: none !important;
    border-radius: var(--r-sm) !important; padding: 6px 8px !important;
    width: 100% !important; cursor: pointer !important;
    transition: all 0.2s !important; min-height: 44px !important;
    display: flex !important; align-items: center !important; margin-top: -15px !important;
}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(76,175,80,0.12) !important; color: var(--text-color) !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(46,125,50,0.22) !important;
    border-left: 3px solid var(--c-brand) !important;
    color: var(--text-color) !important; padding-left: 9px !important;
}
section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    margin: 0 !important; color: var(--text-color) !important;
}

/* — Logout button — */
[data-testid="stSidebar"] .stButton > button {
    font-size: var(--fs-nav) !important;
    font-weight: var(--fw-bold) !important;
    color: var(--text-color) !important;
    text-transform: uppercase !important; background: rgba(46,125,50,0.12) !important;
    border: none !important; border-radius: var(--r-sm) !important;
    padding: 6px 8px !important; width: 100% !important; cursor: pointer !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(198,40,40,0.15) !important;
    border-color: rgba(198,40,40,0.5) !important; color: var(--text-color) !important;
}

/* — Hide sidebar drag handle & collapse button — */
[data-testid="stSidebar"] > div:first-child > div:first-child {
    display: none !important; visibility: hidden !important; height: 0 !important;
}
[data-testid="collapsedControl"],
button[title="Collapse sidebar"],
button[aria-label="Collapse sidebar"] {
    display: none !important; visibility: hidden !important;
    opacity: 0 !important; pointer-events: none !important;
    width: 0 !important; height: 0 !important;
}
[data-testid="stSidebarResizer"],
section[data-testid="stSidebar"] > div:last-child {
    display: none !important; pointer-events: none !important;
}


/* ══════════════════════════════════════════════════════════════════════
   SECTION 4 · METRIC CARDS  (TEMP · HUMIDITY · SOIL rows)
   ► Value font size  →  --fs-value  in SECTION 1
   ► Label font size  →  --fs-label  in SECTION 1
   ► Label color      →  color: var(--c-brand-light) below
   ► Card border      →  border: 1px solid rgba(76,175,80,0.3) below
══════════════════════════════════════════════════════════════════════ */
div[data-testid="stMetric"] {
    background: var(--secondary-background-color) !important;
    border: 1px solid rgba(76,175,80,0.3) !important;
    border-radius: var(--r-md) !important;
    padding: 8px 6px !important; text-align: center !important;
}
div[data-testid="stMetricLabel"] {
    font-weight: var(--fw-bold) !important;
    font-size: var(--fs-label) !important;
    color: var(--c-brand-light) !important;       /* ← change label color here */
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    justify-content: center !important;
}
div[data-testid="stMetricValue"] {
    font-size: var(--fs-value) !important;
    font-weight: var(--fw-black) !important;
    color: var(--text-color) !important;          /* auto light/dark */
    margin-top: 1px !important;
}

/* — pH card (custom metric, same visual weight as stMetric) — */
.ph-metric-wrap {
    background: var(--secondary-background-color);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: var(--r-md); padding: 8px 6px; text-align: center;
}
.ph-metric-label {
    font-weight: var(--fw-bold); font-size: var(--fs-label);
    color: var(--c-brand-light); letter-spacing: 1.2px; text-transform: uppercase;
}
.ph-metric-value {
    font-size: var(--fs-value); font-weight: var(--fw-black);
    color: var(--text-color); margin-top: 1px;
}

/* — pH status badges (Acidic / Neutral / Alkaline) — */
.ph-badge {
    display: inline-block; border-radius: var(--r-sm); padding: 2px 10px;
    font-size: var(--fs-xs) !important; font-weight: var(--fw-bold);
    letter-spacing: 1px; text-transform: uppercase;
    margin-left: 6px; vertical-align: middle;
}
.ph-acidic   { background: rgba(239,83,80,0.18);  border: 1px solid rgba(239,83,80,0.5);  color: var(--c-critical-light); }
.ph-neutral  { background: rgba(76,175,80,0.18);  border: 1px solid rgba(76,175,80,0.5);  color: var(--c-healthy-light); }
.ph-alkaline { background: rgba(66,165,245,0.18); border: 1px solid rgba(66,165,245,0.5); color: var(--c-info-light); }


/* ══════════════════════════════════════════════════════════════════════
   SECTION 5 · COMPONENT STYLES
   ► Camera card, section titles, alert items, badges, image display.
   ► Font sizes reference SECTION 1 vars; colors listed inline.
══════════════════════════════════════════════════════════════════════ */

/* — Camera / image card wrapper — */
.cam-card {
    background: var(--background-color);
    border: 1px solid rgba(46,125,50,0.4);
    border-radius: var(--r-lg); padding: 10px; height: 100%;
}

/* — Section title bars (e.g. "📷 Lettuce Health Feed") — */
.section-title {
    font-size: var(--fs-md) !important;          /* ← title font size */
    font-weight: var(--fw-bold) !important;
    color: var(--text-color) !important;          /* auto light/dark   */
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    margin-bottom: 15px !important; margin-top: 0 !important;
    border-left: 3px solid var(--c-brand); padding-left: 7px;
}

/* — Alert items (red warning boxes) — */
.alert-item {
    padding: 6px 10px;
    background: rgba(183,28,28,0.12);
    border: 1px solid rgba(183,28,28,0.3);
    color: var(--text-color);
    border-radius: var(--r-sm); margin: 10px 0;
    font-size: var(--fs-base) !important;
}

/* — Schedule badge (7:00 AM · 12:00 NN · 5:00 PM) — */
.sched-badge {
    display: inline-block; background: rgba(21,101,192,0.2);
    border: 1px solid rgba(21,101,192,0.5); border-radius: 5px;
    padding: 2px 6px;
    font-size: var(--fs-xs) !important; color: var(--text-color);
    font-weight: var(--fw-bold); margin: 0 2px;
}

/* — Camera metadata text below the image — */
.cam-meta {
    font-size: var(--fs-xs) !important;           /* ← caption size    */
    color: var(--text-color);
    margin-top: 15px; line-height: 1.5;
}

/* — "View all in Drive ↗" link — */
.drive-link {
    display: inline-block; margin-top: 5px;
    background: rgba(46,125,50,0.15);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: var(--r-sm); padding: 4px 10px;
    color: var(--text-color); font-size: var(--fs-sm) !important;
    text-decoration: none;
}

/* — Empty camera placeholder (no image yet) — */
.cam-placeholder {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    min-height: 200px; background: rgba(46,125,50,0.04);
    border: 2px dashed rgba(46,125,50,0.3); border-radius: var(--r-md);
    text-align: center; padding: 20px;
}

/* — Feed image sizing — */
[data-testid="stImage"] { margin-top: 0 !important; margin-bottom: 0 !important; }
[data-testid="stImage"] img {
    border-radius: var(--r-sm) !important;
    max-height: var(--img-h) !important;           /* ← feed image height */
    object-fit: cover !important; width: 100% !important;
}

/* — Data table — */
[data-testid="stDataFrame"] {
    max-height: 300px !important; overflow-y: auto !important;
    font-size: var(--fs-base) !important;
}

/* — Alert banners (st.warning, st.error, etc.) — */
[data-testid="stAlert"] {
    padding: 8px 12px !important; font-size: var(--fs-base) !important;
    border-radius: var(--r-sm) !important; margin: 4px 0 !important;
}

/* — Selectbox — */
[data-testid="stSelectbox"] { margin-bottom: 4px !important; }
[data-baseweb="select"] { min-height: 42px !important; }
.stSelectbox label {
    font-size: var(--fs-sm) !important; color: var(--text-color) !important;
    margin-bottom: 2px !important;
}

/* — Text input — */
.stTextInput label {
    color: var(--text-color) !important;
    font-weight: var(--fw-semi) !important;
    font-size: var(--fs-base) !important;
}

/* — Column padding — */
[data-testid="column"] { height: 100%; padding: 0 4px !important; }

/* — Plotly charts — */
.js-plotly-plot, .plotly, .plot-container { max-height: var(--chart-h) !important; }
[data-testid="stPlotlyChart"] { height: var(--chart-h) !important; overflow: hidden !important; }

/* — Pulse animation (used by live-indicator elements) — */
@keyframes pulse {
    0%,100% { box-shadow: 0 0 5px var(--c-brand); }
    50%      { box-shadow: 0 0 14px var(--c-brand); opacity: 0.7; }
}


/* ══════════════════════════════════════════════════════════════════════
   SECTION 6 · LANDING PAGE BUTTON & LOGIN FORM
   ► "Let's Start" button colors: gradient from --c-brand-dark to --c-brand
   ► Login form input border: rgba(165,214,167,0.45)
   ► Login submit button: same green gradient
══════════════════════════════════════════════════════════════════════ */
.landing-btn-wrapper button {
    background: linear-gradient(135deg, var(--c-brand-dark), var(--c-brand-light)) !important;
    border: 2px solid rgba(255,255,255,0.3) !important;
    border-radius: 50px !important;
    color: white !important;
    font-size: 24px !important;                   /* ← landing button font size */
    font-weight: var(--fw-bold) !important;
    padding: 14px 48px !important; cursor: pointer !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    min-height: 64px !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
    width: auto !important;
}
.landing-btn-wrapper button:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 12px 32px rgba(76,175,80,0.7) !important;
}
.landing-page section[data-testid="stSidebar"] { display: none !important; }

/* — Login form card — */
[data-testid="stForm"] {
    background: var(--secondary-background-color) !important;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: var(--r-lg); border: 1px solid rgba(165,214,167,0.35);
    box-shadow: 0 12px 40px rgba(0,0,0,0.15); padding: 26px 36px 34px !important;
}
[data-testid="stForm"] input {
    background: var(--background-color) !important; color: var(--text-color) !important;
    border: 1px solid rgba(165,214,167,0.45) !important;
    border-radius: var(--r-md) !important;
    font-size: var(--fs-nav) !important; min-height: 48px !important;
}
[data-testid="stForm"] input::placeholder {
    color: var(--text-color) !important; opacity: 0.6 !important;
}
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(90deg, var(--c-brand-dark), var(--c-brand-light)) !important;
    border: none !important; color: #fff !important;
    font-weight: var(--fw-bold) !important;
    border-radius: var(--r-md) !important; letter-spacing: 1.5px;
    font-size: var(--fs-nav) !important;
    padding: 12px !important; min-height: 52px !important; margin-top: 4px !important;
}


/* ══════════════════════════════════════════════════════════════════════
   SECTION 7 · GREENHOUSE AI SUMMARY PANEL
   ► Card background tints: rgba values for healthy/warning/critical.
   ► Label font sizes: --fs-xs and --fs-sm.
   ► Finding row label color: #a5d6a7  (soft green on dark backgrounds).
   ► To make text larger in the summary panel, change --fs-xs and --fs-sm
     in SECTION 1 or override the px values here.
══════════════════════════════════════════════════════════════════════ */

/* — Outer status card — */
.gh-summary-card {
    border-radius: var(--r-md); padding: 14px 16px; margin: 4px 0 8px;
    font-size: var(--fs-sm); line-height: 1.8;     /* ← summary text size */
}
.gh-summary-healthy  { background: rgba(46,125,50,0.18);  border: 1px solid var(--c-healthy-light); }
.gh-summary-warning  { background: rgba(230,81,0,0.18);   border: 1px solid var(--c-warning-light); }
.gh-summary-critical { background: rgba(183,28,28,0.18);  border: 1px solid var(--c-critical-light); }
.gh-summary-pending  { background: rgba(33,33,33,0.35);   border: 1px solid var(--c-pending); }
.gh-summary-unknown  { background: rgba(21,101,192,0.12); border: 1px solid var(--c-info-light); }

/* — Finding rows inside summary card — */
.gh-finding-row {
    display: flex; gap: 6px; align-items: baseline;
    font-size: var(--fs-xs); margin: 2px 0; padding: 2px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.gh-finding-label {
    color: var(--c-brand-xlight); font-weight: var(--fw-bold);
    min-width: 110px; letter-spacing: 0.3px;
    text-transform: uppercase; font-size: 9px;   /* ← finding label size */
}
.gh-finding-value  { color: var(--text-color); flex: 1; }
.gh-finding-high   { color: var(--c-critical-light) !important; }
.gh-finding-low    { color: var(--c-warning-light) !important; }
.gh-finding-normal { color: var(--c-healthy-light) !important; }

/* — Plant status pills — */
.tally-pill {
    display: inline-block; border-radius: 20px; padding: 2px 10px;
    font-size: var(--fs-xs); font-weight: var(--fw-bold);
    margin: 0 3px; letter-spacing: 0.5px;
}
.tally-healthy  { background: rgba(46,125,50,0.3);  border: 1px solid var(--c-healthy-light);  color: var(--c-healthy-light); }
.tally-warning  { background: rgba(230,81,0,0.3);   border: 1px solid var(--c-warning-light);  color: var(--c-warning-light); }
.tally-critical { background: rgba(183,28,28,0.3);  border: 1px solid var(--c-critical-light); color: var(--c-critical-light); }

/* — SMS sent / not-sent badges — */
.sms-sent-badge {
    display: inline-block; background: rgba(21,101,192,0.25);
    border: 1px solid var(--c-info-light); border-radius: 4px;
    padding: 1px 6px; font-size: 9px; color: var(--c-info-light);
    font-weight: var(--fw-bold); margin-left: 6px; vertical-align: middle;
    letter-spacing: 0.5px;
}
.sms-no-badge {
    display: inline-block; background: rgba(66,66,66,0.25);
    border: 1px solid #888; border-radius: 4px;
    padding: 1px 6px; font-size: 9px; color: #aaa;
    font-weight: var(--fw-bold); margin-left: 6px; vertical-align: middle;
}

/* — Sensor summary block — */
.gh-sensor-summary {
    font-size: var(--fs-xs); color: var(--text-color); line-height: 1.7;
    background: rgba(46,125,50,0.08); border-radius: var(--r-sm);
    padding: 6px 8px; margin-bottom: 8px;
    border-left: 3px solid rgba(76,175,80,0.4);
}

/* — Alert list items — */
.gh-alert-item {
    padding: 4px 8px; margin: 3px 0;
    background: rgba(183,28,28,0.10);
    border-left: 3px solid var(--c-critical-light);
    border-radius: 0 var(--r-sm) var(--r-sm) 0;
    font-size: var(--fs-xs); color: var(--c-critical-light); line-height: 1.5;
}
.gh-alert-none {
    font-size: var(--fs-xs); color: var(--text-color);
    font-style: italic; padding: 2px 0;
}

/* — Recommendation bullet items — */
.gh-rec-item {
    padding: 3px 0; font-size: var(--fs-xs);  /* ← rec text size */
    color: var(--text-color);
    line-height: 1.6;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    display: flex; gap: 6px; align-items: flex-start;
}
.gh-rec-bullet { color: var(--text-color); font-weight: var(--fw-black); flex-shrink: 0; margin-top: 1px; }


/* ══════════════════════════════════════════════════════════════════════
   7-INCH DISPLAY NOTE
   The styles above (Sections 1-7) ARE the 7-inch 1024×600 layout.
   No media query is needed for the Pi screen — it is the default.
   If you are only ever using the 7-inch display, you can safely
   ignore Sections 8 and 9 below.
══════════════════════════════════════════════════════════════════════ */


/* ══════════════════════════════════════════════════════════════════════
   SECTION 8 · RESPONSIVE — MOBILE  (screen width < 768px)
   ► Sidebar hides automatically.
   ► App becomes vertically scrollable (no fixed height).
   ► Metric values shrink slightly.
   ► Section title and body text grow for finger-friendly reading.
   ► Touch targets are at least 44px tall.
   ► Edit font sizes here without touching Section 1 tokens.
══════════════════════════════════════════════════════════════════════ */
@media screen and (max-width: 767px) {

    /* — On mobile the sidebar becomes Streamlit's native slide-over overlay.
         Restore the hamburger toggle button so the user can open/close it.
         The sidebar does NOT disappear — it slides in over the content. — */
    [data-testid="collapsedControl"],
    button[title="Collapse sidebar"],
    button[aria-label="Collapse sidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        width: auto !important;
        height: auto !important;
    }

    /* — Sidebar overlays content on mobile (no column push) — */
    section[data-testid="stSidebar"] {
        position: fixed !important;
        z-index: 999 !important;
        width: var(--sidebar-w) !important;
    }

    /* — No left margin on mobile since sidebar is an overlay, not a column — */
    [data-testid="stAppViewContainer"] { margin-left: 0 !important; }

    /* — Allow vertical scrolling — */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .main, .main .block-container {
        overflow-y: auto !important;
        height: auto !important;
        max-height: none !important;
    }

    /* — Comfortable content padding — */
    .main .block-container {
        padding: 12px 10px !important;
    }

    /* — Metric value slightly smaller on narrow screens — */
    div[data-testid="stMetricValue"],
    .ph-metric-value {
        font-size: 20px !important;                /* ← mobile metric value size */
    }

    /* — Section titles — */
    .section-title {
        font-size: 15px !important;               /* ← mobile section title size */
        margin-bottom: 10px !important;
    }

    /* — Body / summary text: slightly larger for poor eyesight — */
    html, body { font-size: 15px !important; }     /* ← mobile base font size    */
    .gh-summary-card  { font-size: 13px !important; }
    .gh-finding-label { font-size: 10px !important; }
    .gh-rec-item      { font-size: 12px !important; }

    /* — Chart height on mobile — */
    .js-plotly-plot, .plotly, .plot-container { max-height: 250px !important; }
    [data-testid="stPlotlyChart"]             { height: 250px !important; }

    /* — Touch-friendly minimum heights — */
    [data-baseweb="select"] { min-height: 50px !important; }
    [data-testid="stForm"] input { min-height: 52px !important; }
}


/* ══════════════════════════════════════════════════════════════════════
   SECTION 9 · RESPONSIVE — DESKTOP  (screen width ≥ 1025px)
   ► Sidebar stays visible (same as 7-inch base styles).
   ► Content area allows vertical scrolling for long pages.
   ► Fonts can be made larger here for high-DPI / large monitors.
   ► Edit independently from the 7-inch base in Sections 1-7.
══════════════════════════════════════════════════════════════════════ */
@media screen and (min-width: 1025px) {

    /* — Allow vertical scrolling on tall content — */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .main, .main .block-container {
        overflow-y: auto !important;
        height: auto !important;
        max-height: none !important;
    }

    /* — Optional: slightly larger base text on desktop monitors —    */
    /* Uncomment the line below if you want bigger text on desktop:   */
    /* html, body { font-size: 15px !important; }                     */

    /* — Optional: taller charts on wide screens —                    */
    /* .js-plotly-plot, .plotly, .plot-container { max-height: 280px !important; } */
    /* [data-testid="stPlotlyChart"] { height: 280px !important; }    */
}

</style>
"""
st.markdown(OPTIMIZED_CSS, unsafe_allow_html=True)

# ── Sidebar margin — dashboard page only ─────────────────────────────
# NOTE: This injects margin-left equal to the sidebar width so the
# main content doesn't sit under the fixed sidebar.
# If you change --sidebar-w in Section 1, also update 230px here.
if st.session_state.get("logged_in") and st.session_state.get("page") == "dashboard":
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {
        margin-left: 230px !important;   /* ← match --sidebar-w in Section 1 */
    }
    </style>""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def file_to_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def ph_label(ph_val: float) -> tuple:
    if ph_val < 5.5:
        return "Acidic", "ph-acidic"
    elif ph_val <= 7.0:
        return "Neutral", "ph-neutral"
    else:
        return "Alkaline", "ph-alkaline"


def gdrive_direct_url(url: str) -> str:
    if not url:
        return ""
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
    if not url:
        return None
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
    if not b64:
        return
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    st.markdown(f"""<style>
    .stApp {{
        background-image: url("data:{mime};base64,{b64}");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }}
    .stApp::before {{
        content: ""; position: fixed; inset: 0;
        background: rgba(0,0,0,0.52); z-index: 0; pointer-events: none;
    }}
    </style>""", unsafe_allow_html=True)


def safe_read_sheet(sheet_obj) -> pd.DataFrame:
    try:
        data = sheet_obj.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame()
        raw_headers = data[0]
        seen = {}
        headers = []
        for h in raw_headers:
            h = h.strip()
            if h in seen:
                seen[h] += 1
                headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                headers.append(h)
        df = pd.DataFrame(data[1:], columns=headers)

        # ai_summary is the new overall greenhouse summary column
        expected = ['timestamp', 'plant_id', 'temp_c', 'humidity',
                    'soil_moisture', 'ph', 'image_url', 'ai_status', 'ai_summary']
        df = df[[c for c in expected if c in df.columns]]

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        for col in ['temp_c', 'humidity', 'soil_moisture', 'ph']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'plant_id' in df.columns:
            df['plant_id'] = pd.to_numeric(df['plant_id'], errors='coerce')
        df = df.dropna(subset=['timestamp', 'plant_id'])
        return df
    except Exception as e:
        st.error(f"Sheet read error: {e}")
        return pd.DataFrame()


# ============================================================
# DRIVE IMAGE HELPERS
# ============================================================
def _get_drive_service_private():
    if not DRIVE_API_OK:
        return None
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
        print(f"[Drive Private] Service build error: {e}")
        return None


def _get_file_id_from_url(url: str) -> str:
    if not url:
        return ""
    if "id=" in url:
        return url.split("id=")[1].split("&")[0].strip()
    if "/file/d/" in url:
        return url.split("/file/d/")[1].split("/")[0].strip()
    return ""


def fetch_drive_image_private(file_id: str):
    if not file_id or not DRIVE_API_OK:
        return None
    try:
        svc = _get_drive_service_private()
        if not svc:
            return None
        request = svc.files().get_media(fileId=file_id)
        buf  = io.BytesIO()
        dl   = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        return PILImage.open(buf)
    except Exception as e:
        print(f"[Drive Private] Download error: {e}")
        return None


# ============================================================
# GREENHOUSE SUMMARY PARSER (UPDATED FOR NEW PI FORMAT)
# ============================================================
def parse_ai_summary(ai_summary_str: str) -> dict:
    """
    Parses the new Gemini summary format (Greenhouse Status / Findings /
    Recommendation / Critical Plants) and legacy formats for backward compatibility.
    Returns a dict with keys used by the UI.
    """
    if not ai_summary_str or str(ai_summary_str).strip() in ("", "nan", "N/A"):
        return {}

    s = str(ai_summary_str).strip()

    if s == "Wait for Batch...":
        return {"__pending__": True}

    # ── NEW THESIS FORMAT (Greenhouse Status with Findings) ────────────────
    if "Greenhouse Status:" in s and "Findings:" in s:
        result = {"__new_format__": True}

        def _find_new(pattern, default=""):
            m = re.search(pattern, s, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else default

        # Extract status from "Greenhouse Status: <Healthy / Warning / Critical>"
        status_line = _find_new(r'Greenhouse Status:\s*(.*?)(?=\n\n|\n|$)', "Unknown")
        result['status_label'] = status_line
        sl = status_line.lower()
        if 'critical' in sl:
            result['status'] = 'Critical'
        elif 'warning' in sl:
            result['status'] = 'Warning'
        elif 'healthy' in sl:
            result['status'] = 'Healthy'
        else:
            result['status'] = 'Unknown'

        # Findings section with 6 subsections
        findings_raw = _find_new(r'Findings:\s*(.*?)(?=\n\nRecommendation:|\Z)', "")

        # Parse each Finding subsection
        img_match = re.search(r'Images:\s*(.+?)(?=\nDisease:|\nSoil|\nTemperature:|\nHumidity:|\npH|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)
        disease_match = re.search(r'Disease:\s*(.+?)(?=\nSoil|\nTemperature:|\nHumidity:|\npH|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)
        soil_match = re.search(r'Soil Moisture:\s*(.+?)(?=\nTemperature:|\nHumidity:|\npH|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)
        temp_match = re.search(r'Temperature:\s*(.+?)(?=\nHumidity:|\npH|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)
        hum_match = re.search(r'Humidity:\s*(.+?)(?=\npH|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)
        ph_match = re.search(r'pH Level:\s*(.+?)(?=\n\n|\Z)', findings_raw, re.IGNORECASE | re.DOTALL)

        result['finding_image'] = img_match.group(1).strip() if img_match else "N/A"
        result['finding_disease'] = disease_match.group(1).strip() if disease_match else "N/A"
        result['finding_soil'] = soil_match.group(1).strip() if soil_match else "N/A"
        result['finding_temp'] = temp_match.group(1).strip() if temp_match else "N/A"
        result['finding_humidity'] = hum_match.group(1).strip() if hum_match else "N/A"
        result['finding_ph'] = ph_match.group(1).strip() if ph_match else "N/A"

        # Recommendation section (single recommendation text)
        rec_raw = _find_new(r'Recommendation:\s*(.*?)(?=\n\nCritical Plants:|\Z)', "")
        if rec_raw:
            # Convert to list for UI compatibility
            result['recommendations'] = [ln.strip() for ln in rec_raw.splitlines() if ln.strip()]
        else:
            result['recommendations'] = []

        # Critical Plants section
        critical_raw = _find_new(r'Critical Plants:\s*(.*?)\Z', "")
        if critical_raw and critical_raw.lower() != 'none':
            result['alert_list'] = [f"Critical: {p.strip()}" for p in critical_raw.split(',') if p.strip()]
        else:
            result['alert_list'] = []

        # No SMS in new format
        result['sms_line'] = ""

        return result

    # ── LEGACY PI FORMAT (OVERALL STATUS - backward compatible) ───────────
    if "OVERALL STATUS:" in s:
        result = {"__new_format__": True}

        def _find_new(pattern, default=""):
            m = re.search(pattern, s, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else default

        # Overall status line
        result['status_label'] = _find_new(r'OVERALL STATUS:\s*(.*?)(?=\n\nSENSOR SUMMARY:|\Z)', "Unknown")
        sl = result['status_label'].lower()
        if 'high' in sl:
            result['status'] = 'Critical'
        elif 'moderate' in sl:
            result['status'] = 'Warning'
        elif 'healthy' in sl:
            result['status'] = 'Healthy'
        else:
            result['status'] = 'Unknown'

        # Sensor summary paragraph
        result['sensor_summary'] = _find_new(r'SENSOR SUMMARY:\s*(.*?)(?=\n\nDISEASE ALERTS:|\Z)', "")

        # Disease alerts (list)
        alerts_raw = _find_new(r'DISEASE ALERTS:\s*(.*?)(?=\n\nRECOMMENDATIONS:|\Z)', "")
        if alerts_raw and "No disease" not in alerts_raw:
            result['alert_list'] = [
                ln.lstrip('- ').strip()
                for ln in alerts_raw.splitlines()
                if ln.strip() and ln.strip().lower() != 'none'
            ]
        else:
            result['alert_list'] = []

        # Recommendations (list)
        recs_raw = _find_new(r'RECOMMENDATIONS:\s*(.*?)\Z', "")
        if recs_raw:
            result['recommendations'] = [
                ln.lstrip('- ').strip()
                for ln in recs_raw.splitlines()
                if ln.strip()
            ]
        else:
            result['recommendations'] = []

        # No SMS in new format
        result['sms_line'] = ""

        return result

    # ── OLD FORMAT (backward compatible, per-plant parsing) ───────────────
    def _find(pattern, default="N/A"):
        m = re.search(pattern, s, re.IGNORECASE)
        return m.group(1).strip() if m else default

    result = {}

    # Overall status
    result['status'] = _find(r'Status:\s*(Healthy|Warning|Critical|Unknown)', "Unknown")

    # Findings — updated to match Pi's new per-plant output (no asterisks)
    result['finding_image']    = _find(r'Image\s*:\s*(.+)')
    result['finding_disease']  = _find(r'Disease\s*:\s*(.+)')
    result['finding_soil']     = _find(r'Soil Moisture\s*:\s*(.+)')
    result['finding_temp']     = _find(r'Temperature\s*:\s*(.+)')
    result['finding_humidity'] = _find(r'Humidity\s*:\s*(.+)')
    result['finding_ph']       = _find(r'pH Level\s*:\s*(.+)')

    # Recommendation (multi-line block after "Recommendation:\n")
    rec_m = re.search(r'Recommendation:\s*\n([\s\S]+)\Z', s)
    if rec_m:
        rec_lines = [ln.lstrip() for ln in rec_m.group(1).splitlines() if ln.strip()]
        result['recommendation'] = " ".join(rec_lines)
    else:
        result['recommendation'] = _find(r'Recommendation:\s*(.+)', "N/A")

    # For old format we still support SMS if present, but UI will hide if empty
    result['sms_line'] = _find(r'SMS:\s*(.+)', "")

    # For compatibility with existing UI (critical/warning plants not in new per-plant)
    result['critical_plants'] = ""
    result['warning_plants'] = ""

    return result


def _finding_class(value_str: str) -> str:
    """Returns CSS class based on High/Low/Normal label in the finding string."""
    v = value_str.lower()
    if v.startswith("high"):   return "gh-finding-high"
    if v.startswith("low"):    return "gh-finding-low"
    if v.startswith("normal"): return "gh-finding-normal"
    return ""


def _status_label_to_display(status_label: str) -> str:
    """Maps 'High Risk' → '🔴 High Risk', 'Moderate Risk' → '⚠️ Moderate Risk', etc."""
    sl = status_label.lower()
    if 'high' in sl:     return f"🔴 {status_label}"
    if 'moderate' in sl: return f"⚠️ {status_label}"
    if 'healthy' in sl:  return f"✅ {status_label}"
    return f"ℹ️ {status_label}"


def render_greenhouse_summary_panel(df: pd.DataFrame):
    """
    Renders the 🤖 AI Greenhouse Summary panel on the dashboard.
    Handles both the new Pi format and the old format.
    """
    if df.empty or 'ai_summary' not in df.columns:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:var(--text-color);">'
            '🕒 No AI summary yet — add the <b>ai_summary</b> column to your Google Sheet '
            'and run the next camera session.'
            '</div>', unsafe_allow_html=True)
        return

    summary_df = df[
        df['ai_summary'].astype(str).str.strip().replace('nan', '') != ''
    ].copy()

    if summary_df.empty:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:var(--text-color);">'
            '🕒 Greenhouse summary not available yet.<br><br>'
            'The Pi writes a summary after each camera session '
            '(<span class="sched-badge">7:00 AM</span>'
            '<span class="sched-badge">12:00 NN</span>'
            '<span class="sched-badge">5:00 PM</span>).'
            '</div>', unsafe_allow_html=True)
        return

    latest_row  = summary_df.sort_values('timestamp').iloc[-1]
    raw_summary = str(latest_row['ai_summary']).strip()
    ts          = pd.to_datetime(latest_row['timestamp']).strftime("%b %d, %Y · %I:%M %p")

    parsed = parse_ai_summary(raw_summary)

    if not parsed:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:var(--text-color);">'
            '🕒 No AI summary yet — waiting for next camera session.'
            '</div>', unsafe_allow_html=True)
        return

    if parsed.get("__pending__"):
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:var(--text-color);">'
            '🔄 AI analyzing batch... greenhouse summary will appear shortly.'
            '</div>', unsafe_allow_html=True)
        return

    status = parsed.get('status', 'Unknown')
    color_map = {
        "Healthy":  ("#81c784", "gh-summary-healthy",  "✅"),
        "Warning":  ("#ffb74d", "gh-summary-warning",  "⚠️"),
        "Critical": ("#ef9a9a", "gh-summary-critical", "🔴"),
        "Unknown":  ("#90CAF9", "gh-summary-unknown",  "ℹ️"),
    }
    txt_c, css_cls, icon = color_map.get(status, ("var(--text-color);", "gh-summary-unknown", "ℹ️"))

    # ── RENDER NEW FORMAT (with Findings section) ─────────────────────────
    if parsed.get('__new_format__'):
        status_label  = parsed.get('status_label', status)
        alert_list    = parsed.get('alert_list', [])
        recs          = parsed.get('recommendations', [])
        sms_line      = parsed.get('sms_line', '')

        # Findings data
        finding_img      = parsed.get('finding_image', 'N/A')
        finding_disease  = parsed.get('finding_disease', 'N/A')
        finding_soil     = parsed.get('finding_soil', 'N/A')
        finding_temp     = parsed.get('finding_temp', 'N/A')
        finding_humidity = parsed.get('finding_humidity', 'N/A')
        finding_ph       = parsed.get('finding_ph', 'N/A')

        # Build Findings HTML
        findings_html = (
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">Images</span>'
            f'<span class="gh-finding-value">{finding_img}</span>'
            f'</div>'
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">Disease</span>'
            f'<span class="gh-finding-value">{finding_disease}</span>'
            f'</div>'
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">Soil Moisture</span>'
            f'<span class="gh-finding-value">{finding_soil}</span>'
            f'</div>'
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">Temperature</span>'
            f'<span class="gh-finding-value">{finding_temp}</span>'
            f'</div>'
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">Humidity</span>'
            f'<span class="gh-finding-value">{finding_humidity}</span>'
            f'</div>'
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">pH Level</span>'
            f'<span class="gh-finding-value">{finding_ph}</span>'
            f'</div>'
        )

        # Critical Plants badges
        if alert_list:
            critical_html = "".join(
                f'<span class="tally-pill tally-critical">{item}</span> '
                for item in alert_list
            )
        else:
            critical_html = '<span class="tally-pill tally-healthy">✅ No critical plants</span>'

        # Recommendations
        recs_html = "".join(
            f'<div class="gh-rec-item">'
            f'<span class="gh-rec-bullet">▸</span>'
            f'<span>{rec}</span>'
            f'</div>'
            for rec in recs
        ) if recs else '<div style="font-size:10px;color:#888;">No recommendations.</div>'

        sms_html = (
            f'<div style="margin-top:8px;padding:6px 8px;'
            f'background:rgba(21,101,192,0.12);border:1px solid rgba(144,202,249,0.3);'
            f'border-radius:6px;font-size:9px;color:var(--text-color);">'
            f'<span style="font-weight:700;letter-spacing:0.5px;">📨 SMS ALERT: </span>'
            f'{sms_line}'
            f'</div>'
        ) if sms_line else ""

        st.markdown(
            f'<div class="gh-summary-card {css_cls}">'
            f'<div style="font-weight:900;color:{txt_c};font-size:13px;'
            f'margin-bottom:6px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">'
            f'{icon} Overall Status: <b>{status_label}</b>'
            f'<span style="font-size:9px;color:var(--text-color);font-weight:400;margin-left:6px;">{ts}</span>'
            f'</div>'
            f'<div style="margin-bottom:8px;">'
            f'{critical_html}'
            f'</div>'
            f'<div style="margin-bottom:6px;">'
            f'<div style="font-size:9px;font-weight:700;color:#a5d6a7;'
            f'letter-spacing:0.8px;text-transform:uppercase;margin-bottom:4px;">'
            f'FINDINGS</div>'
            f'{findings_html}'
            f'</div>'
            f'<div style="padding-top:6px;border-top:1px solid rgba(255,255,255,0.07);">'
            f'<div style="font-size:9px;font-weight:700;color:#66bb6a;'
            f'letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">'
            f'RECOMMENDATION</div>'
            f'{recs_html}'
            f'</div>'
            f'{sms_html}'
            f'</div>',
            unsafe_allow_html=True)
        return

    # ── OLD FORMAT RENDER (unchanged, works with updated parsed fields) ───
    # Affected plant pills (from old format, may be empty)
    crit_pids = parsed.get('critical_plants', '').strip()
    warn_pids = parsed.get('warning_plants',  '').strip()
    tally_html = ""
    if crit_pids:
        tally_html += f'<span class="tally-pill tally-critical">🔴 Critical Lettuce: {crit_pids}</span> '
    if warn_pids:
        tally_html += f'<span class="tally-pill tally-warning">⚠️ Warning Lettuce: {warn_pids}</span>'
    if not tally_html and status == "Healthy":
        tally_html = '<span class="tally-pill tally-healthy">✅ All lettuce healthy</span>'

    # Disease alert line if present in old format
    disease_alert_match = re.search(r'Disease Alert\s*:\s*(.+)', raw_summary, re.IGNORECASE)
    disease_html = ""
    if disease_alert_match:
        disease_text = disease_alert_match.group(1).strip()
        disease_html = f'<div style="margin-top:4px;font-size:10px;color:#ffb74d;">🦠 Disease Alert: {disease_text}</div>'

    # Findings rows
    findings = [
        ("Image",         parsed.get('finding_image',    'N/A')),
        ("Soil Moisture", parsed.get('finding_soil',     'N/A')),
        ("Temperature",   parsed.get('finding_temp',     'N/A')),
        ("Humidity",      parsed.get('finding_humidity', 'N/A')),
        ("pH Level",      parsed.get('finding_ph',       'N/A')),
    ]
    findings_html = ""
    for label, value in findings:
        val_cls = _finding_class(value)
        findings_html += (
            f'<div class="gh-finding-row">'
            f'<span class="gh-finding-label">{label}</span>'
            f'<span class="gh-finding-value {val_cls}">{value}</span>'
            f'</div>'
        )

    rec      = parsed.get('recommendation', 'N/A')
    sms_line = parsed.get('sms_line', '')
    sms_html = (
        f'<div style="margin-top:8px;padding:6px 8px;'
        f'background:rgba(21,101,192,0.12);border:1px solid rgba(144,202,249,0.3);'
        f'border-radius:6px;font-size:9px;color:#90CAF9;">'
        f'<span style="font-weight:700;letter-spacing:0.5px;">📨 SMS ALERT: </span>{sms_line}'
        f'</div>'
    ) if sms_line else ""

    st.markdown(
        f'<div class="gh-summary-card {css_cls}">'
        f'<div style="font-weight:900;color:{txt_c};font-size:13px;'
        f'margin-bottom:6px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">'
        f'{icon} Overall Status: <b>{status}</b>'
        f'<span style="font-size:9px;color:#888;font-weight:400;margin-left:6px;">{ts}</span>'
        f'</div>'
        f'<div style="margin-bottom:8px;">{tally_html}</div>'
        f'{disease_html}'
        f'<div style="margin-bottom:8px;">'
        f'<div style="font-size:9px;font-weight:700;color:#a5d6a7;'
        f'letter-spacing:0.8px;text-transform:uppercase;margin-bottom:4px;">'
        f'FINDINGS (Greenhouse Average)</div>'
        f'{findings_html}'
        f'</div>'
        f'<div style="padding-top:6px;border-top:1px solid rgba(255,255,255,0.07);">'
        f'<div style="font-size:9px;font-weight:700;color:#66bb6a;'
        f'letter-spacing:0.8px;text-transform:uppercase;margin-bottom:3px;">'
        f'RECOMMENDATION</div>'
        f'<div style="font-size:10px;color:#e8f5e9;line-height:1.7;">{rec}</div>'
        f'</div>'
        f'{sms_html}'
        f'</div>',
        unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role      = None

if "page" not in st.session_state:
    st.session_state.page = "landing"

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
        st.markdown("<div style='margin-top: 45vh;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-left: -45vh;'></div>", unsafe_allow_html=True)
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
        f'style="width:100px;height:100px;border-radius:50%;'
        f'border:3px solid #4CAF50;object-fit:cover;'
        f'box-shadow:0 0 28px rgba(76,175,80,0.5);"/></div>'
    ) if logo_b64 else ""

    st.markdown(
        f'<div style="display:flex;flex-direction:column;align-items:center;margin-top:-90px;">'
        f'{logo_html}'
        f'<div style="text-align:center;font-size:34px;font-weight:900;color:#fff;'
        f'letter-spacing:1px;text-shadow:0 2px 12px rgba(0,0,0,0.6);margin-bottom:4px;">'
        f'AgriBot-AI</div>'
        f'<div style="text-align:center;color:#81c784;font-size:12px;'
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
# DATA FUNCTIONS
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
    """Latest sensor readings per plant (all plant_id > 0 rows)."""
    if sheet is None:
        return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty:
        return df
    # Only real plant rows (plant_id 1–8)
    df = df[df['plant_id'] > 0]
    return df.sort_values('timestamp').groupby('plant_id').last().reset_index()


@st.cache_data(ttl=60)
def get_historical_data(plant_id=None, hours=24):
    if sheet is None:
        return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty:
        return df
    df = df[df['plant_id'] > 0]
    df = df[df['timestamp'] >= datetime.now() - timedelta(hours=hours)]
    if plant_id is not None:
        df = df[df['plant_id'] == plant_id]
    return df.sort_values('timestamp')


@st.cache_data(ttl=30)
def get_latest_plant_image() -> dict:
    if sheet is None:
        return {}
    df = safe_read_sheet(sheet)
    if df.empty or 'image_url' not in df.columns:
        return {}
    df = df[df['plant_id'] > 0]
    df_img = df[df['image_url'].astype(str).str.contains("id=", na=False)]
    if df_img.empty:
        return {}
    df_img = df_img.sort_values('timestamp', ascending=False)
    row    = df_img.iloc[0]
    plant  = int(row['plant_id'])
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
        f'<div style="display:flex; flex-direction:column; align-items:center; '
        f'padding-top:8px; width:100%;">'
        f'<div style="padding:2px; border-radius:50%; '
        f'background:linear-gradient(145deg,#388e3c,#1b5e20); '
        f'box-shadow:0 0 12px rgba(76,175,80,0.3); margin-bottom:2px;">'
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="border-radius:50%; width:90px; height:90px; '
        f'display:block; object-fit:cover; background:#0a0d12;"/>'
        f'</div>'
        f'<div style="font-size:18px; font-weight:900; color:#ffffff; '
        f'letter-spacing:0.5px; margin-bottom:3px;">AgriBot-AI</div>'
        f'<div style="font-size:12px; font-weight:700; letter-spacing:1px; '
        f'text-transform:uppercase; padding:1px 8px; border-radius:20px; '
        f'background:rgba(46,125,50,0.15); border:1px solid rgba(76,175,80,0.25); '
        f'color:#ffffff; margin-bottom:7px;">'
        f'{"👑 Admin" if st.session_state.role == "admin" else "🌿 Field User"}'
        f'</div>'
        f'<div style="font-size:14px; font-weight:700; color:#ffffff; '
        f'letter-spacing:2px; text-transform:uppercase; width:100%; '
        f'text-align:center; padding:0 2px; margin-bottom:2px;">Navigation</div>',
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


# ============================================================
# SHARED DATA + THRESHOLDS
# ============================================================
model,  scaler = load_assets()
latest         = get_latest_readings()

PH_LOW,   PH_HIGH   = 5.5, 7.0
SOIL_DRY, SOIL_WET  = 30,  85
TEMP_LOW, TEMP_HIGH = 15,  35
HUM_LOW,  HUM_HIGH  = 50,  90

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="autorefresh")


# ============================================================
# PAGE: LIVE DASHBOARD
# ============================================================
if page == "DASHBOARD":
    st.markdown(
        '<div style="padding:10px; background-color:var(--secondary-background-color); border-radius:10px; margin-bottom:20px;">'
        '<div style="font-size:16px;font-weight:700;color:var(--text-color);opacity:0.7;text-transform:uppercase;">Real-Time Monitoring</div>'
        '<div style="font-size:28px;font-weight:900;color:var(--text-color);margin-top:-5px;">'
        'Greenhouse Overview — AgriBot-AI</div>'
        '</div>', unsafe_allow_html=True)

    if latest.empty:
        st.warning("No sensor data yet — waiting for the Pi to scan the lettuce...")
        st.stop()

    avg_temp = float(latest['temp_c'].mean())
    avg_hum  = float(latest['humidity'].mean())
    avg_ph   = float(latest['ph'].mean())
    avg_soil = float(latest['soil_moisture'].mean())

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TEMP",     f"{avg_temp:.1f} °C")
    m2.metric("HUMIDITY", f"{avg_hum:.0f} %")

    ph_lbl, ph_cls = ph_label(avg_ph)
    with m3:
        st.markdown(
            f'<div class="ph-metric-wrap">'
            f'<div class="ph-metric-label">PH</div>'
            f'<div class="ph-metric-value">'
            f'{avg_ph:.2f}'
            f'<span class="ph-badge {ph_cls}">{ph_lbl}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True)

    m4.metric("SOIL", f"{avg_soil:.0f} %")

    img_data = get_latest_plant_image()
    cam_col, right_col = st.columns([3, 2], gap="small")

    # Plant Health Feed
    with cam_col:
        st.markdown('<div style="margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📷 Lettuce Health Feed</div>',
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
                    '<div style="font-size:11px;color:#ef9a9a;margin-top:6px;">'
                    'Image could not be loaded.<br>'
                    'Check Drive sharing permissions or credentials.json.</div>'
                    '</div>', unsafe_allow_html=True)

            pid_txt = f"🥬 Lettuce {img_data['plant_id']}" if img_data.get("plant_id") else ""
            ts_txt  = f"🕒 {img_data['timestamp']}"       if img_data.get("timestamp") else ""
            st.markdown(
                f'<div class="cam-meta">{pid_txt}&nbsp;&nbsp;{ts_txt}<br>'
                f'Captured at '
                f'<span class="sched-badge">7:00 AM</span>'
                f'<span class="sched-badge">12:00 NN</span>'
                f'<span class="sched-badge">5:00 PM</span></div>'
                f'<a href="{DRIVE_FOLDER_URL}" target="_blank" class="drive-link">'
                f'☁️ View all in Drive ↗</a>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="cam-placeholder">'
                '<div style="font-size:36px;margin-bottom:8px;">📷</div>'
                '<div style="font-size:12px;font-weight:700;color:#4CAF50;">No image yet</div>'
                '<div style="font-size:10px;color:#2e7d32;margin-top:100px;">'
                'Captures at '
                '<span class="sched-badge">7:00 AM</span>'
                '<span class="sched-badge">12:00 NN</span>'
                '<span class="sched-badge">5:00 PM</span></div>'
                '</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Right column: AI Greenhouse Summary
    with right_col:
        if not latest.empty:
            last_ts = pd.to_datetime(latest['timestamp']).max()
            st.markdown(
                f'<div style="text-align:right;font-size:9px;color:#388e3c;'
                f'margin-bottom:6px;">🔄 {last_ts.strftime("%H:%M:%S")}</div>',
                unsafe_allow_html=True)

        st.markdown('<div class="section-title">🤖 AI Lettuce Summary</div>',
                    unsafe_allow_html=True)

        # Pass full dataframe — render function finds latest non-blank ai_summary
        all_df = safe_read_sheet(sheet) if sheet else pd.DataFrame()
        render_greenhouse_summary_panel(all_df)


# ============================================================
# PAGE: ANALYSIS
# ============================================================
elif page == "ANALYSIS":
    st.markdown(
        '<div style="padding:10px; background-color:var(--secondary-background-color); border-radius:10px; margin-bottom:20px;">'
        '<div style="font-size:16px;font-weight:700;color:var(--text-color);opacity:0.7;text-transform:uppercase;">Historical Trends</div>'
        '<div style="font-size:28px;font-weight:900;color:var(--text-color);margin-top:-5px;">'
        'Sensor data over time</div>'
        '</div>', unsafe_allow_html=True)

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
        "Temperature (°C)": ("temp_c",       "°C"),
        "Humidity (%)":     ("humidity",      "%"),
        "pH":               ("ph",            "pH"),
        "Soil Moisture (%)":("soil_moisture", "%"),
    }
    y_col, y_label = col_map[sensor_choice]

    if sensor_choice == "Soil Moisture (%)":
        plant_sel = st.selectbox(
            "Select Plant", list(range(1, 9)),  # Shows 1-8
            format_func=lambda x: f"Lettuce {x}")
        hist_df = get_historical_data(plant_id=plant_sel, hours=hours)
        chart_title = f"Soil Moisture — Lettuce {plant_sel}"

        if not hist_df.empty:
            fig = px.line(hist_df, x='timestamp', y=y_col, title=chart_title)
            fig.update_layout(
                height=210, margin=dict(t=32, b=20, l=30, r=10),
                yaxis_title=y_label,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(13,17,23,0.85)',
                font_color='#a5d6a7',
                title_font_color='#fff', title_font_size=12,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data for this plant in the selected time range.")

        st.markdown('<div class="section-title">🌱 All Lettuce — Current Soil Moisture</div>',
                    unsafe_allow_html=True)

        soil_rows = []
        for _, row in latest.iterrows():
            soil_rows.append({
                "Plant":  f"L{int(row['plant_id'])}",
                "Soil %": float(row['soil_moisture']),
                "Status": "Dry" if float(row['soil_moisture']) < SOIL_DRY
                          else ("Wet" if float(row['soil_moisture']) > SOIL_WET else "OK")
            })
        soil_df = pd.DataFrame(soil_rows)

        bar = px.bar(
            soil_df, x='Plant', y='Soil %',
            color='Soil %', color_continuous_scale='Greens',
            text='Soil %',
            labels={'Plant': 'Plant', 'Soil %': 'Soil Moisture (%)'}
        )
        bar.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        bar.update_layout(
            height=200, margin=dict(t=10, b=20, l=30, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(13,17,23,0.85)',
            font_color='#a5d6a7', coloraxis_showscale=False,
        )
        st.plotly_chart(bar, use_container_width=True)

    else:
        hist_df = get_historical_data(plant_id=None, hours=hours)
        chart_title = f"{sensor_choice} — Greenhouse Overall"

        if not hist_df.empty:
            overall = (
                hist_df.groupby('timestamp')[y_col]
                .mean()
                .reset_index()
                .sort_values('timestamp')
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
                plot_bgcolor='rgba(13,17,23,0.85)',
                font_color='#a5d6a7',
                title_font_color='#fff', title_font_size=12,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data in the selected time range.")


# ============================================================
# PAGE: SYSTEM LOGS
# ============================================================
elif page == "LOGS":
    st.markdown(
        '<div style="padding:10px; background-color:var(--secondary-background-color); border-radius:10px; margin-bottom:20px;">'
        '<div style="font-size:16px;font-weight:700;color:var(--text-color);opacity:0.7;text-transform:uppercase;">System Logs</div>'
        '<div style="font-size:28px;font-weight:900;color:var(--text-color);margin-top:-5px;">'
        'Sensor and AI history</div>'
        '</div>', unsafe_allow_html=True)

    logs = get_historical_data(plant_id=None, hours=24)
    if not logs.empty:

        def extract_status_only(ai_str):
            """Extract status + disease label from ai_status column."""
            if not ai_str or str(ai_str).strip() in ("", "nan", "N/A"):
                return ""
            s = str(ai_str).strip()
            if s == "Wait for Batch...":
                return "⏳ Pending"
            if "Quota Limit Reached" in s:
                return "⏭ Quota Skipped"
            status_m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
            if not status_m:
                return s[:40]
            status = status_m.group(1).capitalize()
            icons  = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴", "Unknown": "ℹ️"}
            label  = f"{icons.get(status, '')} {status}"
            # Show disease name if one was detected
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
            """Show a flag in logs if this row has the overall ai_summary written."""
            if not ai_summary_str or str(ai_summary_str).strip() in ("", "nan"):
                return ""
            s = str(ai_summary_str).strip()
            if not s:
                return ""
            # New format
            new_m = re.search(r'OVERALL STATUS:\s*\n?(.+)', s, re.IGNORECASE)
            if new_m:
                label = new_m.group(1).strip()
                sl = label.lower()
                if 'high' in sl:     return "🏡 🔴 High Risk"
                if 'moderate' in sl: return "🏡 ⚠️ Moderate Risk"
                if 'healthy' in sl:  return "🏡 ✅ Healthy"
                return f"🏡 {label}"
            # Old format
            m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
            if m:
                status = m.group(1).capitalize()
                icons  = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴", "Unknown": "ℹ️"}
                return f"🏡 {icons.get(status,'')} {status}"
            return "🏡 Summary"

        logs['ai_result']  = logs['ai_status'].apply(extract_status_only) \
                             if 'ai_status' in logs.columns else ""
        logs['summary_flag'] = logs['ai_summary'].apply(extract_summary_flag) \
                                if 'ai_summary' in logs.columns else ""

        display_cols = ['timestamp', 'plant_id', 'temp_c', 'humidity',
                        'soil_moisture', 'ph', 'ai_result', 'summary_flag']
        if 'image_url' in logs.columns:
            display_cols.insert(-2, 'image_url')

        cfg = {
            "timestamp":    st.column_config.TextColumn("Time"),
            "plant_id":     st.column_config.NumberColumn("Plant"),
            "temp_c":       st.column_config.NumberColumn("Temp (°C)"),
            "humidity":     st.column_config.NumberColumn("Hum (%)"),
            "soil_moisture":st.column_config.NumberColumn("Soil %"),
            "ph":           st.column_config.NumberColumn("pH"),
            "ai_result":    st.column_config.TextColumn("🤖 AI Status", width="small"),
            "summary_flag": st.column_config.TextColumn("🏡 Overall", width="small"),
            "image_url":    st.column_config.LinkColumn("📸 Image"),
        }

        display_cols = [c for c in display_cols if c in logs.columns]
        st.dataframe(
            logs[display_cols].sort_values('timestamp', ascending=False),
            column_config=cfg,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No logs available for the last 24 hours.")


# ============================================================
# PAGE: USER MANAGEMENT
# ============================================================
elif page == "USERS":
    st.markdown(
        '<div style="padding:10px; background-color:var(--secondary-background-color); border-radius:10px; margin-bottom:20px;">'
        '<div style="font-size:16px;font-weight:700;color:var(--text-color);opacity:0.7;text-transform:uppercase;">Admin Panel</div>'
        '<div style="font-size:28px;font-weight:900;color:var(--text-color);margin-top:-5px;">'
        'Registered accounts</div>'
        '</div>', unsafe_allow_html=True)

    st.table(pd.DataFrame({
        "Username": ["admin@agribot.ai", "user@agribot.ai"],
        "Role":     ["Administrator",    "Standard User"]
    }))
    st.info("Future feature: add / remove users via database.")