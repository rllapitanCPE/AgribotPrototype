from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import random
import time
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# This line is NEW: It tells the app where your images are stored
# Make sure the folder 'backend/mock_images' exists!
if not os.path.exists("mock_images"):
    os.makedirs("mock_images")

app.mount("/images", StaticFiles(directory="mock_images"), name="images")

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
    
    return {
        "sensors": {
            "temp": temp,
            "ph": ph,
            "humidity": hum
        },
        "ai_analysis": ai_report,
        "timestamp": time.strftime("%H:%M:%S")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)