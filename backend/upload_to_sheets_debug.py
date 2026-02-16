import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup Authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# 2. Open the Spreadsheet
spreadsheet = client.open("Agribot-AI-datasheet")
sheet = spreadsheet.sheet1

# 3. Read CSV
df = pd.read_csv('lettuce_dataset_updated.csv')

# Debug: Print actual column names
print("Actual column names in CSV:")
print(df.columns.tolist())
print("\n")

# Use the actual column names from the CSV
required_columns = df.columns.tolist()

# Create a new dataframe with all columns
df_filtered = df[required_columns]

# 4. Prepare for Upload
# Replace any empty values with blank strings
df_filtered = df_filtered.fillna("")

# Convert the dataframe to a list of lists (headers + data rows)
data_to_upload = [df_filtered.columns.values.tolist()] + df_filtered.values.tolist()

print(f"Uploading {len(df_filtered)} rows...")
print(f"First few rows: {data_to_upload[:3]}")

# 5. Clear and Update the Sheet
try:
    sheet.clear()
    print("Sheet cleared successfully")
    
    sheet.update('A1', data_to_upload)
    print(f"Successfully uploaded {len(df_filtered)} rows!")
except Exception as e:
    print(f"Error: {e}")
