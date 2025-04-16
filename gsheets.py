import csv, io, os
import gspread
from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()

GOOGLE_API_CREDENTIALS_PATH = os.getenv("GOOGLE_API_CREDENTIALS_PATH")

def get_google_sheet(spreadsheet_url, sheet_name):
    print(f"Inicia get_google_sheet. Sheet: {sheet_name}")

    try:
        # Load credentials and create a client
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_API_CREDENTIALS_PATH,
            scopes=scope
        )


        client = gspread.authorize(credentials)

        # Open the spreadsheet and select the sheet
        spreadsheet = client.open_by_url(spreadsheet_url)
        sheet = spreadsheet.worksheet(sheet_name)

        print("OK. Fin get_google_sheet")

        return sheet, True

    except Exception as e:
        error_message = f'Error al obtener la hoja de Google Sheets: {str(e)}'
        print(error_message)
        return None, False

def export_sheet_to_csv(spreadsheet_url, sheet_name, csv_file_path):
    """
    Exports data from a Google Sheet to a CSV file.

    Parameters:
        spreadsheet_url (str): The URL of the Google Sheet.
        sheet_name (str): The name of the worksheet.
        csv_file_path (str): The local file path to save the CSV.

    Returns:
        bool: True if export is successful, False otherwise.
    """
    print(f"Inicia export_sheet_to_csv. Sheet: {sheet_name}")
    try:
        sheet, success = get_google_sheet(spreadsheet_url, sheet_name)
        if not success or sheet is None:
            print("Failed to obtain the sheet using get_google_sheet")
            return False

        # Get all data from the sheet
        data = sheet.get_all_values()
        
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(data)

        print(f"OK. CSV export complete: {csv_file_path}")
        return True
    except Exception as e:
        error_message = f"Error exporting sheet to CSV: {str(e)}"
        print(error_message)
        return False

def export_sheet_to_csv_string(spreadsheet_url, sheet_name):
    """
    Exports data from a Google Sheet to a CSV formatted string.
    
    Parameters:
        spreadsheet_url (str): The URL of the Google Sheet.
        sheet_name (str): The name of the worksheet.

    Returns:
        str: CSV formatted string if export is successful, otherwise an empty string.
    """
    print(f"Inicia export_sheet_to_csv_string. Sheet: {sheet_name}")
    try:
        sheet, success = get_google_sheet(spreadsheet_url, sheet_name)
        if not success or sheet is None:
            print("Failed to obtain the sheet using get_google_sheet")
            return ""
        # Get all data from the sheet
        data = sheet.get_all_values()
        
        # Remove the column with header "Plantilla HTML"
        if data and "Plantilla HTML" in data[0]:
            col_index = data[0].index("Plantilla HTML")
            data = [row[:col_index] + row[col_index+1:] for row in data]
        
        
        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerows(data)
        csv_content = csv_output.getvalue()
        csv_output.close()
        
        print("OK. CSV string export complete")
        return csv_content
    except Exception as e:
        error_message = f"Error exporting sheet to CSV string: {str(e)}"
        print(error_message)
        print(error_message)
        return ""

