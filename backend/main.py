from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import random
import time
import os
import gspread
import joblib
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. LOAD LAWRENCE'S AI MODEL & SCALER
try:
    model = joblib.load('anomaly_model.pkl')
    scaler = joblib.load('anomaly_scaler.pkl')
    print("✓ Real ML Anomaly Model Loaded")
except Exception as e:
    print(f"✗ Model Error: {e}. Ensure .pkl files are in the backend folder.")
    model, scaler = None, None

# 2. GOOGLE SHEETS SETUP
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Agribot-AI-datasheet")
    sheet = spreadsheet.sheet1
    print("✓ Google Sheets Connected")
except Exception as e:
    print(f"✗ Google Sheets Error: {e}")
    sheet = None

app.mount("/images", StaticFiles(directory="mock_images"), name="images")

def run_anomaly_detection(temp, hum, ph):
    """Uses the Isolation Forest model to predict anomalies"""
    if model and scaler:
        # Prepare data for the model
        X = np.array([[temp, hum, ph]])
        X_normalized = scaler.transform(X)
        prediction = model.predict(X_normalized)[0] # 1 = Normal, -1 = Anomaly
        
        if prediction == -1:
            return "Anomaly Detected", "Warning: Environmental conditions are outside normal range!"
        return "Normal", "System conditions are stable."
    return "Simulation", "Model files missing."

@app.get("/system-data")
async def get_system_data():
    # 1. Simulate Sensor Readings
    temp = round(random.uniform(20.0, 35.0), 1)
    hum = round(random.uniform(50.0, 90.0), 1)
    ph = round(random.uniform(5.0, 8.0), 1)
    
    # 2. Run Real AI Analysis
    status, advice = run_anomaly_detection(temp, hum, ph)
    
    # 3. Pick Mock Image
    images = os.listdir("mock_images")
    selected_img = random.choice(images) if images else ""
    
    payload = {
        "sensors": {"temp": temp, "ph": ph, "humidity": hum},
        "ai_analysis": {"status": status, "image": selected_img, "advice": advice},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # 4. Upload to Google Sheets (Lawrence's Logic)
    if sheet:
        try:
            sheet.append_row([payload["timestamp"], temp, hum, ph, status])
        except:
            pass
            
    return payload

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)