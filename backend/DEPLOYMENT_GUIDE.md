# 🤖 Complete AI Anomaly Detection System - Deployment Guide

## 📊 System Overview

Your AI/ML system is now ready to detect anomalies in agricultural sensor data!

### What It Does:
✅ **Trains** on your Google Sheets historical data  
✅ **Detects** abnormal Temperature, Humidity, and pH readings  
✅ **Warns** you immediately when anomalies are found  
✅ **Analyzes** single readings in real-time  
✅ **Exports** detailed reports to CSV  

---

## 📁 Files Created

| File | Purpose | Run When |
|------|---------|----------|
| **anomaly_detection_model.py** | Trains the ML model | First time setup or when retraining |
| **anomaly_warnings.py** | Full dataset analysis & warnings | Regular monitoring, check all data |
| **anomaly_utility.py** | Single reading analysis | Real-time sensor checks |
| **anomaly_model.pkl** | Trained ML model (binary) | Auto-loaded by other scripts |
| **anomaly_scaler.pkl** | Data normalizer (binary) | Auto-loaded by other scripts |

---

## 🚀 Step-by-Step Usage

### **STEP 1: Train the Model** (Do this once)
```bash
python anomaly_detection_model.py
```

**Output:**
- Loads 3169+ records from Google Sheets
- Trains Isolation Forest model
- Detects ~5% anomalies automatically
- Saves `anomaly_model.pkl` and `anomaly_scaler.pkl`

**Expected Results:**
```
Total records: 3169
Normal records: 3010 (94.98%)
Anomalies detected: 159 (5.02%)
```

---

### **STEP 2: Check All Data for Anomalies**
```bash
python anomaly_warnings.py
```

**Output:**
- Analyzes all records in your Google Sheet
- Lists each anomaly with details:
  - Plant ID & Date
  - Temperature, Humidity, pH values
  - Anomaly Score (lower = more anomalous)
- Shows statistical summary

**Example Output:**
```
⚠️  ANOMALIES DETECTED (159 total):

[1] Plant ID: 2 | Date: 8/4/2023
    Temperature: 33.5°C
    Humidity: 65%
    pH Level: 6.8
    Anomaly Score: -0.6012
```

---

### **STEP 3: Analyze Single Readings (Real-Time)**
```bash
python anomaly_utility.py check <temperature> <humidity> <ph> [plant_id] [date]
```

**Examples:**

Normal reading:
```bash
python anomaly_utility.py check 32 65 6.4 Plant1 2023-08-01

✓ NORMAL READING
Anomaly Score: -0.4801
```

Anomalous reading:
```bash
python anomaly_utility.py check 20 50 6.0 Plant5 2023-09-09

⚠️ ANOMALY DETECTED!
Anomaly Score: -0.6587
```

---

## 🔄 Recommended Workflow

### Daily Monitoring
```bash
# Morning check
python anomaly_warnings.py

# When new sensor readings come in
python anomaly_utility.py check <temp> <humidity> <ph> <plant_id> <date>
```

### Weekly Deep Analysis
```bash
# Sunday evening - full dataset review
python anomaly_warnings.py > weekly_report.txt
```

### Monthly Retraining (When you have significant new data)
```bash
python anomaly_detection_model.py
python anomaly_warnings.py
```

---

## 📈 Understanding the Results

### Anomaly Score Explanation:
- **Score > -0.2**: Normal reading (safe)
- **-0.2 to -0.5**: Unusual but acceptable (monitor)
- **< -0.5**: Anomaly detected (investigate!)

### What Counts as Anomalous:
Based on training, these combinations are abnormal:
- **Very high temperature** (33.5°C) + **normal humidity** (65%)
- **Low temperature** (20°C) + **low humidity** (50%)
- **Edge cases** in pH (6.0 or 6.8) with extreme temps/humidity

---

## 🛠️ Customization Guide

