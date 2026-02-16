from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random
import time

app = FastAPI()

# This allows your Frontend to talk to your Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/system-data")
async def get_sensor_data():
    # In Phase 4, we will replace these random numbers 
    # with real data from your RPi sensors
    temp = round(random.uniform(22.0, 30.0), 1)
    hum = round(random.uniform(60.0, 80.0), 0)
    ph = round(random.uniform(5.0, 7.5), 1)
    
    # Logic for Recommendations based on your Thesis thresholds
    recommendation = "Optimal conditions."
    status = "Stable"
    
    if ph < 5.5:
        recommendation = "pH too acidic. Add pH Up."
        status = "Warning"
    elif ph > 6.5:
        recommendation = "pH too alkaline. Add pH Down."
        status = "Warning"
    
    return {
        "temperature": temp,
        "humidity": hum,
        "ph_level": ph,
        "recommendation": recommendation,
        "status": status,
        "timestamp": time.strftime("%H:%M:%S")
    }

# To run this, you will eventually use: uvicorn main:app --reload