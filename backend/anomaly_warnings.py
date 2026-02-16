"""
Real-Time Anomaly Detection & Warning System
Uses trained model to predict anomalies and generate alerts
Saves results to timestamped text file
"""

import pandas as pd
import numpy as np
import joblib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

class AnomalyDetectionSystem:
    def __init__(self):
        """Initialize the anomaly detection system"""
        self.model = None
        self.scaler = None
        self.feature_columns = ['Temperature (°C)', 'Humidity (%)', 'pH Level']
        self.load_models()
        
    def load_models(self):
        """Load pre-trained model and scaler"""
        try:
            self.model = joblib.load('anomaly_model.pkl')
            self.scaler = joblib.load('anomaly_scaler.pkl')
            print("✓ Model and scaler loaded successfully")
        except FileNotFoundError as e:
            print(f"✗ Error: {e}")
            print("  Please run 'anomaly_detection_model.py' first to train the model")
            exit(1)
    
    def get_data_from_sheets(self):
        """Fetch latest data from Google Sheets"""
        print("\nFetching data from Google Sheets...")
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            
            spreadsheet = client.open("Agribot-AI-datasheet")
            sheet = spreadsheet.sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            print(f"✓ Fetched {len(df)} records from Google Sheets")
            return df
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def get_data_from_csv(self):
        """Fallback: Fetch data from CSV"""
        print("\nFetching data from CSV...")
        try:
            df = pd.read_csv('lettuce_dataset_updated.csv', encoding='latin-1')
            print(f"✓ Loaded {len(df)} records from CSV")
            return df
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def detect_anomalies(self, df):
        """Detect anomalies in the data"""
        # Prepare data with original info
        df_check = df[self.feature_columns + ['Plant_ID', 'Date']].copy()
        
        # Convert to numeric
        for col in self.feature_columns:
            df_check[col] = pd.to_numeric(df_check[col], errors='coerce')
        
        # Handle missing values
        df_check = df_check.dropna()
        
        # Extract features only for normalization
        X_features = df_check[self.feature_columns].values
        
        # Normalize using the training scaler
        X_normalized = self.scaler.transform(X_features)
        
        # Predict
        predictions = self.model.predict(X_normalized)
        anomaly_scores = self.model.score_samples(X_normalized)
        
        return predictions, anomaly_scores, df_check
    
    def generate_warnings(self, df, predictions, anomaly_scores):
        """Generate warning messages for detected anomalies"""
        warnings = []
        
        for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
            if pred == -1:  # Anomaly detected
                record = df.iloc[idx]
                warning = {
                    'Index': idx,
                    'Anomaly_Score': f"{score:.4f}",
                    'Temperature': f"{record['Temperature (°C)']}°C",
                    'Humidity': f"{record['Humidity (%)']}%",
                    'pH': f"{record['pH Level']}",
                    'Plant_ID': str(record.get('Plant_ID', 'Unknown')),
                    'Date': str(record.get('Date', 'Unknown'))
                }
                warnings.append(warning)
        
        return warnings
    
    def print_report(self, df, predictions, anomaly_scores, warnings, report_file=None):
        """Print a detailed report (to console and/or file)"""
        print_output = lambda msg: print(msg, file=report_file) if report_file else print(msg)
        print_both = lambda msg: (print(msg), print(msg, file=report_file) if report_file else None)
        
        report_text = []
        header = "\n" + "=" * 80
        header += f"\nANOMALY DETECTION REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        header += "\n" + "=" * 80
        
        print_both(header)
        report_text.append(header)
        
        total_records = len(predictions)
        anomaly_count = (predictions == -1).sum()
        normal_count = (predictions == 1).sum()
        anomaly_percentage = (anomaly_count / total_records) * 100
        
        summary = f"\nSummary:"
        summary += f"\n  Total Records: {total_records}"
        summary += f"\n  Normal: {normal_count} ({(normal_count/total_records)*100:.2f}%)"
        summary += f"\n  Anomalies: {anomaly_count} ({anomaly_percentage:.2f}%)"
        
        print_both(summary)
        report_text.append(summary)
        
        if warnings:
            anomaly_header = f"\n⚠️  ANOMALIES DETECTED ({len(warnings)} total):"
            anomaly_divider = "-" * 80
            print_both(anomaly_header)
            print_both(anomaly_divider)
            report_text.append(anomaly_header)
            report_text.append(anomaly_divider)
            
            for i, warning in enumerate(warnings, 1):  # Show ALL anomalies
                anomaly_detail = f"\n  [{i}] Plant ID: {warning['Plant_ID']} | Date: {warning['Date']}"
                anomaly_detail += f"\n      Temperature: {warning['Temperature']}"
                anomaly_detail += f"\n      Humidity: {warning['Humidity']}"
                anomaly_detail += f"\n      pH Level: {warning['pH']}"
                anomaly_detail += f"\n      Anomaly Score: {warning['Anomaly_Score']}"
                
                print_both(anomaly_detail)
                report_text.append(anomaly_detail)
        else:
            no_anomaly_text = f"\n✓ No anomalies detected! All readings are within normal ranges."
            print_both(no_anomaly_text)
            report_text.append(no_anomaly_text)
        
        footer = "\n" + "=" * 80
        print_both(footer)
        report_text.append(footer)
    
    def run(self):
        """Run the anomaly detection system"""
        print("\n" + "=" * 80)
        print("REAL-TIME ANOMALY WARNING SYSTEM")
        print("=" * 80)
        
        # Create timestamped report file
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_filename = f"anomaly_report_{timestamp}.txt"
        
        # Fetch data
        df = self.get_data_from_sheets()
        if df is None:
            df = self.get_data_from_csv()
        
        if df is None:
            print("✗ Failed to load data from both sources")
            return
        
        # Detect anomalies
        print("\nAnalyzing data for anomalies...")
        predictions, anomaly_scores, df_clean = self.detect_anomalies(df)
        
        # Generate warnings
        warnings = self.generate_warnings(df_clean, predictions, anomaly_scores)
        
        # Print report to console AND file
        with open(report_filename, 'w', encoding='utf-8') as f:
            self.print_report(df_clean, predictions, anomaly_scores, warnings, f)
        
        # Show file location
        abs_path = os.path.abspath(report_filename)
        print(f"\n✓ Report saved to: {report_filename}")
        print(f"  Full path: {abs_path}")

if __name__ == "__main__":
    system = AnomalyDetectionSystem()
    system.run()
