# Quick Start Guide - Plant Sensor Monitoring System

Get your system running in 5 minutes!

## Installation (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the Flask Server (Terminal 1)
```bash
python app.py
```

You should see:
```
✓ Server starting on http://localhost:5000
✓ Dashboard: http://localhost:5000/
```

### Step 3: Send Test Data (Terminal 2)

**Option A: Run the Sensor Script with Mock Data**
```bash
python raspberry_pi_sensor.py
```

**Option B: Send Manual Test Data**
```bash
# Terminal command (Linux/Mac)
curl -X POST http://localhost:5000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"temperature": 23.5, "humidity": 65.0, "ph": 6.8, "plant_id": "Plant-1"}'

# PowerShell (Windows)
$body = @{temperature=23.5; humidity=65.0; ph=6.8; plant_id="Plant-1"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/api/sensor-data" `
  -Method POST -Body $body -ContentType "application/json"
```

### Step 4: Open Dashboard
Open your browser and go to:
```
http://localhost:5000
```

## That's It! ✓

Your dashboard should now show:
- ✓ Current readings
- ✓ Live charts
- ✓ System statistics
- ✓ Anomaly alerts (if data is anomalous)

---

## File Structure

```
project/
├── app.py                      # Flask web server
├── raspberry_pi_sensor.py      # Sensor reading script
├── requirements.txt            # Python dependencies
├── setup_instructions.md       # Complete setup guide
├── QUICK_START.md             # This file
├── anomaly_model.pkl          # Pre-trained model (if available)
├── anomaly_scaler.pkl         # Model scaler (if available)
├── templates/
│   └── index.html             # Web dashboard
└── static/
    └── styles.css             # CSS styling
```

---

## Next: Configure for Real Sensors

Edit `raspberry_pi_sensor.py` and uncomment the sensor you're using:

### Option 1: DHT22 + pH Sensor
```python
def collect_sensor_data():
    temp, humidity = read_dht22_sensor(pin=17)
    ph = read_ph_sensor(adc_pin=0)
    if temp is None or humidity is None or ph is None:
        return None, None, None
    return temp, humidity, ph
```

### Option 2: LM35 + DHT22
```python
def collect_sensor_data():
    temp = read_lm35_sensor(adc_pin=0)
    humidity, _ = read_dht22_sensor(pin=17)
    ph = read_ph_sensor(adc_pin=1)
    # ... rest of function
```

Then uncomment the corresponding imports and install sensor libraries:
```bash
pip install Adafruit-DHT
pip install adafruit-circuitpython-ads1x15
```

---

## Connect to Raspberry Pi

Change the server URL in `raspberry_pi_sensor.py`:

```python
# Find this line:
SERVER_URL = "http://localhost:5000"

# Change to your server's IP:
SERVER_URL = "http://192.168.1.100:5000"
```

Find your server IP:
```bash
# Linux/Mac
ifconfig | grep "inet "

# Windows PowerShell
ipconfig | findstr IPv4
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't access dashboard | Check if server is running: `python app.py` |
| "Connection refused" | Firewall blocking port 5000. Try port 5001 |
| Mock data stops | Sensor script crashed. Check error message and restart |
| No anomalies detected | Model files missing (optional). System uses basic detection |
| Old readings in memory | Click "Clear Data" on dashboard or restart server |

---

## API Endpoints

```
POST   /api/sensor-data    - Send sensor reading
GET    /api/latest         - Get latest reading
GET    /api/history        - Get reading history
GET    /api/stats          - Get statistics
POST   /api/clear          - Clear all data
```

---

## Dashboard Features

- 🌡️ **Temperature** - Current, min, max, average
- 💧 **Humidity** - Current, min, max, average  
- ⚗️ **pH Level** - Current, min, max, average
- 📊 **Live Charts** - Real-time trends
- 🚨 **Anomaly Alerts** - When data is unusual
- 📈 **Statistics** - Total readings, anomaly count
- 🔄 **Auto-refresh** - Updates every 2 seconds

---

## For More Information

See `setup_instructions.md` for:
- Understanding the system architecture
- Detailed wiring diagrams for sensors
- Sensor calibration procedures
- Multi-plant monitoring setup
- Security considerations
- Performance optimization

---

**Ready to monitor your plants? Start with `python app.py` and open http://localhost:5000!** 🌱
