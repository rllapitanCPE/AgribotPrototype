"""
Raspberry Pi Sensor Data Collection Script
Reads sensor data and sends to Flask server
"""

import requests
import time
import json
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Flask server details
SERVER_URL = "http://localhost:5000"  # Change to your Raspberry Pi's IP or hostname
API_ENDPOINT = f"{SERVER_URL}/api/sensor-data"

# Sensor reading interval (seconds)
SENSOR_READ_INTERVAL = 10

# Plant identifier (for monitoring multiple plants)
PLANT_ID = "Plant-1"

# Connection retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2

# ============================================================================
# SENSOR READING FUNCTIONS
# Modify these functions to read from your actual sensors
# ============================================================================

def read_dht22_sensor(pin):
    """
    Read DHT22 temperature and humidity sensor
    
    Installation:
        pip install Adafruit-DHT
    
    Wiring (DHT22):
        - VCC (pin 1) -> 3.3V
        - DATA (pin 2) -> GPIO pin (default: 17)
        - GND (pin 4) -> GND
    
    Usage:
        temp, humidity = read_dht22_sensor(17)
    """
    try:
        import Adafruit_DHT
        
        # DHT22 sensor type
        sensor = Adafruit_DHT.DHT22
        
        # Read sensor
        humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
        
        if humidity is not None and temperature is not None:
            return temperature, humidity
        else:
            print("DHT22: Failed to read sensor")
            return None, None
    except ImportError:
        print("⚠ Adafruit_DHT not installed. Install with: pip install Adafruit-DHT")
        return None, None
    except Exception as e:
        print(f"✗ DHT22 Error: {e}")
        return None, None

def read_lm35_sensor(adc_pin):
    """
    Read LM35 temperature sensor via ADC
    
    Installation:
        pip install adafruit-circuitpython-ads1x15
    
    Wiring (LM35 to ADS1115 ADC):
        - LM35 Vcc (pin 1) -> 5V
        - ADC SCL -> GPIO 3 (SCL)
        - ADC SDA -> GPIO 2 (SDA)
        - GND -> GND
    
    Usage:
        temp = read_lm35_sensor(adc_pin=0)
    """
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        
        # Create analog input channel
        channel = AnalogIn(ads, adc_pin)
        
        # Read voltage and convert to temperature
        # LM35: 10mV per degree Celsius
        voltage = channel.voltage
        temperature = voltage * 100  # Convert to Celsius
        
        return temperature
    except ImportError:
        print("⚠ adafruit-circuitpython-ads1x15 not installed")
        return None
    except Exception as e:
        print(f"✗ LM35 Error: {e}")
        return None

def read_ph_sensor(adc_pin):
    """
    Read pH sensor via ADC
    
    Installation:
        pip install adafruit-circuitpython-ads1x15
    
    Wiring (pH sensor to ADS1115):
        - pH sensor output -> A1 analogue pin
        - SCL -> GPIO 3 (SCL)
        - SDA -> GPIO 2 (SDA)
        - GND -> GND
    
    Calibration:
        The voltage to pH conversion requires calibration with known pH buffers.
        This is a simplified example. Adjust the formula based on your sensor.
    
    Usage:
        ph = read_ph_sensor(adc_pin=1)
    """
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        
        # Create analog input channel
        channel = AnalogIn(ads, adc_pin)
        
        # Read voltage - conversion depends on calibration
        # This is a placeholder formula - calibrate with your sensor!
        voltage = channel.voltage
        ph = 7.0 + (voltage - 1.65) * 3.0  # Simplified conversion
        
        # Clamp to valid pH range
        ph = max(0.0, min(14.0, ph))
        
        return ph
    except ImportError:
        print("⚠ adafruit-circuitpython-ads1x15 not installed")
        return None
    except Exception as e:
        print(f"✗ pH Sensor Error: {e}")
        return None

