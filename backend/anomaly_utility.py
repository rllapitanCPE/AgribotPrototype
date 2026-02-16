"""
Advanced Anomaly Detection Utility
- Analyze single sensor readings
- Export warnings to CSV
- Continuous monitoring mode
"""

import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import csv
import sys

class AnomalyDetector:
    def __init__(self):
        """Initialize detector"""
        try:
            self.model = joblib.load('anomaly_model.pkl')
            self.scaler = joblib.load('anomaly_scaler.pkl')
            self.feature_columns = ['Temperature (°C)', 'Humidity (%)', 'pH Level']
        except FileNotFoundError:
            print("✗ Model files not found. Run anomaly_detection_model.py first.")
            exit(1)
    
    def check_single_reading(self, temperature, humidity, ph_level):
        """Analyze a single sensor reading"""
        # Create array
        X = np.array([[temperature, humidity, ph_level]])
        
        # Normalize
        X_normalized = self.scaler.transform(X)
        
        # Predict
        prediction = self.model.predict(X_normalized)[0]
        score = self.model.score_samples(X_normalized)[0]
        
        return prediction, score
    
    def analyze_reading(self, temperature, humidity, ph_level, plant_id="Unknown", date="Unknown"):
        """Detailed analysis of a reading"""
        prediction, score = self.check_single_reading(temperature, humidity, ph_level)
        
        print("\n" + "=" * 70)
        print(f"SENSOR READING ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print(f"\nInput Data:")
        print(f"  Plant ID: {plant_id}")
        print(f"  Date: {date}")
        print(f"  Temperature: {temperature}°C")
        print(f"  Humidity: {humidity}%")
        print(f"  pH Level: {ph_level}")
        
        print(f"\nAnalysis Result:")
        if prediction == -1:
            print(f"  ⚠️  ANOMALY DETECTED!")
            print(f"  Anomaly Score: {score:.4f} (lower = more anomalous)")
            print(f"\n  Explanation:")
            print(f"  This reading differs significantly from normal patterns.")
            print(f"  Investigate possible causes.")
        else:
            print(f"  ✓ NORMAL READING")
            print(f"  Anomaly Score: {score:.4f} (normal values closer to 0)")
            print(f"\n  Explanation:")
            print(f"  This reading is within expected parameters.")
        
        print("\n" + "=" * 70)
        return prediction, score

def interactive_mode():
    """Interactive command-line mode"""
    detector = AnomalyDetector()
    
    print("\n" + "=" * 70)
    print("INTERACTIVE ANOMALY DETECTION")
    print("=" * 70)
    print("Commands:")
    print("  'check' - Analyze a single reading")
    print("  'batch' - Analyze multiple readings from file")
    print("  'exit' - Exit program")
    print("=" * 70)
    
    while True:
        command = input("\nEnter command: ").strip().lower()
        
        if command == 'exit':
            print("Goodbye!")
            break
        
        elif command == 'check':
            try:
                plant_id = input("Plant ID: ").strip()
                date = input("Date: ").strip()
                temp = float(input("Temperature (°C): "))
                humidity = float(input("Humidity (%): "))
                ph = float(input("pH Level: "))
                
                detector.analyze_reading(temp, humidity, ph, plant_id, date)
            except ValueError:
                print("✗ Invalid input. Please enter numbers for sensor values.")
        
        elif command == 'batch':
            filename = input("CSV filename (with Plant_ID, Date, Temperature (°C), Humidity (%), pH Level): ").strip()
            try:
                df = pd.read_csv(filename)
                results = []
                
                for idx, row in df.iterrows():
                    temp = float(row['Temperature (°C)'])
                    humidity = float(row['Humidity (%)'])
                    ph = float(row['pH Level'])
                    
                    pred, score = detector.check_single_reading(temp, humidity, ph)
                    
                    results.append({
                        'Plant_ID': row.get('Plant_ID', 'Unknown'),
                        'Date': row.get('Date', 'Unknown'),
                        'Temperature': temp,
                        'Humidity': humidity,
                        'pH_Level': ph,
                        'Is_Anomaly': 'Yes' if pred == -1 else 'No',
                        'Anomaly_Score': score
                    })
                
                # Save results
                results_df = pd.DataFrame(results)
                output_file = f"anomaly_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                results_df.to_csv(output_file, index=False)
                
                anomaly_count = (results_df['Is_Anomaly'] == 'Yes').sum()
                print(f"\n✓ Analysis complete!")
                print(f"  Total records: {len(results_df)}")
                print(f"  Anomalies: {anomaly_count} ({(anomaly_count/len(results_df)*100):.1f}%)")
                print(f"  Results saved to: {output_file}")
            
            except Exception as e:
                print(f"✗ Error: {e}")
        
        else:
            print("✗ Unknown command")

if __name__ == "__main__":
    # Check if custom command provided
    if len(sys.argv) > 1:
        if sys.argv[1] == 'interactive':
            interactive_mode()
        elif sys.argv[1] == 'check':
            if len(sys.argv) >= 5:
                detector = AnomalyDetector()
                temp = float(sys.argv[2])
                humidity = float(sys.argv[3])
                ph = float(sys.argv[4])
                plant_id = sys.argv[5] if len(sys.argv) > 5 else "Unknown"
                date = sys.argv[6] if len(sys.argv) > 6 else "Unknown"
                detector.analyze_reading(temp, humidity, ph, plant_id, date)
            else:
                print("Usage: python anomaly_utility.py check <temperature> <humidity> <ph> [plant_id] [date]")
    else:
        # Default: interactive mode
        interactive_mode()
