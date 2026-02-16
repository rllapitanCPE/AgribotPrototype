import gspread

gc = gspread.service_account(filename="credentials.json")

sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1otEZmlkFRhEvq4DZVPDejwN0p6p6bd_xITQIJti4hgc/edit?usp=sharing")
worksheet = sh.sheet1

worksheet.append_row(["Earl", "Dimagiba", "F."])
print("Sheet updated successfully!")