# ============================================================================
# MOCK SENSOR FUNCTIONS (FOR TESTING)
# Use these when sensors are not connected
# ============================================================================

def read_mock_sensors():
    """
    Generate random sensor data for testing
    Remove this function once real sensors are connected
    """
    import random
    
    temperature = 20 + random.uniform(-2, 5)  # 18-25°C
    humidity = 60 + random.uniform(-10, 10)   # 50-70%
    ph = 6.5 + random.uniform(-0.3, 0.3)      # 6.2-6.8
    
    return temperature, humidity, ph

# ============================================================================
# SENSOR DATA COLLECTION
# ============================================================================

def collect_sensor_data():
    """
    Collect data from all sensors
    Returns: (temperature, humidity, ph) or (None, None, None) if failed
    """
    
    # === OPTION 1: Use real sensors ===
    # Uncomment and modify these lines to use actual sensors
    
    # temp, humidity = read_dht22_sensor(pin=17)
    # ph = read_ph_sensor(adc_pin=0)
    # if temp is None or humidity is None or ph is None:
    #     return None, None, None
    # return temp, humidity, ph
    
    # === OPTION 2: Use individual sensor readings ===
    # temp = read_lm35_sensor(adc_pin=0)
    # humidity, _ = read_dht22_sensor(pin=17)
    # ph = read_ph_sensor(adc_pin=1)
    # if temp is None or humidity is None or ph is None:
    #     return None, None, None
    # return temp, humidity, ph
    
    # === OPTION 3: Use mock data (for testing) ===
    return read_mock_sensors()

# ============================================================================
# DATA TRANSMISSION
# ============================================================================

def send_sensor_data(temperature, humidity, ph, plant_id=PLANT_ID):
    """
    Send sensor data to Flask server
    Returns: True if successful, False otherwise
    """
    
    payload = {
        'temperature': round(temperature, 2),
        'humidity': round(humidity, 2),
        'ph': round(ph, 4),
        'plant_id': plant_id
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'UNKNOWN')
                print(f"✓ Data sent successfully - Status: {status}")
                return True
            else:
                print(f"✗ Server returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"✗ Connection error (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                
        except requests.exceptions.Timeout:
            print(f"✗ Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                
        except Exception as e:
            print(f"✗ Error sending data: {e}")
            return False
    
    print(f"✗ Failed to send data after {MAX_RETRIES} attempts")
    return False

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    """Main sensor reading and transmission loop"""
    
    print("=" * 70)
    print("Raspberry Pi Sensor Data Collection System")
    print("=" * 70)
    print(f"Server URL: {SERVER_URL}")
    print(f"Plant ID: {PLANT_ID}")
    print(f"Read interval: {SENSOR_READ_INTERVAL} seconds")
    print(f"Retries on failure: {MAX_RETRIES}")
    print("\nStarting sensor collection... (Press Ctrl+C to stop)\n")
    
    reading_count = 0
    error_count = 0
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] Reading sensors...")
            
            # Read sensor data
            temperature, humidity, ph = collect_sensor_data()
            
            if temperature is None or humidity is None or ph is None:
                print("✗ Failed to read sensors")
                error_count += 1
                time.sleep(SENSOR_READ_INTERVAL)
                continue
            
            # Display readings
            print(f"  Temperature: {temperature:.2f}°C")
            print(f"  Humidity:    {humidity:.2f}%")
            print(f"  pH:          {ph:.4f}")
            
            # Send to server
            if send_sensor_data(temperature, humidity, ph):
                reading_count += 1
            else:
                error_count += 1
            
            # Wait before next reading
            time.sleep(SENSOR_READ_INTERVAL)
    
    except KeyboardInterrupt:
        print(f"\n\n{'=' * 70}")
        print("Sensor collection stopped by user")
        print(f"Total readings sent: {reading_count}")
        print(f"Errors: {error_count}")
        print("=" * 70)

if __name__ == '__main__':
    main()
