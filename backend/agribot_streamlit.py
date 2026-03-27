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
# The Pi runs Gemini, writes the full structured result
# (per-plant blocks + GREENHOUSE_SUMMARY at plant_id=0)
# to the ai_status column in Google Sheets.
# Streamlit reads that column — zero Gemini quota used here.
#
# SUMMARY CHANGE: The AI Health Status panel now shows ONE
# consolidated greenhouse summary (plant_id=0 row) instead of
# per-plant cards. This gives the operator an at-a-glance
# view of overall greenhouse health + top recommendation.
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

OPTIMIZED_CSS = """
<style>
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
    width: 100% !important; font-size: 14px !important;
}
.stApp {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100vh !important;
    width: 100vw !important; max-height: 100vh !important;
}
[data-testid="stAppViewContainer"] {
    overflow: hidden !important; padding: 0 !important;
    margin: 0 !important; height: 100vh !important;
}
[data-testid="stAppViewBlockContainer"] {
    overflow: hidden !important; padding: 0 !important;
    margin: 0 !important; padding-top: 0 !important;
    height: 100vh !important; max-height: 100vh !important;
}
.main {
    margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; height: 100vh !important;
}
section.main > div {
    padding-top: 0 !important; padding-bottom: 0 !important; margin-top: 0 !important;
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
section[data-testid="stSidebar"] {
    width: 230px !important; min-width: 230px !important;
    background: #023f23 !important;
    border-right: 1px solid rgba(46,125,50,0.5) !important;
    overflow: hidden !important; height: 100vh !important; padding-top: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    display: flex !important; flex-direction: column !important;
    align-items: center !important; padding: 0 4px 4px !important;
}
[data-testid="stSidebar"] [data-testid="stElementToolbar"] { display: none !important; }
.stRadio > div {
    gap: 20px !important; width: 100% !important;
    flex-direction: column !important; margin-bottom: 8px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 16px !important; font-weight: 700 !important; color: #ffffff !important;
    letter-spacing: 0.8px !important; text-transform: uppercase !important;
    background: rgba(46,125,50,0.12) !important; border: none !important;
    border-radius: 8px !important; padding: 6px 8px !important; width: 100% !important;
    cursor: pointer !important; transition: all 0.2s !important; min-height: 44px !important;
    display: flex !important; align-items: center !important;
    margin-top: -15px !important; padding-top: 0 !important;
}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(76,175,80,0.12) !important; color: #ffffff !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"]
label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(46,125,50,0.22) !important;
    border-left: 3px solid #4CAF50 !important;
    color: #ffffff !important; padding-left: 9px !important;
}
section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    margin: 0 !important; color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button {
    font-size: 16px !important; font-weight: 700 !important; color: #ffffff !important;
    letter-spacing: 0.8px !important; text-transform: uppercase !important;
    background: rgba(46,125,50,0.12) !important; border: none !important;
    border-radius: 8px !important; padding: 6px 8px !important; width: 100% !important;
    min-height: 44px !important; transition: all 0.2s !important; margin-top: 8px !important;
    cursor: pointer !important; display: flex !important;
    align-items: center !important; justify-content: center !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(198,40,40,0.15) !important;
    border-color: rgba(198,40,40,0.5) !important; color: #ffffff !important;
}
div[data-testid="stMetric"] {
    background: #023f23 !important; border: 1px solid rgba(76,175,80,0.3) !important;
    border-radius: 10px !important; padding: 8px 6px !important; text-align: center !important;
}
div[data-testid="stMetricLabel"] {
    font-weight: 700 !important; font-size: 11px !important; color: #66bb6a !important;
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    justify-content: center !important;
}
div[data-testid="stMetricValue"] {
    font-size: 24px !important; font-weight: 900 !important;
    color: #fff !important; margin-top: 1px !important;
}
.cam-card {
    background: rgba(13,17,23,0.9); border: 1px solid rgba(46,125,50,0.4);
    border-radius: 12px; padding: 10px; height: 100%;
}
.section-title {
    font-size: 12px !important; font-weight: 700 !important; color: #66bb6a !important;
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    margin-bottom: 15px !important; margin-top: 0 !important;
    border-left: 3px solid #4CAF50; padding-left: 7px;
}
.alert-item {
    padding: 6px 10px; background: rgba(183,28,28,0.12);
    border: 1px solid rgba(183,28,28,0.3); color: #ef9a9a;
    border-radius: 8px; margin: 10px 0; font-size: 13px !important;
}
.sched-badge {
    display: inline-block; background: rgba(21,101,192,0.2);
    border: 1px solid rgba(21,101,192,0.5); border-radius: 5px;
    padding: 2px 6px; font-size: 10px !important; color: #90CAF9;
    font-weight: 700; margin: 0 2px;
}
.cam-meta {
    font-size: 10px !important; color: #66bb6a; margin-top: 15px; line-height: 1.5;
}
.drive-link {
    display: inline-block; margin-top: 5px; background: rgba(46,125,50,0.15);
    border: 1px solid rgba(76,175,80,0.3); border-radius: 7px; padding: 4px 10px;
    color: #81c784; font-size: 11px !important; text-decoration: none;
}
.cam-placeholder {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 200px; background: rgba(46,125,50,0.04);
    border: 2px dashed rgba(46,125,50,0.3); border-radius: 10px;
    text-align: center; padding: 20px;
}
.ph-badge {
    display: inline-block; border-radius: 6px; padding: 2px 10px;
    font-size: 10px !important; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; margin-left: 6px; vertical-align: middle;
}
.ph-acidic   { background: rgba(239,83,80,0.18);  border: 1px solid rgba(239,83,80,0.5);  color: #ef9a9a; }
.ph-neutral  { background: rgba(76,175,80,0.18);  border: 1px solid rgba(76,175,80,0.5);  color: #81c784; }
.ph-alkaline { background: rgba(66,165,245,0.18); border: 1px solid rgba(66,165,245,0.5); color: #90CAF9; }
.ph-metric-wrap {
    background: #023f23; border: 1px solid rgba(76,175,80,0.3);
    border-radius: 10px; padding: 8px 6px; text-align: center;
}
.ph-metric-label {
    font-weight: 700; font-size: 11px; color: #66bb6a;
    letter-spacing: 1.2px; text-transform: uppercase;
}
.ph-metric-value {
    font-size: 24px; font-weight: 900; color: #fff; margin-top: 1px;
}
.js-plotly-plot, .plotly, .plot-container { max-height: 210px !important; }
[data-testid="stPlotlyChart"] { height: 210px !important; overflow: hidden !important; }
[data-testid="stDataFrame"] {
    max-height: 300px !important; overflow-y: auto !important; font-size: 13px !important;
}
[data-testid="stAlert"] {
    padding: 8px 12px !important; font-size: 13px !important;
    border-radius: 8px !important; margin: 4px 0 !important;
}
[data-testid="stSelectbox"] { margin-bottom: 4px !important; }
[data-baseweb="select"] { min-height: 42px !important; }
.stSelectbox label { font-size: 12px !important; color: #66bb6a !important; margin-bottom: 2px !important; }
.stTextInput label { color: #c8e6c9 !important; font-weight: 600 !important; font-size: 13px !important; }
.landing-btn-wrapper button {
    background: linear-gradient(135deg, #2e7d32, #66bb6a) !important;
    border: 2px solid rgba(255,255,255,0.3) !important; border-radius: 50px !important;
    color: white !important; font-size: 24px !important; font-weight: 700 !important;
    padding: 14px 48px !important; cursor: pointer !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    min-height: 64px !important; transition: transform 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important; width: auto !important;
}
.landing-btn-wrapper button:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 12px 32px rgba(76,175,80,0.7) !important;
}
.landing-page section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stForm"] {
    background: linear-gradient(160deg,
        rgba(27,94,32,0.65) 0%, rgba(46,125,50,0.55) 100%) !important;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 18px; border: 1px solid rgba(165,214,167,0.35);
    box-shadow: 0 12px 40px rgba(0,0,0,0.35); padding: 26px 36px 34px !important;
}
[data-testid="stForm"] input {
    background: rgba(255,255,255,0.1) !important; color: #fff !important;
    border: 1px solid rgba(165,214,167,0.45) !important; border-radius: 10px !important;
    font-size: 16px !important; min-height: 48px !important;
}
[data-testid="stForm"] input::placeholder { color: rgba(200,230,200,0.6) !important; }
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(90deg, #2e7d32, #66bb6a) !important;
    border: none !important; color: #fff !important; font-weight: 700 !important;
    border-radius: 10px !important; letter-spacing: 1.5px; font-size: 16px !important;
    padding: 12px !important; min-height: 52px !important; margin-top: 4px !important;
}
@keyframes pulse {
    0%,100% { box-shadow: 0 0 5px #4CAF50; }
    50%      { box-shadow: 0 0 14px #4CAF50; opacity: 0.7; }
}
[data-testid="column"] { height: 100%; padding: 0 4px !important; }
.main .block-container { display: flex; flex-direction: column; overflow: hidden; }
.main .block-container > [data-testid="stVerticalBlock"] { flex: 1; overflow: hidden; }
[data-testid="stImage"] { margin-top: 0 !important; margin-bottom: 0 !important; }
[data-testid="stImage"] img {
    border-radius: 8px !important; max-height: 260px !important;
    object-fit: cover !important; width: 100% !important;
}
/* Greenhouse summary card */
.gh-summary-card {
    border-radius: 11px; padding: 12px 14px; margin: 4px 0 8px;
    font-size: 11px; line-height: 1.8;
}
.gh-summary-healthy  { background: rgba(46,125,50,0.18);  border: 1px solid #81c784; }
.gh-summary-warning  { background: rgba(230,81,0,0.18);   border: 1px solid #ffb74d; }
.gh-summary-critical { background: rgba(183,28,28,0.18);  border: 1px solid #ef9a9a; }
.gh-summary-pending  { background: rgba(33,33,33,0.35);   border: 1px solid #555; }
.gh-summary-unknown  { background: rgba(21,101,192,0.12); border: 1px solid #90CAF9; }
/* plant tally pills */
.tally-pill {
    display: inline-block; border-radius: 20px; padding: 2px 10px;
    font-size: 10px; font-weight: 700; margin: 0 3px; letter-spacing: 0.5px;
}
.tally-healthy  { background: rgba(46,125,50,0.3);  border:1px solid #81c784; color:#81c784; }
.tally-warning  { background: rgba(230,81,0,0.3);   border:1px solid #ffb74d; color:#ffb74d; }
.tally-critical { background: rgba(183,28,28,0.3);  border:1px solid #ef9a9a; color:#ef9a9a; }
/* SMS sent badge */
.sms-sent-badge {
    display: inline-block; background: rgba(21,101,192,0.25);
    border: 1px solid #90CAF9; border-radius: 4px;
    padding: 1px 6px; font-size: 9px; color: #90CAF9; font-weight: 700;
    margin-left: 6px; vertical-align: middle; letter-spacing: 0.5px;
}
.sms-no-badge {
    display: inline-block; background: rgba(66,66,66,0.25);
    border: 1px solid #888; border-radius: 4px;
    padding: 1px 6px; font-size: 9px; color: #aaa; font-weight: 700;
    margin-left: 6px; vertical-align: middle;
}
</style>
"""
st.markdown(OPTIMIZED_CSS, unsafe_allow_html=True)


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
        expected = ['timestamp', 'plant_id', 'temp_c', 'humidity',
                    'soil_moisture', 'ph', 'image_url', 'ai_status']
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
# GREENHOUSE SUMMARY PARSER
# Reads the plant_id=0 row written by the Pi after every batch
# ============================================================
def parse_greenhouse_summary_from_sheets(ai_status_str: str) -> dict:
    """
    Parses the consolidated GREENHOUSE_SUMMARY block stored at plant_id=0.

    Expected Sheets format:
        Overall Status: Warning
        Plants Healthy: 5
        Plants Warning: 2
        Plants Critical: 1
        Key Issues:
          - Soil moisture low in plants 3 and 6
          - pH slightly elevated across all plants
        Overall Recommendation:
          Increase irrigation frequency for plants 3 and 6 immediately...
        SMS Sent: Yes

    Returns:
        {
          'overall_status'  : str,
          'plants_healthy'  : int,
          'plants_warning'  : int,
          'plants_critical' : int,
          'key_issues'      : [str, ...],
          'recommendation'  : str,
          'sms_sent'        : "Yes" | "No" | "N/A",
          'timestamp'       : str,   # filled in by caller
        }
    or {} if unparseable / {'__pending__': True} if wait state.
    """
    if not ai_status_str or str(ai_status_str).strip() in ("", "nan", "N/A"):
        return {}

    s = str(ai_status_str).strip()

    if s == "Wait for Batch...":
        return {"__pending__": True}

    def _find(pattern, default="N/A"):
        m = re.search(pattern, s, re.IGNORECASE)
        return m.group(1).strip() if m else default

    result = {}
    result['overall_status']  = _find(r'Overall Status:\s*(Healthy|Warning|Critical|Unknown)', "Unknown")
    result['plants_healthy']  = int(_find(r'Plants Healthy:\s*(\d+)', "0"))
    result['plants_warning']  = int(_find(r'Plants Warning:\s*(\d+)', "0"))
    result['plants_critical'] = int(_find(r'Plants Critical:\s*(\d+)', "0"))

    # Key Issues bullet list
    issues_m = re.search(r'Key Issues:\s*\n([\s\S]+?)(?=Overall Recommendation:|\Z)', s)
    key_issues = []
    if issues_m:
        for line in issues_m.group(1).splitlines():
            line = line.strip().lstrip('- ').strip()
            if line and line.lower() != "none":
                key_issues.append(line)
    result['key_issues'] = key_issues

    # Overall Recommendation (multi-line)
    rec_m = re.search(r'Overall Recommendation:\s*\n([\s\S]+?)(?=\nSMS Sent:|\Z)', s)
    if rec_m:
        rec_lines = [ln.lstrip() for ln in rec_m.group(1).splitlines() if ln.strip()]
        result['recommendation'] = " ".join(rec_lines)
    else:
        result['recommendation'] = "N/A"

    sms_m = re.search(r'SMS Sent:\s*(Yes|No)', s, re.IGNORECASE)
    result['sms_sent'] = sms_m.group(1).capitalize() if sms_m else "N/A"

    return result


