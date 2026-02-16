import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup Authentication
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# 2. Open the Spreadsheet
spreadsheet = client.open("Agribot-AI-datasheet")
sheet = spreadsheet.sheet1

# 3. Read and Filter the CSV
# Ensure 'lettuce_dataset.csv' is in your VS Code folder
df = pd.read_csv('lettuce_dataset_updated.csv', encoding='latin-1')

# Select only the columns you requested
# Note: Ensure these column names match your CSV exactly (e.g., check for special characters like °C)
required_columns = [
    'Plant_ID', 'Date', 'Temperature (°C)', 'Humidity (%)', 
    'TDS Value (ppm)', 'pH Level', 'Growth Days', 
    'Temperature (F)', 'Humidity'
]

# Create a new dataframe with just these columns
df_filtered = df[required_columns]

# 4. Prepare for Upload
# Replace any empty values with blank strings
df_filtered = df_filtered.fillna("")

# Convert the dataframe to a list of lists (headers + data rows)
data_to_upload = [df_filtered.columns.values.tolist()] + df_filtered.values.tolist()

# 5. Clear and Update the Sheet
try:
    sheet.clear()
    sheet.update('A1', data_to_upload)
    print(f"Successfully uploaded {len(df_filtered)} rows!")
except Exception as e:
    print(f"Error: {e}")
