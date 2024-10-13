import firebase_admin
from firebase_admin import credentials, auth

# Inicializar Firebase Admin SDK
cred = credentials.Certificate("app/rendiciones-5b817-firebase-adminsdk-sq4uh-590dca77e5.json")
firebase_admin.initialize_app(cred)

def verify_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        return uid
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None