def render_greenhouse_summary_panel(df: pd.DataFrame):
    """
    Renders the consolidated 🏡 Greenhouse AI Summary panel.

    Reads the most recent plant_id=0 row (written by Pi after every batch).
    Shows: overall status, plant tally, key issues, and the operator recommendation.
    Falls back gracefully if no summary row exists yet.
    """
    if df.empty or 'ai_status' not in df.columns:
        st.info("📋 No AI summary yet — waiting for next camera session.")
        return

    # Isolate plant_id=0 rows (greenhouse summary rows)
    summary_df = df[df['plant_id'] == 0].copy()

    if summary_df.empty:
        # No summary row exists yet — show a helpful note
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 Greenhouse summary not available yet.<br><br>'
            'The Pi will write a consolidated summary after the next scheduled '
            'camera session (7:00 AM, 12:00 NN, or 5:00 PM).'
            '</div>', unsafe_allow_html=True)
        return

    # Most recent summary row
    latest_summary_row = summary_df.sort_values('timestamp').iloc[-1]
    raw_ai = str(latest_summary_row['ai_status']).strip()
    ts     = pd.to_datetime(latest_summary_row['timestamp']).strftime("%b %d, %Y · %I:%M %p")

    parsed = parse_greenhouse_summary_from_sheets(raw_ai)

    if not parsed:
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 No AI summary yet — waiting for next camera session.'
            '</div>', unsafe_allow_html=True)
        return

    # Pending state
    if parsed.get("__pending__"):
        st.markdown(
            '<div class="gh-summary-card gh-summary-pending" style="color:#aaa;">'
            '🕒 AI analyzing batch... greenhouse summary will appear after all plants are captured.'
            '</div>', unsafe_allow_html=True)
        return

    status = parsed.get('overall_status', 'Unknown')
    color_map = {
        "Healthy":  ("#81c784", "gh-summary-healthy",  "✅"),
        "Warning":  ("#ffb74d", "gh-summary-warning",  "⚠️"),
        "Critical": ("#ef9a9a", "gh-summary-critical", "🔴"),
        "Unknown":  ("#90CAF9", "gh-summary-unknown",  "ℹ️"),
    }
    txt_c, css_cls, icon = color_map.get(status, ("#90CAF9", "gh-summary-unknown", "ℹ️"))

    sms_sent = parsed.get('sms_sent', 'N/A')
    sms_html = (
        '<span class="sms-sent-badge">📨 SMS SENT</span>'
        if sms_sent == "Yes" else
        '<span class="sms-no-badge">SMS: N/A</span>'
    )

    h = parsed['plants_healthy']
    w = parsed['plants_warning']
    c = parsed['plants_critical']

    tally_html = (
        f'<span class="tally-pill tally-healthy">✅ {h} Healthy</span>'
        f'<span class="tally-pill tally-warning">⚠️ {w} Warning</span>'
        f'<span class="tally-pill tally-critical">🔴 {c} Critical</span>'
    )

    issues = parsed.get('key_issues', [])
    if issues:
        issues_html = "".join(
            f'<div style="color:#ffcc80;font-size:10px;margin:1px 0;">• {i}</div>'
            for i in issues
        )
    else:
        issues_html = '<div style="color:#81c784;font-size:10px;">• No major issues detected</div>'

    rec = parsed.get('recommendation', 'N/A')

    st.markdown(
        f'<div class="gh-summary-card {css_cls}">'

        # Header
        f'<div style="font-weight:900;color:{txt_c};font-size:13px;'
        f'margin-bottom:7px;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">'
        f'{icon} Overall Greenhouse Status: <b>{status}</b>{sms_html}'
        f'<span style="font-size:9px;color:#888;font-weight:400;margin-left:6px;">{ts}</span>'
        f'</div>'

        # Plant tally pills
        f'<div style="margin-bottom:8px;">{tally_html}</div>'

        # Key Issues
        f'<div style="margin-bottom:8px;padding-bottom:7px;'
        f'border-bottom:1px solid rgba(255,255,255,0.08);">'
        f'<div style="font-size:10px;font-weight:700;color:#a5d6a7;'
        f'letter-spacing:0.5px;margin-bottom:3px;">KEY ISSUES</div>'
        f'{issues_html}'
        f'</div>'

        # Overall Recommendation
        f'<div>'
        f'<div style="font-size:10px;font-weight:700;color:#66bb6a;'
        f'letter-spacing:0.5px;margin-bottom:3px;">OVERALL RECOMMENDATION</div>'
        f'<div style="font-size:10px;color:#e8f5e9;line-height:1.7;">{rec}</div>'
        f'</div>'

        f'</div>',
        unsafe_allow_html=True)


