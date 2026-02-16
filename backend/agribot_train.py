import gspread
import pandas as pd
import numpy as np
import tensorflow as tf
from oauth2client.service_account import ServiceAccountCredentials
from sklearn.model_selection import train_test_split

# 1. AUTHENTICATION & DATA FETCH
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Open your Agribot datasheet
sheet = client.open("Agribot-AI-datasheet").sheet1
data = sheet.get_all_records()

# 2. DATA PREPROCESSING
df = pd.DataFrame(data)

# --- THESIS STEP: Define your Inputs (X) and Labels (y) ---
# Example: If column 'A' and 'B' are sensors, and 'C' is the result
X = df[['Sensor_A', 'Sensor_B']].values 
y = df['Target_Label'].values

# Split data: 80% for training, 20% for testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 3. BUILD THE TENSORFLOW MODEL
model = tf.keras.Sequential([
    tf.keras.layers.Dense(16, activation='relu', input_shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(8, activation='relu'),
    tf.keras.layers.Dense(1, activation='sigmoid') # Binary output (e.g., Yes/No)
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# 4. TRAIN
model.fit(X_train, y_train, epochs=50, batch_size=4)

# 5. SAVE FOR RASPBERRY PI (TFLite)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)

print("AI Training Complete and TFLite model saved!")