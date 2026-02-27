import json
import os
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

# ============================
# CONFIG
# ============================

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

estado = {}
INICIO = "INICIO"
MENU = "MENU"
FECHA = "FECHA"
HORA = "HORA"
MENSAJE = "MENSAJE"

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

# ============================
# JSON HELPERS
# ============================

def cargar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================
# WHATSAPP SEND
# ============================

def enviar_whatsapp(chat_id, texto):
    if not WHATSAPP_TOKEN or not PHONE_ID:
        print("Faltan variables WHATSAPP_TOKEN o PHONE_ID")
        return

    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": chat_id,
        "type": "text",
        "text": {"body": texto}
    }

    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print("Error enviando WhatsApp:", e)

# ============================
# MENU
# ============================

MENU_TXT = (
    "🤖 E-Bot Asistente\n\n"
    "1️⃣ Solicitar Visita\n"
    "2️⃣ Dejar Mensaje\n"
    "3️⃣ Información\n"
    "4️⃣ Salir\n\n"
    "✍️ Escriba el número:"
)

# ============================
# WEBHOOK
# ============================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        chat_id = mensaje["from"]
        texto = mensaje["text"]["body"].strip()
    except:
        return "ok"

    est = estado.get(chat_id, INICIO)

    if texto.lower() == "/start":
        estado[chat_id] = MENU
        enviar_whatsapp(chat_id, MENU_TXT)
        return "ok"

    if est == INICIO:
        enviar_whatsapp(chat_id, "✋ Enviá /start para comenzar.")
        return "ok"

    if est == MENU:

        if texto == "1":
            turnos = cargar_json(TURNOS_FILE)
            fechas = [t["fecha"] for t in turnos]

            if not fechas:
                enviar_whatsapp(chat_id, "❌ No hay fechas disponibles.")
            else:
                estado[chat_id] = FECHA
                enviar_whatsapp(chat_id, "📅 Fechas:\n" + "\n".join(fechas) + "\n\nEscriba la fecha.")

            return "ok"

        if texto == "2":
            estado[chat_id] = MENSAJE
            enviar_whatsapp(chat_id, "📝 Escriba su mensaje:")
            return "ok"

        if texto == "3":
            enviar_whatsapp(chat_id, "💻 Información en desarrollo.")
            enviar_whatsapp(chat_id, MENU_TXT)
            return "ok"

        if texto == "4":
            enviar_whatsapp(chat_id, "👋 Hasta pronto.")
            estado[chat_id] = INICIO
            return "ok"

        enviar_whatsapp(chat_id, "❌ Opción no válida.")
        enviar_whatsapp(chat_id, MENU_TXT)
        return "ok"

    if est == FECHA:
        fecha = texto
        turnos = cargar_json(TURNOS_FILE)
        turno = next((t for t in turnos if t["fecha"] == fecha), None)

        if not turno:
            enviar_whatsapp(chat_id, "❌ Fecha no disponible.")
            return "ok"

        libres = [h["hora"] for h in turno["horarios"] if h["disponible"]]

        if not libres:
            enviar_whatsapp(chat_id, "❌ No hay horarios.")
            return "ok"

        estado[chat_id] = HORA
        estado[f"{chat_id}_fecha"] = fecha
        enviar_whatsapp(chat_id, "⏰ Horarios:\n" + "\n".join(libres) + "\n\nEscriba la hora.")
        return "ok"

    if est == HORA:
        hora = texto
        fecha = estado.get(f"{chat_id}_fecha")

        turnos = cargar_json(TURNOS_FILE)
        for t in turnos:
            if t["fecha"] == fecha:
                for h in t["horarios"]:
                    if h["hora"] == hora and h["disponible"]:
                        h["disponible"] = False
                        guardar_json(TURNOS_FILE, turnos)

                        enviar_whatsapp(chat_id, f"✅ Turno: {fecha} a las {hora}")
                        estado[chat_id] = MENU
                        enviar_whatsapp(chat_id, MENU_TXT)
                        return "ok"

        enviar_whatsapp(chat_id, "❌ Hora no disponible.")
        return "ok"

    if est == MENSAJE:
        mensajes = cargar_json(MENSAJES_FILE)
        mensajes.append({
            "chat": chat_id,
            "mensaje": texto,
            "fecha": str(datetime.now())
        })
        guardar_json(MENSAJES_FILE, mensajes)

        enviar_whatsapp(chat_id, "✅ Mensaje recibido.")
        estado[chat_id] = MENU
        enviar_whatsapp(chat_id, MENU_TXT)
        return "ok"

    return "ok"


@app.route("/webhook", methods=["GET"])
def verify():
    return request.args.get("hub.challenge", "")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
