"""
Anomaly Detection Model Training Script
Trains an Isolation Forest ML model to detect anomalies in:
- Temperature (°C)
- Humidity (%)
- pH Level
"""

import pandas as pd
import numpy as np
import gspread
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from oauth2client.service_account import ServiceAccountCredentials

print("=" * 60)
print("ANOMALY DETECTION MODEL TRAINING")
print("=" * 60)

# 1. AUTHENTICATION & DATA FETCH FROM GOOGLE SHEETS
print("\n1. Authenticating with Google Sheets...")
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

try:
    spreadsheet = client.open("Agribot-AI-datasheet")
    sheet = spreadsheet.sheet1
    data = sheet.get_all_records()
    print(f"✓ Successfully fetched {len(data)} records from Google Sheets")
except Exception as e:
    print(f"✗ Error fetching from Google Sheets: {e}")
    print("  Falling back to CSV file...")
    df = pd.read_csv('lettuce_dataset_updated.csv', encoding='latin-1')
else:
    df = pd.DataFrame(data)

# 2. DATA PREPROCESSING
print("\n2. Preprocessing data...")

# Select the features for anomaly detection
feature_columns = ['Temperature (°C)', 'Humidity (%)', 'pH Level']

# Create a copy for preprocessing
df_anomaly = df[feature_columns].copy()

# Convert to numeric (in case there are any string values)
for col in feature_columns:
    df_anomaly[col] = pd.to_numeric(df_anomaly[col], errors='coerce')

# Remove rows with missing values
initial_rows = len(df_anomaly)
df_anomaly = df_anomaly.dropna()
print(f"✓ Cleaned data: {initial_rows} rows → {len(df_anomaly)} rows (removed {initial_rows - len(df_anomaly)} rows with missing values)")

# Check data statistics
print("\n3. Data Statistics:")
print("-" * 60)
print(df_anomaly.describe())

# 4. NORMALIZE THE DATA
print("\n4. Normalizing features...")
scaler = StandardScaler()
X_normalized = scaler.fit_transform(df_anomaly)
print("✓ Features normalized using StandardScaler")

# 5. TRAIN ISOLATION FOREST MODEL
print("\n5. Training Isolation Forest model...")
print("   Parameters:")
print("   - Contamination: 0.05 (assumes ~5% of data are anomalies)")
print("   - Random State: 42 (for reproducibility)")

model = IsolationForest(
    contamination=0.05,  # Assume ~5% of data are anomalies
    random_state=42,
    n_estimators=100
)

model.fit(X_normalized)

# Get predictions (1 = normal, -1 = anomaly)
predictions = model.predict(X_normalized)
anomaly_count = (predictions == -1).sum()
anomaly_percentage = (anomaly_count / len(predictions)) * 100

print(f"✓ Model trained successfully!")
print(f"  Total records: {len(predictions)}")
print(f"  Normal records: {(predictions == 1).sum()}")
print(f"  Anomalies detected: {anomaly_count} ({anomaly_percentage:.2f}%)")

# 6. SAVE MODEL AND SCALER
print("\n6. Saving model and scaler...")
joblib.dump(model, 'anomaly_model.pkl')
joblib.dump(scaler, 'anomaly_scaler.pkl')
print("✓ Model saved as 'anomaly_model.pkl'")
print("✓ Scaler saved as 'anomaly_scaler.pkl'")

# 7. SHOW SAMPLE ANOMALIES
print("\n7. Sample Anomalies Detected:")
print("-" * 60)
anomalies_mask = predictions == -1
if anomalies_mask.any():
    anomaly_samples = df_anomaly[anomalies_mask].head(10)
    print(anomaly_samples.to_string())
else:
    print("No anomalies detected in the dataset (adjust contamination parameter if needed)")

print("\n" + "=" * 60)
print("TRAINING COMPLETE!")
print("Next: Run 'anomaly_warnings.py' for real-time predictions")
print("=" * 60)
