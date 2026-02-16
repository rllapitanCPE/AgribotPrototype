# 🤖 Anomaly Detection AI System - Quick Start Guide

## Overview
This system uses **Isolation Forest** (Machine Learning) to detect anomalies in:
- Temperature (°C)
- Humidity (%)
- pH Level

It's trained on your Google Sheets agricultural data and provides real-time warnings when abnormal values are detected.

---

## 📋 Files Overview

### 1. **anomaly_detection_model.py** (Training)
Trains the ML model on your historical data.

**What it does:**
- Fetches data from your Google Sheet
- Normalizes Temperature, Humidity, and pH Level
- Trains an Isolation Forest model to learn normal patterns
- Saves the trained model for later use
- Shows detection statistics

**Run it:**
```bash
python anomaly_detection_model.py
```

**Output:**
- `anomaly_model.pkl` - Trained ML model
- `anomaly_scaler.pkl` - Data normalization scaler

---

### 2. **anomaly_warnings.py** (Prediction/Warnings)
Uses the trained model to predict anomalies and generate warnings.

**What it does:**
- Loads the trained model
- Fetches latest data from Google Sheets
- Analyzes each record for anomalies
- Generates warnings with details
- Shows comprehensive report

**Run it:**
```bash
python anomaly_warnings.py
```

**Output Example:**
```
⚠️  ANOMALIES DETECTED (5 total):
  [1] Plant ID: 1 | Date: 8/10/2023
      Temperature: 22.7°C
      Humidity: 63%
      pH Level: 6.3
      Anomaly Score: -0.4521
```

---

## 🚀 Quick Start (Step by Step)

### Step 1: Train the Model
```bash
python anomaly_detection_model.py
```
Wait for it to complete. You should see:
- ✓ Data loaded
- ✓ Model trained
- ✓ Files saved

### Step 2: Run Anomaly Detection
```bash
python anomaly_warnings.py
```
The system will show all anomalies with warnings.

### Step 3: Monitor Your Data
Run `anomaly_warnings.py` whenever you want to check for anomalies in new data.

---

## 📊 How It Works

**Isolation Forest Algorithm:**
- Unsupervised learning - doesn't need labeled examples
- Effective for multidimensional data
- Fast and memory efficient
- Detects abnormal patterns automatically

**Parameters:**
- **Contamination**: 5% (assumes ~5% of data are anomalies)
- **n_estimators**: 100 trees (for accuracy)

---

## 🎨 Customization

### Change Anomaly Sensitivity
Edit `anomaly_detection_model.py`:
```python
model = IsolationForest(
    contamination=0.10,  # Change: 10% for more sensitive detection
    random_state=42,
    n_estimators=100
)
```

### Add More Features
Edit both scripts to include more columns:
```python
feature_columns = ['Temperature (°C)', 'Humidity (%)', 'pH Level', 'TDS Value (ppm)']
```

### Monitor Specific Plant IDs
Edit `anomaly_warnings.py` to filter:
```python
df = df[df['Plant_ID'] == '1']  # Only Plant 1
```

---

## ✅ Requirements Met

- ✓ Trained on Google Sheets data
- ✓ Detects anomalies in Temperature, Humidity, pH Level
- ✓ Provides warnings with details
- ✓ Easy to run and understand
- ✓ Uses professional ML algorithm

---

## 🔧 Troubleshooting

**Issue**: "credentials.json not found"
- Solution: Ensure credentials.json is in the same folder

**Issue**: "Column names don't match"
- Solution: Check spreadsheet column names match the code

**Issue**: "No anomalies detected"
- Solution: Increase contamination value (e.g., 0.10 instead of 0.05)

---

## 📝 Next Steps

1. Train your first model: `python anomaly_detection_model.py`
2. Check for anomalies: `python anomaly_warnings.py`
3. Monitor regularly or set up a scheduler to run `anomaly_warnings.py` periodically