### Adjust Sensitivity (Detect More/Fewer Anomalies)

**More sensitive** (catch more anomalies):
```python
# In anomaly_detection_model.py, change:
contamination=0.10  # From 0.05 (detect 10% instead of 5%)
```

**Less sensitive** (fewer false alarms):
```python
contamination=0.02  # Only mark top 2% as anomalies
```

Then retrain:
```bash
python anomaly_detection_model.py
```

### Add More Features

To also monitor TDS Value or Growth Days:
```python
# In both scripts, change:
feature_columns = [
    'Temperature (°C)', 
    'Humidity (%)', 
    'pH Level',
    'TDS Value (ppm)',  # Add this
    'Growth Days'        # Add this
]
```

Then retrain with new features.

### Monitor Specific Plants

```python
# In anomaly_warnings.py, after fetching data:
df = df[df['Plant_ID'] == '1']  # Only Plant 1
```

---

## 📊 Integration Examples

### Integrate with Raspberry Pi/Arduino
```python
# Send sensor reading, get warning
import subprocess
import json

temp, humidity, ph = 32.1, 68.5, 6.4

result = subprocess.run([
    'python', 'anomaly_utility.py', 'check',
    str(temp), str(humidity), str(ph)
], capture_output=True, text=True)

if 'ANOMALY DETECTED' in result.stdout:
    # Trigger alarm, send email, etc.
    send_alert("Abnormal reading detected!")
```

### Schedule Automatic Checks
**Windows Task Scheduler:**
```
Task: Check Anomalies Daily
Action: python "C:\path\to\anomaly_warnings.py"
Schedule: Daily at 8:00 AM
```

**Linux/Mac (Cron):**
```bash
0 8 * * * cd /path/to/folder && python anomaly_warnings.py >> anomaly_log.txt
```

---

## 🔧 Troubleshooting

### Problem: "Model not found"
**Solution:** Run training first
```bash
python anomaly_detection_model.py
```

### Problem: "credentials.json not found"
**Solution:** Ensure credentials.json is in the same folder as scripts

### Problem: Column name errors
**Solution:** Update column names in scripts to match your Google Sheet exactly

### Problem: No anomalies detected
**Solution:** Decrease contamination value in training script:
```python
contamination=0.10  # Instead of 0.05
```

### Problem: Too many false alarms
**Solution:** Increase contamination value:
```python
contamination=0.02  # Instead of 0.05
```

---

## 📈 Performance Metrics

**Current Model Status:**
- ✅ Training data: 3,169 records
- ✅ Accuracy: Unsupervised (no labeled data needed)
- ✅ Features: 3 (Temperature, Humidity, pH)
- ✅ Anomalies detected: ~159 (5%)
- ✅ Response time: <1 second per reading

---

## 🎓 How It Works (Technical)

**Algorithm: Isolation Forest**
- Unsupervised learning (doesn't need labeled anomalies)
- Isolates anomalies by randomly selecting features
- Normal points require more splits to isolate
- Anomalies isolate quickly → detected!

**Why Isolation Forest?**
- ✅ Excellent for multivariate data (3+ features)
- ✅ Doesn't assume data distribution
- ✅ Fast and memory efficient
- ✅ No training labels needed
- ✅ Detects both global and local anomalies

---

## 📞 Next Steps

1. ✅ Run training once: `python anomaly_detection_model.py`
2. ✅ Check your data: `python anomaly_warnings.py`
3. ✅ Test with sensors: `python anomaly_utility.py check 32 65 6.4`
4. 📅 Set up daily monitoring (Task Scheduler or Cron)
5. 📊 Review weekly and adjust sensitivity as needed

---

## 📚 References

- [Isolation Forest Paper](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08.pdf)
- [scikit-learn Documentation](https://scikit-learn.org/)
- [Google Sheets API](https://developers.google.com/sheets/api)

---

**System Ready! Start monitoring anomalies now! 🎉**
