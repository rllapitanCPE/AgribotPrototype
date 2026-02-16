# Plant Sensor Monitoring System - Setup Guide

Complete setup guide for the web-based live monitoring system for plant sensors connected to a Raspberry Pi.

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Connecting Sensors](#connecting-sensors)
6. [Running the System](#running-the-system)
7. [Testing the API](#testing-the-api)
8. [Accessing the Frontend](#accessing-the-frontend)
9. [Troubleshooting](#troubleshooting)

---

## System Overview

The Plant Sensor Monitoring System consists of:

1. **Flask Web Server** (`app.py`)
   - Receives sensor data via HTTP POST requests
   - Runs anomaly detection on incoming readings
   - Stores last 100 readings in memory
   - Serves the interactive web dashboard

2. **Raspberry Pi Sensor Script** (`raspberry_pi_sensor.py`)
   - Reads from temperature, humidity, and pH sensors every 10 seconds
   - Sends data to the Flask server
   - Handles connection errors gracefully
   - Works with DHT22, LM35, and pH sensors

3. **Web Dashboard** (`templates/index.html`)
   - Real-time sensor readings display
   - Interactive charts showing trends
   - Anomaly alerts
   - System statistics
   - Auto-refreshes every 2 seconds

4. **Anomaly Detection** (using pre-trained model)
   - Uses your existing `anomaly_model.pkl` and `anomaly_scaler.pkl`
   - Detects unusual sensor patterns
   - Scores anomalies on a 0-1 scale

---

## Prerequisites

### Server Requirements

- **Python 3.7+**
- Flask web framework
- NumPy (for data processing)

### Raspberry Pi Requirements

- **Python 3.7+**
- Raspberry Pi OS (Debian-based)
- Network connection to the server
- GPIO pins for sensor connections

### Sensors (Optional - for real sensor data)

- **DHT22** - Temperature and Humidity sensor
- **LM35** - Temperature sensor (analog)
- **pH Sensor** - Soil/Water pH measurement
- **ADC Converter** - ADS1115 for analog sensors (optional)

---

## Installation

### Step 1: Install Python Dependencies on Server

```bash
# Install Flask
pip install flask

# Install NumPy
pip install numpy

# Install requests (for testing)
pip install requests

# Or install all at once
pip install flask numpy requests
```

### Step 2: Verify Anomaly Detection Files

Make sure these files are in the same directory as `app.py`:

```
anomaly_model.pkl
anomaly_scaler.pkl
```

If these files don't exist, the system will fall back to basic rule-based anomaly detection.

### Step 3: Copy Flask App Files

Ensure the following file structure is created:

```
project_directory/
├── app.py                    # Flask server
├── anomaly_model.pkl         # Pre-trained model (if available)
├── anomaly_scaler.pkl        # Model scaler (if available)
├── templates/
│   └── index.html           # Web dashboard
└── static/
    └── styles.css           # CSS styling
```

### Step 4: Install Raspberry Pi Dependencies (Optional)

On your Raspberry Pi, install sensor libraries:

```bash
# For DHT22 sensor
pip install Adafruit-DHT

# For ADS1115 ADC (for analog sensors like pH, LM35)
pip install adafruit-circuitpython-ads1x15
pip install adafruit-circuitpython-busio
pip install adafruit-circuitpython-digitalio

# For requests
pip install requests
```

---

## Configuration

### Server Configuration (`app.py`)

Edit the configuration constants at the top of `app.py`:

```python
MAX_READINGS = 100      # Number of readings to keep in memory
PORT = 5000            # Server port (change if needed)
```

### Raspberry Pi Configuration (`raspberry_pi_sensor.py`)

Edit the configuration section:

```python
# Server URL - Change to your server's IP/hostname
SERVER_URL = "http://192.168.1.100:5000"

# How often to read sensors (seconds)
SENSOR_READ_INTERVAL = 10

# Plant identifier for multi-plant monitoring
PLANT_ID = "Plant-1"

# Connection retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2
```

#### Setting the Server URL

Replace `localhost` with your actual server address:

**For local network:**
```python
SERVER_URL = "http://192.168.1.100:5000"  # Replace with your server's IP
```

**For Raspberry Pi running on same computer:**
```python
SERVER_URL = "http://localhost:5000"
```

**For cloud-hosted server:**
```python
SERVER_URL = "https://yourdomain.com"
```

---

## Connecting Sensors

### Option 1: DHT22 (Temperature & Humidity)

**Wiring:**
```
DHT22 Pin 1 (VCC)    → 3.3V
DHT22 Pin 2 (DATA)   → GPIO 17 (or any GPIO pin)
DHT22 Pin 4 (GND)    → GND
```

**Using in code:**
```python
def collect_sensor_data():
    temp, humidity = read_dht22_sensor(pin=17)
    ph = read_ph_sensor(adc_pin=0)
    return temp, humidity, ph
```

### Option 2: LM35 (Temperature via ADC)

**Wiring (to ADS1115 ADC):**
```
LM35 Vcc (pin 1)  → 5V
LM35 Out (pin 2)  → A0 (ADS1115 input)
LM35 GND (pin 3)  → GND

ADS1115 SCL → GPIO 3
ADS1115 SDA → GPIO 2
```

**Using in code:**
```python
def collect_sensor_data():
    temp = read_lm35_sensor(adc_pin=0)
    humidity, _ = read_dht22_sensor(pin=17)
    ph = read_ph_sensor(adc_pin=1)
    return temp, humidity, ph
```

### Option 3: pH Sensor (via ADC)

**Wiring (to ADS1115 ADC):**
```
pH Sensor Output → A1 (ADS1115 input)
ADS1115 SCL → GPIO 3
ADS1115 SDA → GPIO 2
```

**Calibration:**
pH sensors require calibration with known pH buffers:

1. Prepare pH 6.86 and pH 9.18 buffer solutions
2. Read the voltage at each pH
3. Update the conversion formula in `read_ph_sensor()`

---

## Running the System

### Step 1: Start the Flask Server

On your server machine:

```bash
# Navigate to the project directory
cd /path/to/project

# Run the Flask app
python app.py
```

You should see output like:
```
============================================================
Plant Sensor Monitoring System - Flask Server
============================================================

✓ Anomaly detection model loaded from anomaly_model.pkl
✓ Scaler loaded from anomaly_scaler.pkl

✓ Server starting on http://localhost:5000
✓ Dashboard: http://localhost:5000/
✓ API: http://localhost:5000/api/sensor-data

Press Ctrl+C to stop the server
```

### Step 2: Configure Sensors

Edit `raspberry_pi_sensor.py` to enable your sensors. Choose ONE of these options:

**Option A: Use Real DHT22 + pH Sensors**
```python
def collect_sensor_data():
    temp, humidity = read_dht22_sensor(pin=17)
    ph = read_ph_sensor(adc_pin=0)
    if temp is None or humidity is None or ph is None:
        return None, None, None
    return temp, humidity, ph
```

**Option B: Use Mock Data (Testing)**
```python
def collect_sensor_data():
    return read_mock_sensors()
```

### Step 3: Start Sensor Reading Script

On the Raspberry Pi (or second terminal):

```bash
# Navigate to the project directory
cd /path/to/project

# Run the sensor script
python raspberry_pi_sensor.py
```

You should see output like:
```
======================================================================
Raspberry Pi Sensor Data Collection System
======================================================================
Server URL: http://192.168.1.100:5000
Plant ID: Plant-1
Read interval: 10 seconds
Retries on failure: 3

Starting sensor collection... (Press Ctrl+C to stop)

[2026-02-16 10:30:45] Reading sensors...
  Temperature: 22.45°C
  Humidity:    65.30%
  pH:          6.85
✓ Data sent successfully - Status: NORMAL
```

---

## Testing the API

### Test 1: Send Single Reading

```bash
curl -X POST http://localhost:5000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 23.5,
    "humidity": 65.0,
    "ph": 6.8,
    "plant_id": "Plant-1"
  }'
```

Expected response:
```json
{
  "success": true,
  "status": "NORMAL",
  "anomaly_score": 0.15
}
```

### Test 2: Get Latest Reading

```bash
curl http://localhost:5000/api/latest
```

### Test 3: Get Reading History

```bash
# Get all readings
curl http://localhost:5000/api/history

# Get last 10 readings
curl http://localhost:5000/api/history?limit=10

# Get readings for specific plant
curl http://localhost:5000/api/history?plant_id=Plant-1
```

### Test 4: Get Statistics

```bash
curl http://localhost:5000/api/stats
```

Expected response:
```json
{
  "total_readings": 42,
  "anomaly_count": 2,
  "anomaly_percentage": 4.76,
  "temperature": {
    "current": 23.5,
    "avg": 22.8,
    "min": 20.2,
    "max": 25.1
  },
  "humidity": {
    "current": 65.0,
    "avg": 63.4,
    "min": 58.2,
    "max": 72.1
  },
  "ph": {
    "current": 6.8,
    "avg": 6.75,
    "min": 6.4,
    "max": 7.1
  },
  "last_reading_time": "2026-02-16T10:30:45.123456"
}
```

### Test 5: Using Python

```python
import requests
import json

# Send sensor data
data = {
    'temperature': 24.0,
    'humidity': 68.0,
    'ph': 6.9,
    'plant_id': 'Plant-1'
}

response = requests.post(
    'http://localhost:5000/api/sensor-data',
    json=data
)

print(response.json())

# Get statistics
stats = requests.get('http://localhost:5000/api/stats').json()
print(f"Total readings: {stats['total_readings']}")
print(f"Anomalies: {stats['anomaly_count']}")
```

---

## Accessing the Frontend

### Open the Dashboard

Once the server is running, open your web browser and navigate to:

```
http://localhost:5000
```

Or from another computer:

```
http://192.168.1.100:5000
```

### Dashboard Features

The dashboard displays:

1. **Current Readings**
   - Temperature, Humidity, pH
   - Min, Max, Average values
   - Current status (NORMAL/ANOMALY)

2. **Live Charts**
   - Temperature trends
   - Humidity trends
   - pH trends

3. **Statistics**
   - Total readings count
   - Number of anomalies detected
   - Anomaly percentage

4. **Alerts**
   - Recent anomalies with timestamps
   - Anomaly scores

5. **Auto-refresh**
   - Updates every 2 seconds
   - Shows connection status

### Mobile Access

The dashboard is fully responsive and works on:
- Smartphones
- Tablets
- Laptops
- Any modern web browser

---

## Troubleshooting

### Issue 1: "Connection refused" Error

**Problem:** Flask server not responding

**Solutions:**
```bash
# Check if server is running
ps aux | grep python

# Check if port is in use
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Try different port in app.py
PORT = 5001
```

### Issue 2: Raspberry Pi Can't Connect to Server

**Problem:** `Connection error (attempt 1/3)`

**Solutions:**

1. Check network connectivity:
```bash
ping 192.168.1.100  # Ping the server
```

2. Verify server URL:
```python
# In raspberry_pi_sensor.py
SERVER_URL = "http://192.168.1.100:5000"  # Use correct IP
```

3. Check firewall:
```bash
# On server machine
sudo ufw allow 5000  # Linux
```

### Issue 3: "Anomaly model not loaded"

**Problem:** Model files missing

**Solutions:**

1. Ensure files exist in the project directory:
```bash
ls anomaly_model.pkl anomaly_scaler.pkl
```

2. The system will fall back to basic anomaly detection if files are missing

### Issue 4: Sensors Not Reading Data

**Problem:** `None, None, None` from sensors

**Solutions:**

1. Check sensor wiring
2. Install required libraries:
```bash
pip install Adafruit-DHT
pip install adafruit-circuitpython-ads1x15
```

3. Test individual sensors:
```python
python -c "from raspberry_pi_sensor import read_dht22_sensor; print(read_dht22_sensor(17))"
```

4. Use mock data for testing:
```python
def collect_sensor_data():
    return read_mock_sensors()  # Remove sensors code temporarily
```

### Issue 5: Old Data in Memory

**Problem:** Want to clear history

**Solutions:**

1. Using API:
```bash
curl -X POST http://localhost:5000/api/clear
```

2. Click "Clear Data" button on dashboard

3. Restart Flask server

### Issue 6: High Anomaly Rate

**Problem:** False positives from anomaly detection

**Solutions:**

1. Check sensor calibration
2. Verify expected ranges in code:
```python
# Basic ranges in anomaly detection
Temperature: 0-50°C
Humidity: 0-100%
pH: 4.0-9.0
```

3. Retrain model with more diverse data

---

## Performance Tips

### For Better Response Times

1. **Reduce Reading Frequency** (if not needed)
```python
SENSOR_READ_INTERVAL = 30  # Read every 30 seconds instead of 10
```

2. **Limit Dashboard Update**
```javascript
// In index.html, change interval from 2000ms to higher
updateInterval = setInterval(updateDashboard, 5000);
```

3. **Use Network Connection Efficiently**
- Batch multiple readings before sending
- Increase request timeout for slow connections

### For Multi-Plant Monitoring

Monitor multiple plants by changing the `plant_id`:

```python
# Raspberry Pi script
for plant in ['Plant-1', 'Plant-2', 'Plant-3']:
    temperature, humidity, ph = collect_sensor_data()
    send_sensor_data(temperature, humidity, ph, plant_id=plant)
```

Query specific plant on dashboard:
```
/api/history?plant_id=Plant-1
/api/stats?plant_id=Plant-1
```

---

## Security Considerations

For production deployment:

1. **Use HTTPS**
```python
# Install pyopenssl
pip install pyopenssl

# Run with SSL
app.run(ssl_context='adhoc')
```

2. **Add Authentication**
```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@app.route('/api/sensor-data', methods=['POST'])
@auth.login_required
def receive_sensor_data():
    # ...
```

3. **Rate Limiting**
```python
pip install flask-limiter
```

4. **Enable CORS for specific domains**
```python
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "192.168.1.*"}})
```

---

## Next Steps

1. **Integrate with InfluxDB** for long-term data storage
2. **Add Email Alerts** for anomalies
3. **Create Data Export** to CSV/JSON
4. **Set up Logging** for debugging
5. **Deploy to Cloud** (AWS, Azure, Heroku)

---

## Support & Resources

- Flask Documentation: https://flask.palletsprojects.com/
- Raspberry Pi Guides: https://www.raspberrypi.org/documentation/
- DHT22 Documentation: https://learn.adafruit.com/dht/overview
- Chart.js Documentation: https://www.chartjs.org/docs/latest/

---

**Last Updated:** February 2026  
**System Version:** 1.0
