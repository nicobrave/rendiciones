from google.cloud import vision, storage
import os
import requests

# Inicializar Google Vision Client y Storage Client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "app/vision-api-credentials.json"
vision_client = vision.ImageAnnotatorClient()
storage_client = storage.Client()

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