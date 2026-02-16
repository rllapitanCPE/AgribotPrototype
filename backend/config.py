"""
Configuration File for Anomaly Detection System
Modify these settings without editing the main scripts
"""

# ============================================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================================
SPREADSHEET_NAME = "Agribot-AI-datasheet"  # Name of your Google Sheet
CREDENTIALS_FILE = "credentials.json"        # Your Google credentials file

# ============================================================================
# FEATURE CONFIGURATION
# ============================================================================
# Which columns to monitor for anomalies
FEATURE_COLUMNS = [
    'Temperature (°C)',
    'Humidity (%)',
    'pH Level'
]

# Additional information columns (for reporting)
INFO_COLUMNS = [
    'Plant_ID',
    'Date'
]

# ============================================================================
# MODEL TRAINING CONFIGURATION
# ============================================================================
# Contamination rate: Percentage of data expected to be anomalies
# Lower value = fewer anomalies detected (less sensitive)
# Higher value = more anomalies detected (more sensitive)
CONTAMINATION_RATE = 0.05  # 5% - good balance

# Number of trees in Isolation Forest
# Higher = more accurate but slower
N_ESTIMATORS = 100

# Random seed for reproducibility
RANDOM_STATE = 42

# ============================================================================
# MODEL FILES
# ============================================================================
MODEL_FILE = "anomaly_model.pkl"      # Trained model
SCALER_FILE = "anomaly_scaler.pkl"    # Data scaler

# ============================================================================
# OUTPUT & REPORTING
# ============================================================================
# Number of anomalies to display (0 = show all)
TOP_ANOMALIES_TO_DISPLAY = 10

# Anomaly score thresholds for interpretation
ANOMALY_SCORE_MARGINS = {
    'SAFE': -0.2,         # Score > -0.2: Normal
    'WARNING': -0.5,      # Score -0.2 to -0.5: Warning
    'CRITICAL': -0.5      # Score < -0.5: Anomaly
}

# ============================================================================
# SENSITIVITY PRESETS
# Use these for quick sensitivity changes
# ============================================================================

SENSITIVITY_PRESETS = {
    'LOW': {
        'description': 'Only detect obvious anomalies',
        'contamination': 0.02  # 2%
    },
    'MEDIUM': {
        'description': 'Balanced sensitivity',
        'contamination': 0.05  # 5%
    },
    'HIGH': {
        'description': 'Detect more subtle anomalies',
        'contamination': 0.10  # 10%
    },
    'VERY_HIGH': {
        'description': 'Catch all edge cases',
        'contamination': 0.15  # 15%
    }
}

# ============================================================================
# QUICK SETUP: Uncomment one line to change all settings at once
# ============================================================================
# CURRENT_SENSITIVITY = 'MEDIUM'  # Uncomment and change as needed

# ============================================================================
# MONITORING MODE
# ============================================================================
# Enable continuous monitoring features
ENABLE_ALERTS = True           # Send alerts for anomalies
ALERT_METHOD = 'console'       # 'console', 'email', 'webhook'

# Email configuration (if ALERT_METHOD = 'email')
EMAIL_CONFIG = {
    'sender': 'your_email@gmail.com',
    'password': 'your_app_password',
    'recipients': ['admin@example.com'],
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# Webhook configuration (if ALERT_METHOD = 'webhook')
WEBHOOK_URL = 'https://your-webhook-endpoint.com/anomaly'

# ============================================================================
# ADVANCED OPTIONS
# ============================================================================
# Data preprocessing
REMOVE_MISSING_VALUES = True   # Drop rows with NaN
MISSING_VALUE_STRATEGY = 'drop'  # 'drop' or 'mean'

# Feature scaling
SCALE_FEATURES = True          # Normalize features (recommended)
SCALER_METHOD = 'standard'     # 'standard', 'minmax', 'robust'

# ============================================================================
# LOGGING & DEBUG
# ============================================================================
VERBOSE = True                 # Print detailed messages
DEBUG_MODE = False             # Show extra debugging info
LOG_FILE = 'anomaly_detection.log'
