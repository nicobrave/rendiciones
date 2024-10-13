from google.cloud import storage

# Inicializar el cliente de almacenamiento
client = storage.Client()
bucket_name = "gs://rendiciones-5b817.appspot.com"

# Verificar si el bucket existe
try:
    bucket = client.get_bucket(bucket_name)
    print(f"Bucket '{bucket_name}' encontrado correctamente.")
except Exception as e:
    print(f"Error al acceder al bucket: {e}")