def parse_per_plant_ai_from_sheets(ai_str: str) -> dict:
    """
    Parses a per-plant ai_status block (plant_id 1-8) written by the Pi.
    Returns a dict with status, image finding, recommendation, etc.
    """
    if not ai_str or str(ai_str).strip() in ("", "nan", "N/A", "Analyzing..."):
        return {}
    s = str(ai_str).strip()

    def _find(pattern, default="N/A"):
        m = re.search(pattern, s, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    status_m = re.search(r'Status:\s*(Healthy|Warning|Critical|Unknown)', s, re.IGNORECASE)
    status   = status_m.group(1).capitalize() if status_m else "Unknown"

    image_finding = _find(r'Image\s*:\s*(.+)')
    soil_finding  = _find(r'Soil Moisture\s*:\s*(.+)')
    rec_m = re.search(r'Recommendation:\s*\n([\s\S]+?)(?:\nSMS Sent:|\Z)', s)
    rec   = " ".join(ln.strip() for ln in rec_m.group(1).splitlines() if ln.strip()) if rec_m else "N/A"
    sms_m = re.search(r'SMS Sent:\s*(Yes|No)', s, re.IGNORECASE)
    sms   = sms_m.group(1).capitalize() if sms_m else "N/A"

    return {
        'status':        status,
        'image_finding': image_finding,
        'soil_finding':  soil_finding,
        'recommendation': rec,
        'sms_sent':      sms,
    }


def render_per_plant_ai_cards(df: pd.DataFrame):
    """
    Renders compact per-plant AI analysis cards below the main dashboard panels.
    Each card shows: Plant #, status badge, image finding, recommendation.
    Only shown when AI data is available (after a camera session).
    """
    if df.empty or 'ai_status' not in df.columns:
        return

    plant_df = df[df['plant_id'] > 0].copy()
    if plant_df.empty:
        return

    # Get most recent ai_status per plant that has actual AI data
    plant_df = plant_df[
        plant_df['ai_status'].notna() &
        ~plant_df['ai_status'].isin(["", "nan", "N/A", "Analyzing...", "Wait for Batch..."])
    ]
    if plant_df.empty:
        return

    latest_ai = plant_df.sort_values('timestamp').groupby('plant_id').last().reset_index()
    # Only plants 1-8 with actual parsed data
    cards = []
    for _, row in latest_ai.iterrows():
        parsed = parse_per_plant_ai_from_sheets(str(row.get('ai_status', '')))
        if parsed:
            parsed['plant_id'] = int(row['plant_id'])
            parsed['timestamp'] = pd.to_datetime(row['timestamp']).strftime("%H:%M")
            cards.append(parsed)

    if not cards:
        return

    st.markdown('<div class="section-title" style="margin-top:10px;">🌱 Per-Plant AI Analysis</div>',
                unsafe_allow_html=True)

    # 4 per row
    cols_per_row = 4
    for i in range(0, len(cards), cols_per_row):
        row_cards = cards[i:i + cols_per_row]
        cols = st.columns(len(row_cards))
        for col, card in zip(cols, row_cards):
            status = card.get('status', 'Unknown')
            color_map = {
                "Healthy":  ("#81c784", "rgba(46,125,50,0.18)",  "✅"),
                "Warning":  ("#ffb74d", "rgba(230,81,0,0.18)",   "⚠️"),
                "Critical": ("#ef9a9a", "rgba(183,28,28,0.18)",  "🔴"),
                "Unknown":  ("#90CAF9", "rgba(21,101,192,0.12)", "❓"),
            }
            txt_c, bg_c, icon = color_map.get(status, ("#90CAF9", "rgba(21,101,192,0.12)", "❓"))
            img_f = card.get('image_finding', 'N/A')
            rec   = card.get('recommendation', 'N/A')
            rec_short = rec[:90] + "..." if len(rec) > 90 else rec
            pid   = card.get('plant_id', '?')
            ts    = card.get('timestamp', '')

            with col:
                st.markdown(
                    f'<div style="background:{bg_c};border:1px solid {txt_c}33;'
                    f'border-radius:9px;padding:8px 10px;margin-bottom:6px;">'
                    f'<div style="font-weight:900;color:{txt_c};font-size:11px;'
                    f'margin-bottom:4px;display:flex;justify-content:space-between;">'
                    f'<span>{icon} Plant {pid}</span>'
                    f'<span style="font-size:9px;color:#666;font-weight:400;">{ts}</span>'
                    f'</div>'
                    f'<div style="font-size:10px;color:#ccc;margin-bottom:3px;">'
                    f'<b style="color:#a5d6a7;">Img:</b> {img_f}</div>'
                    f'<div style="font-size:10px;color:#e8f5e9;line-height:1.5;">'
                    f'<b style="color:#66bb6a;">Rec:</b> {rec_short}</div>'
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
        st.markdown("<div style='margin-top: 30vh;'></div>", unsafe_allow_html=True)
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
    """Latest sensor readings per plant (excludes plant_id=0 summary rows)."""
    if sheet is None:
        return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty:
        return df
    # Exclude plant_id=0 (greenhouse summary rows)
    df = df[df['plant_id'] > 0]
    return df.sort_values('timestamp').groupby('plant_id').last().reset_index()


@st.cache_data(ttl=60)
def get_historical_data(plant_id=None, hours=24):
    if sheet is None:
        return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty:
        return df
    # Exclude summary rows
    df = df[df['plant_id'] > 0]
    df = df[df['timestamp'] >= datetime.now() - timedelta(hours=hours)]
    if plant_id is not None:
        df = df[df['plant_id'] == plant_id]
    return df.sort_values('timestamp')


@st.cache_data(ttl=30)
def get_greenhouse_summary_row() -> pd.DataFrame:
    """
    Returns the most recent plant_id=0 row (greenhouse summary) from Sheets.
    This is the consolidated AI result written by the Pi after each batch.
    """
    if sheet is None:
        return pd.DataFrame()
    df = safe_read_sheet(sheet)
    if df.empty or 'ai_status' not in df.columns:
        return pd.DataFrame()
    summary_df = df[df['plant_id'] == 0].copy()
    if summary_df.empty:
        return pd.DataFrame()
    return summary_df.sort_values('timestamp').tail(1)


@st.cache_data(ttl=30)
def get_latest_plant_image() -> dict:
    if sheet is None:
        return {}
    df = safe_read_sheet(sheet)
    if df.empty or 'image_url' not in df.columns:
        return {}
    df = df[df['plant_id'] > 0]  # Exclude summary rows
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
        '<div style="padding:6px 12px 2px;">'
        '<div style="font-size:20px;font-weight:900;color:#fff;line-height:1.2;">'
        'Real-Time Monitoring</div>'
        '<div style="font-size:20px;color:#66bb6a;letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        'Greenhouse Overview — AgriBot-AI</div>'
        '</div>', unsafe_allow_html=True)

    if latest.empty:
        st.warning("No sensor data yet — waiting for the Pi...")
        st.stop()

    avg_temp = float(latest['temp_c'].mean())
    avg_hum  = float(latest['humidity'].mean())
    avg_ph   = float(latest['ph'].mean())
    avg_soil = float(latest['soil_moisture'].mean())

    # ── Metric cards ──────────────────────────────────────────
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

    # ── Plant Health Feed ─────────────────────────────────────
    with cam_col:
        st.markdown('<div style="margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📷 Plant Health Feed</div>',
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

            pid_txt = f"🥬 Plant {img_data['plant_id']}" if img_data.get("plant_id") else ""
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

    # ── Right column: AI Greenhouse Summary + Alerts ──────────
    with right_col:
        if not latest.empty:
            last_ts = pd.to_datetime(latest['timestamp']).max()
            st.markdown(
                f'<div style="text-align:right;font-size:9px;color:#388e3c;'
                f'margin-bottom:6px;">🔄 {last_ts.strftime("%H:%M:%S")}</div>',
                unsafe_allow_html=True)

        # 🤖 Consolidated Greenhouse AI Summary
        st.markdown('<div class="section-title">🤖 AI Greenhouse Summary</div>',
                    unsafe_allow_html=True)

        gh_summary_df = get_greenhouse_summary_row()
        # Pass full sheet data so render function can find plant_id=0 rows
        all_df = safe_read_sheet(sheet) if sheet else pd.DataFrame()
        render_greenhouse_summary_panel(all_df)

    # ── Per-Plant AI Analysis cards (full width below camera + summary) ──
    all_df_for_plants = safe_read_sheet(sheet) if sheet else pd.DataFrame()
    render_per_plant_ai_cards(all_df_for_plants)




# ============================================================
# PAGE: ANALYSIS
# ============================================================
elif page == "ANALYSIS":
    st.markdown(
        '<div style="padding:6px 12px 4px;">'
        '<div style="font-size:18px;font-weight:900;color:#fff;">Historical Trends</div>'
        '<div style="font-size:20px;color:#66bb6a;letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        'Sensor data over time</div></div>',
        unsafe_allow_html=True)

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
            "Select Plant", list(range(1, 11)),
            format_func=lambda x: f"Plant {x}")
        hist_df = get_historical_data(plant_id=plant_sel, hours=hours)
        chart_title = f"Soil Moisture — Plant {plant_sel}"

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
        '<div style="padding:6px 12px 4px;">'
        '<div style="font-size:18px;font-weight:900;color:#fff;">System Logs</div>'
        '<div style="font-size:20px;color:#66bb6a;letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        'Last 24 hours</div></div>',
        unsafe_allow_html=True)

    logs = get_historical_data(plant_id=None, hours=24)
    if not logs.empty:
        def extract_sms_sent(ai_str):
            if not ai_str or str(ai_str).strip() in ("", "nan", "N/A", "Wait for Batch..."):
                return ""
            m = re.search(r'SMS Sent:\s*(Yes|No)', str(ai_str), re.IGNORECASE)
            return "📨 Yes" if (m and m.group(1).lower() == "yes") else ""

        def extract_status_only(ai_str):
            if not ai_str or str(ai_str).strip() in ("", "nan", "N/A"):
                return ""
            if str(ai_str).strip() == "Wait for Batch...":
                return "⏳ Pending"
            # Check for greenhouse summary (plant_id=0 rows)
            m_overall = re.search(r'Overall Status:\s*(Healthy|Warning|Critical)', str(ai_str), re.IGNORECASE)
            if m_overall:
                s = m_overall.group(1).capitalize()
                icons = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴"}
                return f"🏡 {icons.get(s,'')} {s} (Summary)"
            m = re.search(r'Status:\s*(Healthy|Warning|Critical)', str(ai_str), re.IGNORECASE)
            if m:
                s = m.group(1).capitalize()
                icons = {"Healthy": "✅", "Warning": "⚠️", "Critical": "🔴"}
                return f"{icons.get(s, '')} {s}"
            return str(ai_str)[:40]

        logs['ai_result']  = logs['ai_status'].apply(extract_status_only) if 'ai_status' in logs.columns else ""
        logs['sms_status'] = logs['ai_status'].apply(extract_sms_sent)    if 'ai_status' in logs.columns else ""

        display_cols = ['timestamp', 'plant_id', 'temp_c', 'humidity',
                        'soil_moisture', 'ph', 'ai_result', 'sms_status']
        if 'image_url' in logs.columns:
            display_cols.insert(-3, 'image_url')

        cfg = {
            "timestamp":     st.column_config.TextColumn("Time"),
            "plant_id":      st.column_config.NumberColumn("Plant"),
            "temp_c":        st.column_config.NumberColumn("Temp (°C)"),
            "humidity":      st.column_config.NumberColumn("Hum (%)"),
            "soil_moisture": st.column_config.NumberColumn("Soil %"),
            "ph":            st.column_config.NumberColumn("pH"),
            "ai_result":     st.column_config.TextColumn("🤖 AI Status", width="small"),
            "sms_status":    st.column_config.TextColumn("📨 SMS", width="small"),
            "image_url":     st.column_config.LinkColumn("📸 Image"),
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
        '<div style="padding:6px 12px 4px;">'
        '<div style="font-size:18px;font-weight:900;color:#fff;">Admin Panel</div>'
        '<div style="font-size:20px;color:#66bb6a;letter-spacing:1px;margin-top:-75px;font-weight:bold;">'
        'Registered accounts</div></div>',
        unsafe_allow_html=True)

    st.table(pd.DataFrame({
        "Username": ["admin@agribot.ai", "user@agribot.ai"],
        "Role":     ["Administrator",    "Standard User"]
    }))
    st.info("Future feature: add / remove users via database.")
