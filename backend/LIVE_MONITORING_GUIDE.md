# 🌱 Live Plant Monitoring System - Complete Guide

## 📊 System Overview

Your complete monitoring system is now ready! Here's how it all works together:

```
Raspberry Pi Sensors
   (DHT22, LM35, pH)
         ↓
   HTTP POST Request
         ↓
   Flask Web Server (app.py)
         ↓
   AI Anomaly Detection Model
         ↓
   Real-time Web Dashboard
         ↓
   Live Charts & Alerts
```

---

## 🚀 Quick Start (5 Minutes)

### **Step 1: Install Dependencies**
```bash
cd "c:\Users\ASUS ROG\Documents\Visual Studio\file for test"
pip install -r requirements.txt
```

### **Step 2: Start the Flask Server**
```bash
python app.py
```

Expected output:
```
PLANT MONITORING WEB SERVER
✓ Models loaded successfully
✓ Flask server starting...
Access the web interface at: http://localhost:5000
```

### **Step 3: Open the Web Dashboard**
- Open your browser and go to: **http://localhost:5000**
- You'll see a beautiful live monitoring dashboard

### **Step 4: Send Test Data (Optional)**
Open another terminal and run:
```bash
python raspberry_pi_sensor.py
```

This sends simulated sensor data to the server. Each reading will be processed through your AI model and displayed on the dashboard!

---

## 📁 Files Created

### **Backend**
- **app.py** - Flask web server with API endpoints
- **requirements.txt** - Python dependencies
- **anomaly_model.pkl** - Your trained AI model (used by app.py)
- **anomaly_scaler.pkl** - Data normalizer (used by app.py)

### **Raspberry Pi**
- **raspberry_pi_sensor.py** - Script to run on Raspberry Pi
- Collects sensor data every 10 seconds
- Sends data to Flask server via HTTP

### **Frontend**
- **templates/index.html** - Interactive web dashboard
- **static/styles.css** - Modern styling

### **Documentation**
- **setup_instructions.md** - Detailed setup guide
- **QUICK_START.md** - Quick reference

---

## 🔌 API Endpoints

Your Flask server provides 5 API endpoints:

| Endpoint | Method | Purpose | Example |
|----------|--------|---------|---------|
| `/` | GET | Web dashboard | http://localhost:5000 |
| `/api/sensor-data` | POST | Send sensor reading | See below |
| `/api/latest` | GET | Get latest readings | http://localhost:5000/api/latest |
| `/api/history` | GET | Get reading history | http://localhost:5000/api/history?plant_id=1 |
| `/api/stats` | GET | Get statistics | http://localhost:5000/api/stats |
| `/api/clear` | POST | Clear all data | POST to endpoint |

### **Send Sensor Data (POST)**

From your Raspberry Pi or any device:

```bash
curl -X POST http://localhost:5000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "plant_id": "1",
    "temperature": 32.5,
    "humidity": 65.3,
    "ph": 6.4,
    "timestamp": "2026-02-16T12:30:45"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Data received and processed",
  "result": {
    "is_anomaly": false,
    "anomaly_score": -0.4521,
    "status": "NORMAL"
  }
}
```

### **Get Latest Readings (GET)**

```bash
curl http://localhost:5000/api/latest
```

**Response:**
```json
{
  "success": true,
  "data": {
    "1": {
      "plant_id": "1",
      "temperature": 32.5,
      "humidity": 65.3,
      "ph": 6.4,
      "timestamp": "2026-02-16T12:30:45",
      "is_anomaly": false,
      "status": "NORMAL"
    }
  }
}
```

---

## 🌐 Web Dashboard Features

When you open **http://localhost:5000**, you'll see:

### **1. Statistics Section**
- Total readings received
- Anomalies detected
- Anomaly percentage
- Last update time

### **2. Current Readings Cards**
- **Temperature**: Current, Min, Max, Average
- **Humidity**: Current, Min, Max, Average
- **pH Level**: Current, Min, Max, Average
- **System Status**: Shows connection and processing status

### **3. Live Charts**
- Temperature trend over time
- Humidity trend over time
- pH Level trend over time
- Charts auto-update every 2 seconds

### **4. Anomaly Alerts**
- Shows any readings flagged as anomalies
- Displays timestamp and anomaly score
- Color-coded: Green (Normal), Red (Anomaly)

### **5. Control Buttons**
- Refresh data manually
- Clear all data

---

## 🌱 Setting Up Raspberry Pi

### **Configure the Sensor Script**

Edit `raspberry_pi_sensor.py` and set:

```python
FLASK_SERVER_URL = "http://192.168.1.100:5000"  # Your server IP
PLANT_ID = "1"                                   # Plant identifier
SEND_INTERVAL = 10                              # Seconds between readings
```

### **Choose Your Sensors**

The script supports multiple sensor types. Uncomment the sensor you're using:

**Option 1: DHT22 (Temperature & Humidity)**
```python
import Adafruit_DHT
sensor = Adafruit_DHT.DHT22
pin = 4  # GPIO pin
humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
```

**Option 2: LM35 (Analog Temperature)**
```python
# Uses ADC (ADS1115) to read analog voltage
voltage = channel.voltage
temperature = voltage * 100  # LM35: 10mV per degree
```

