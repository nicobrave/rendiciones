import os
import sys
import json
import re
import requests
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import auth, credentials as firebase_credentials
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Inicializar la aplicación Flask
app = Flask(__name__)

# Configuración de Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1BV86uBkOr1QST1GviKLCfAxNs15VOEIQS8IXM5vie8E'
RANGE_NAME = 'Sheet1!A:J'

# Inicializar credenciales de Google
def initialize_google_credentials():
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            raise ValueError("La variable de entorno 'GOOGLE_CREDENTIALS' no está configurada.")
        google_credentials_info = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(google_credentials_info, scopes=SCOPES)
        print("Credenciales de Google inicializadas correctamente.")
        return credentials
    except Exception as e:
        print(f"Error al cargar las credenciales de Google: {e}")
        sys.exit(1)

google_credentials = initialize_google_credentials()

# Inicializar cliente de Google Vision
client = vision.ImageAnnotatorClient(credentials=google_credentials)

# Inicializar cliente de Google Sheets
service = build('sheets', 'v4', credentials=google_credentials)

# Inicializar Firebase
def initialize_firebase():
    try:
        credentials_json = os.environ.get('FIREBASE_CREDENTIALS')
        if not credentials_json:
            raise ValueError("La variable de entorno 'FIREBASE_CREDENTIALS' no está configurada.")
        firebase_credentials_info = json.loads(credentials_json)
        firebase_cred = firebase_credentials.Certificate(firebase_credentials_info)
        firebase_admin.initialize_app(firebase_cred)
        print("Firebase inicializado correctamente.")
    except Exception as e:
        print(f"Error al cargar las credenciales de Firebase: {e}")
        sys.exit(1)

initialize_firebase()

# Ruta principal (login y registro)
@app.route('/')
def index():
    return render_template('index.html')

# Ruta del dashboard (protegida)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Función para limpiar y convertir montos
def clean_amount(amount_str):
    if amount_str == "N/A":
        return amount_str
    # Eliminar puntos (separadores de miles) y reemplazar comas por puntos (separadores decimales)
    cleaned_str = amount_str.replace('.', '').replace(',', '.').replace('$', '').strip()
    try:
        # Convertir a float
        return float(cleaned_str)
    except ValueError:
        return "N/A"

