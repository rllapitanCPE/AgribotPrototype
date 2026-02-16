import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Open service account
gc = gspread.service_account(filename="credentials.json")

# Google Drive folder ID from the shared link
folder_id = "1boNo4Bv-SoBE9ZRxBmSBXw_gSzmTTwDL"

# Build Google Drive service
creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=creds)

# List files in the folder
print(f"Files in Google Drive folder: {folder_id}\n")
try:
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        spaces="drive",
        fields="files(id, name, mimeType)",
        pageSize=10
    ).execute()
    
    files = results.get("files", [])
    if files:
        for file in files:
            print(f"- {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")
    else:
        print("No files found in this folder.")
except Exception as e:
    print(f"Error: {e}")

print("\nGoogle Drive test completed!")
