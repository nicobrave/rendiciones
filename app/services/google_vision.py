import os
import sys
import json
import requests
from google.cloud import vision, storage
from google.oauth2.service_account import Credentials

def initialize_google_clients():
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            raise ValueError("La variable de entorno 'GOOGLE_CREDENTIALS' no está configurada.")
        google_credentials_info = json.loads(credentials_json)
        google_credentials = Credentials.from_service_account_info(google_credentials_info)
        vision_client = vision.ImageAnnotatorClient(credentials=google_credentials)
        storage_client = storage.Client(credentials=google_credentials)
        print("Clientes de Google Vision API y Storage inicializados correctamente.")
        return vision_client, storage_client
    except Exception as e:
        print(f"Error al cargar las credenciales de Google: {e}")
        sys.exit(1)

vision_client, storage_client = initialize_google_clients()

def process_receipt(bucket_name, file_name):
    # Descargar la imagen desde Firebase Storage
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    image_content = blob.download_as_bytes()

    # Procesar la imagen con Google Vision
    image = vision.Image(content=image_content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        extracted_text = texts[0].description
        # Clasificar el gasto
        category = classify_expense(extracted_text)
        return extracted_text, category
    else:
        return "No text found", "otros"

def process_receipt_from_url(image_url):
    # Descargar la imagen desde la URL
    response = requests.get(image_url)
    if response.status_code != 200:
        return None, None

    image_content = response.content

    # Procesar la imagen con Google Vision
    image = vision.Image(content=image_content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        extracted_text = texts[0].description
        # Clasificar el gasto
        category = classify_expense(extracted_text)
        return extracted_text, category
    else:
        return "No text found", "otros"

def classify_expense(text):
    text = text.lower()
    keywords = {
        'materiales': ['cemento', 'acero', 'arena', 'hormigón', 'ladrillo'],
        'transporte': ['flete', 'camión', 'transporte', 'entrega'],
        'mano de obra': ['albañil', 'electricista', 'obrero', 'mano de obra'],
        'servicios': ['agua', 'luz', 'electricidad', 'internet', 'gas'],
    }

    for category, words in keywords.items():
        for word in words:
            if word in text:
                return category
    return 'otros'