# Función para procesar la imagen desde una URL y extraer el texto
def process_receipt_from_url(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            raise ValueError("No se pudo descargar la imagen desde la URL proporcionada.")

        content = response.content
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if not texts:
            raise ValueError("No se pudo extraer texto de la imagen")

        extracted_text = texts[0].description
        print(f"Texto extraído completo: {extracted_text}")

        # Inicializar valores por defecto
        rut = "N/A"
        provider_name = "N/A"
        address = "N/A"
        net_amount = "N/A"
        iva = "N/A"
        iva_percentage = "N/A"
        total_amount = "N/A"

        # Buscamos patrones comunes que podrían indicar los datos específicos
        lines = extracted_text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Buscar el RUT
            if re.search(r'\d{1,2}\.\d{3}\.\d{3}-[0-9kK]', line_lower):
                rut_match = re.search(r'\d{1,2}\.\d{3}\.\d{3}-[0-9kK]', line_lower)
                if rut_match:
                    rut = rut_match.group(0)

            # Buscar el nombre del proveedor (puede variar)
            if any(keyword in line_lower for keyword in ["señor(es)", "cliente", "proveedor"]):
                provider_name = line.strip()

            # Buscar la dirección
            if any(keyword in line_lower for keyword in ["dirección", "direccion"]):
                address = line.strip()

            # Buscar el monto neto
            if "neto" in line_lower or "monto neto" in line_lower:
                net_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', line)
                if not net_match and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    net_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', next_line)
                if net_match:
                    net_amount = net_match.group(0)

            # Buscar el porcentaje de IVA
            if "iva" in line_lower or "i.v.a" in line_lower or "v.a" in line_lower or "lv.a" in line_lower or "19%" in line_lower:
                iva_percentage_match = re.search(r'(\d{1,2})\s*%', line_lower)
                if iva_percentage_match:
                    iva_percentage = iva_percentage_match.group(1)
                else:
                    # Manejar posibles errores de OCR
                    iva_percentage_match = re.search(r'(\d{1,2})\s*%?\s*\$?', line_lower)
                    if iva_percentage_match:
                        iva_percentage = iva_percentage_match.group(1)
                # Buscar el monto del IVA
                iva_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', line)
                if not iva_match and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    iva_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', next_line)
                if iva_match:
                    iva = iva_match.group(0)

            # Buscar el monto total
            if "total" in line_lower:
                total_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', line)
                if not total_match and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    total_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', next_line)
                if total_match:
                    total_amount = total_match.group(0)

        # Limpieza y conversión de montos
        net_amount = clean_amount(net_amount)
        total_amount = clean_amount(total_amount)

        # Convertir porcentaje de IVA a número flotante
        if iva_percentage != "N/A":
            try:
                iva_percentage_value = float(iva_percentage)
            except ValueError:
                iva_percentage_value = 0.0
        else:
            iva_percentage_value = 0.0

        # Calcular el monto del IVA si es posible
        if isinstance(net_amount, float) and iva_percentage_value > 0:
            iva = net_amount * (iva_percentage_value / 100)
        elif isinstance(net_amount, float) and isinstance(total_amount, float):
            # Si no tenemos el porcentaje, calculamos el IVA a partir del total
            iva = total_amount - net_amount
        else:
            iva = "N/A"

        # Clasificación del gasto
        category = classify_expense(extracted_text)

        return {
            "rut": rut,
            "provider_name": provider_name,
            "address": address,
            "net_amount": net_amount,
            "iva": iva,
            "iva_percentage": iva_percentage_value if iva_percentage_value > 0 else "N/A",
            "total_amount": total_amount,
            "category": category
        }

    except Exception as e:
        print(f"Error al procesar la imagen: {e}")
        raise e

# Función para clasificar el gasto en una categoría
def classify_expense(text):
    text = text.lower()
    keywords = {
        'materiales': ['cemento', 'acero', 'arena', 'hormigón', 'ladrillo'],
        'transporte': ['flete', 'camión', 'transporte', 'entrega'],
        'mano de obra': ['albañil', 'electricista', 'obrero', 'mano de obra'],
        'servicios': ['agua', 'luz', 'electricidad', 'internet', 'gas'],
    }

    for category, words in keywords.items():
        for word in text.split():
            if word in words:
                return category
    return 'otros'

# Función para guardar datos en Google Sheets
def save_to_google_sheets(uid, email, project_id, rut, provider_name, address, net_amount, iva, total_amount, category, iva_percentage):
    try:
        # Formatear los montos con dos decimales
        net_amount_formatted = "{:.2f}".format(net_amount) if isinstance(net_amount, float) else "N/A"
        iva_formatted = "{:.2f}".format(iva) if isinstance(iva, float) else "N/A"
        total_amount_formatted = "{:.2f}".format(total_amount) if isinstance(total_amount, float) else "N/A"
        
        # Formatear el porcentaje de IVA
        if iva_percentage != "N/A":
            iva_display = f"{iva_percentage}%"
        else:
            iva_display = iva_formatted

        values = [[
            uid or "N/A",
            email or "N/A",
            project_id or "N/A",
            rut or "N/A",
            provider_name or "N/A",
            address or "N/A",
            net_amount_formatted,
            iva_display,
            total_amount_formatted,
            category or "N/A"
        ]]
        body = {'values': values}

        # Llamada a Google Sheets API para guardar los datos
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        print(f"{result.get('updates', {}).get('updatedCells', 0)} celdas actualizadas.")
    except Exception as e:
        print(f"Error al guardar en Google Sheets: {e}")

# Ruta para recibir y guardar las rendiciones
@app.route('/upload', methods=['POST'])
def upload():
    # Obtener el token de autenticación de Firebase desde la cabecera 'Authorization'
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return jsonify({"message": "Token de autenticación faltante"}), 403

    # Extraer el token de la cabecera
    if not auth_header.startswith('Bearer '):
        return jsonify({"message": "Formato de token de autenticación inválido"}), 403

    id_token = auth_header.split('Bearer ')[1]

    # Verificar el token de Firebase para obtener UID y email
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
    except Exception as e:
        return jsonify({"message": f"Token de autenticación inválido: {e}"}), 403

    # Obtener la URL de la imagen y el ID del proyecto del formulario
    project_id = request.json.get('project_id')
    image_url = request.json.get('image_url')

    # Procesar la imagen desde la URL para extraer los datos
    try:
        extracted_data = process_receipt_from_url(image_url)
        rut = extracted_data.get("rut", "N/A")
        provider_name = extracted_data.get("provider_name", "N/A")
        address = extracted_data.get("address", "N/A")
        net_amount = extracted_data.get("net_amount", "N/A")
        iva = extracted_data.get("iva", "N/A")
        iva_percentage = extracted_data.get("iva_percentage", "N/A")
        total_amount = extracted_data.get("total_amount", "N/A")
        category = extracted_data.get("category", "otros")
    except Exception as e:
        return jsonify({"message": f"Error al procesar la imagen: {e}"}), 400

    # Imprimir los valores extraídos para verificar que no haya problemas
    print(f"Datos extraídos: UID={uid}, Email={email}, ProjectID={project_id}, RUT={rut}, Proveedor={provider_name}, Dirección={address}, Neto={net_amount}, IVA={iva}, Total={total_amount}, Categoría={category}, IVA Porcentaje={iva_percentage}")

    # Guardar los datos en Google Sheets
    save_to_google_sheets(uid, email, project_id, rut, provider_name, address, net_amount, iva, total_amount, category, iva_percentage)

    return jsonify({"message": "Datos guardados en Google Sheets."})

if __name__ == "__main__":
    app.run()
