from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import random
import time
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
for folder in ["mock_images", "logs"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/images", StaticFiles(directory="mock_images"), name="images")

LOG_FILE = "logs/sensor_history.json"

def log_data(data):
    """Saves sensor readings to a JSON file for thesis analysis"""
    history = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                history = json.load(f)
            except:
                history = []
    
    history.append(data)
    # Keep only the last 100 readings to save space
    if len(history) > 100:
        history.pop(0)
        
    with open(LOG_FILE, "w") as f:
        json.dump(history, f, indent=4)

def simulate_ai_analysis():
    outcomes = [
        {"status": "Healthy", "image": "healthy.jpg", "advice": "No action needed. Plants are thriving."},
        {"status": "Leaf Spot Detected", "image": "sick.jpg", "advice": "Fungal infection risk! Check humidity."},
        {"status": "Yellowing Leaves", "image": "yellow.jpg", "advice": "Nutrient deficiency. Check pH levels."}
    ]
    return random.choice(outcomes)

@app.get("/system-data")
async def get_system_data():
    temp = round(random.uniform(22.0, 29.0), 1)
    ph = round(random.uniform(5.0, 7.5), 1)
    hum = round(random.uniform(60, 80), 0)
    
    ai_report = simulate_ai_analysis()
    
    payload = {
        "sensors": {
            "temp": temp,
            "ph": ph,
            "humidity": hum
        },
        "ai_analysis": ai_report,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save to 'database'
    log_data(payload)
    
    return payload

# New endpoint to see the history
@app.get("/history")
async def get_history():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)