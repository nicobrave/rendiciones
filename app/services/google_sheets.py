from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from flask import Flask, request, jsonify
import re
from app.services.google_vision import process_receipt

app = Flask(__name__)

# Configuración de Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1BV86uBkOr1QST1GviKLCfAxNs15VOEIQS8IXM5vie8E'
RANGE_NAME = 'Test_rendiciones!A:J'  # Rango para guardar los datos en la hoja "Test_rendiciones"

# Cargar las credenciales del archivo JSON
creds = Credentials.from_service_account_file('app/sheets-api-credentials.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Función para guardar datos en Google Sheets
def save_to_google_sheets(uid, email, project_id, rut, provider_name, address, net_amount, iva, total_amount, category):
    try:
        # Datos a guardar en la hoja de cálculo
        values = [[uid, email, project_id, rut, provider_name, address, net_amount, iva, total_amount, category]]
        body = {'values': values}

        # Llamada a Google Sheets API para guardar los datos
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        print(f"{result.get('updates').get('updatedCells')} celdas actualizadas.")
    except Exception as e:
        print(f"Error al guardar en Google Sheets: {e}")

# Ruta para recibir y guardar las rendiciones
@app.route('/upload', methods=['POST'])
def upload():
    uid = request.form.get('uid')
    email = request.form.get('email')
    project_id = request.form.get('project_id')
    file = request.files.get('image')

    # Procesar la imagen para extraer los datos
    rut, provider_name, address, net_amount, iva, total_amount, category = process_receipt(file)

    # Guardar los datos en Google Sheets
    save_to_google_sheets(uid, email, project_id, rut, provider_name, address, net_amount, iva, total_amount, category)

    return jsonify({"message": "Datos guardados en Google Sheets."})

if __name__ == "__main__":
    app.run()