**Option 3: pH Sensor (Analog)**
```python
# Uses ADC to read pH level
voltage = channel.voltage
pH = 7 + (2.5 - voltage) / 0.18  # Calibrated formula
```

**Option 4: BME280 (All-in-one)**
```python
import adafruit_bme280.advanced as adafruit_bme280
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
temperature = bme280.temperature
humidity = bme280.humidity
```

---

## 🔧 Deployment Options

### **Local Testing (Windows/Mac/Linux)**
```bash
python app.py  # Flask server
# In another terminal:
python raspberry_pi_sensor.py  # Test data sender
# Open: http://localhost:5000
```

### **Raspberry Pi + Server**
1. **On your server PC/Mac/Linux:**
   ```bash
   python app.py
   ```

2. **On Raspberry Pi:**
   ```bash
   python raspberry_pi_sensor.py
   ```

3. Open dashboard from any device: **http://<server-ip>:5000**

### **Docker Deployment (Optional)**
Create a `Dockerfile` file for easy deployment across machines.

---

## 📊 Monitoring Multiple Plants

Monitor multiple plants in the same dashboard!

**Raspberry Pi 1 (Plant A):**
```python
PLANT_ID = "Plant_A"  # Unique ID
FLASK_SERVER_URL = "http://192.168.1.100:5000"
```

**Raspberry Pi 2 (Plant B):**
```python
PLANT_ID = "Plant_B"  # Different ID
FLASK_SERVER_URL = "http://192.168.1.100:5000"  # Same server
```

Each plant sends data to the same server, and the dashboard displays all of them!

---

## 🎨 Dashboard Colors & Meanings

| Color | Status | Meaning |
|-------|--------|---------|
| **Green** | ✓ NORMAL | Reading is within normal range |
| **Red** | ⚠️ ANOMALY | Unusual reading detected |
| **Blue** | 🔄 UPDATING | Data is being refreshed |
| **Orange** | ⚠️ WARNING | Minor issues |

---

## 🔍 Understanding Anomaly Scores

When your AI model checks a reading, it gives an "Anomaly Score":

- **Score > -0.2**: Normal ✅ (Safe)
- **-0.2 to -0.5**: Unusual ⚠️ (Monitor)
- **< -0.5**: Anomaly 🚨 (Alert)

Lower scores = more anomalous. Your model was trained to recognize patterns based on your historical data.

---

## 🚨 Viewing Anomalies

### **In Web Dashboard**
- Anomaly Alerts section shows flagged readings
- Red background indicates anomalous data
- Click for more details

### **In Terminal**
When running `app.py`, you'll see logs like:
```
[2026-02-16 12:30:45] Plant 1: Temp=32.5°C, Humidity=65.3%, pH=6.4 - NORMAL
[2026-02-16 12:31:00] Plant 1: Temp=20.0°C, Humidity=50.0%, pH=6.0 - ANOMALY
```

---

## 📈 Data Storage

- Last **100 readings** stored in memory
- When server restarts, data is cleared
- For permanent storage, integrate with database (see below)

---

## 🗄️ Adding Database Storage (Optional)

To save data permanently, modify `app.py`:

```python
import sqlite3

# After receiving data
def save_to_database(reading):
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO readings (plant_id, temperature, humidity, pH, timestamp, is_anomaly)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (reading['plant_id'], reading['temperature'], reading['humidity'], 
          reading['pH'], reading['timestamp'], reading['is_anomaly']))
    conn.commit()
    conn.close()
```

---

## 🔒 Security Considerations

- **Local Network**: Current setup is fine for local use
- **Production**: Add authentication (Flask-Login)
- **Data**: Use HTTPS instead of HTTP
- **Firewall**: Only allow trusted Raspberry Pis

---

## ❌ Troubleshooting

### **"Server not responding"**
- Check Flask server is running: `python app.py`
- Check firewall isn't blocking port 5000
- Try: `curl http://localhost:5000/api/test`

### **"Models not loaded"**
- Ensure `anomaly_model.pkl` and `anomaly_scaler.pkl` exist
- Check file permissions
- Run from correct directory

### **"No data on dashboard"**
- Check `raspberry_pi_sensor.py` is running
- Check for error messages in Flask terminal
- Try sending test data manually with curl

### **"Can't connect from another device"**
- Change `FLASK_SERVER_URL` to your server's IP, not localhost
- Check firewall allows port 5000
- Example: `http://192.168.1.100:5000`

---

## 🎯 Next Steps

1. ✅ Start Flask server: `python app.py`
2. ✅ Open dashboard: http://localhost:5000
3. ✅ Run sensor script: `python raspberry_pi_sensor.py`
4. 🔧 Configure actual Raspberry Pi sensors
5. 📊 Monitor your plants in real-time!

---

## 📞 Summary of Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask web server
python app.py

# Run sensor data collector (another terminal)
python raspberry_pi_sensor.py

# Test API
curl http://localhost:5000/api/latest
curl http://localhost:5000/api/stats

# View logs
# Check Flask terminal for [Plant X: Temp=... Status=...]
```

---

**Your complete live monitoring system is ready! 🎉**

Start with Step 1 above and you'll have real-time plant monitoring with AI anomaly detection!
