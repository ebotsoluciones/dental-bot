import requests
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Tu token de acceso permanente de WhatsApp Business API
ACCESS_TOKEN = "TU_TOKEN_PERMANENTE"
PHONE_NUMBER_ID = "TU_NUMERO_ID"

# Función para enviar mensaje de vuelta
def send_message(to, message):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }
    r = requests.post(url, headers=headers, json=data)
    return r.status_code, r.text

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación de Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode and token == "ebot-token":
            return challenge
        return "Forbidden", 403

    if request.method == "POST":
        data = request.get_json()
        # Extraemos el número del remitente y el mensaje
        try:
            entry = data["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            messages = value.get("messages")
            if messages:
                from_number = messages[0]["from"]
                text = messages[0]["text"]["body"].lower()
                # Lógica mínima
                if "hola" in text:
                    send_message(from_number, "Hola!")
                elif "salir" in text:
                    send_message(from_number, "Chau!")
                else:
                    send_message(from_number, "No entendí, decime 'hola' o 'salir'")
        except Exception as e:
            print("Error procesando mensaje:", e)
        return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
