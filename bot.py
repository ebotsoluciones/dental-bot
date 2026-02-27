"""
BOT PARA TWILIO WHATSAPP SANDBOX
--------------------------------
Este bot utiliza la API de Twilio para WhatsApp.

Flujo:
1) Twilio recibe mensaje desde WhatsApp
2) Twilio llama al webhook (/webhook)
3) Flask procesa mensaje
4) Responde con TwiML (MessagingResponse)
5) Twilio envía respuesta al usuario

No usa Meta Graph API ni tokens de WhatsApp Business.
Es compatible con sandbox de Twilio.
"""

import json
import os
from flask import Flask, request
from datetime import datetime
from twilio.twiml.messaging_response import MessagingResponse

# --------------------------------------------------
# APP FLASK
# --------------------------------------------------

app = Flask(__name__)

# --------------------------------------------------
# ESTADO (memoria en runtime)
# --------------------------------------------------

estado = {}
INICIO = "INICIO"
MENU = "MENU"
FECHA = "FECHA"
HORA = "HORA"
MENSAJE = "MENSAJE"

# Archivos locales para turnos y mensajes
TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

# --------------------------------------------------
# HELPERS JSON
# --------------------------------------------------

def cargar_json(path):
    """Carga JSON desde archivo. Si falla, retorna lista vacía."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_json(path, data):
    """Guarda JSON en archivo con formato legible."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --------------------------------------------------
# MENÚ
# --------------------------------------------------

MENU_TXT = (
    "🤖 E-Bot Asistente\n\n"
    "1️⃣ Solicitar Visita\n"
    "2️⃣ Dejar Mensaje\n"
    "3️⃣ Información\n"
    "4️⃣ Salir\n\n"
    "✍️ Escriba el número:"
)

# --------------------------------------------------
# WEBHOOK (TWILIO)
# --------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Endpoint que recibe mensajes desde Twilio.
    Twilio envía datos en form-data:
    From -> número del usuario
    Body -> texto del mensaje
    """

    from_number = request.values.get("From")
    body = request.values.get("Body", "").strip()

    # Respuesta TwiML
    resp = MessagingResponse()
    msg = resp.message()

    est = estado.get(from_number, INICIO)

    # Comando /start
    if body.lower() == "/start":
        estado[from_number] = MENU
        msg.body(MENU_TXT)
        return str(resp)

    # Estado inicial
    if est == INICIO:
        msg.body("✋ Enviá /start para comenzar.")
        return str(resp)

    # MENÚ PRINCIPAL
    if est == MENU:

        if body == "1":
            turnos = cargar_json(TURNOS_FILE)
            fechas = [t["fecha"] for t in turnos]

            if not fechas:
                msg.body("❌ No hay fechas disponibles.")
            else:
                estado[from_number] = FECHA
                msg.body("📅 Fechas:\n" + "\n".join(fechas) + "\n\nEscriba la fecha.")
            return str(resp)

        if body == "2":
            estado[from_number] = MENSAJE
            msg.body("📝 Escriba su mensaje:")
            return str(resp)

        if body == "3":
            msg.body("💻 Información en desarrollo.")
            msg.body(MENU_TXT)
            return str(resp)

        if body == "4":
            msg.body("👋 Hasta pronto.")
            estado[from_number] = INICIO
            return str(resp)

        msg.body("❌ Opción no válida.")
        msg.body(MENU_TXT)
        return str(resp)

    # SELECCIÓN DE FECHA
    if est == FECHA:
        fecha = body
        turnos = cargar_json(TURNOS_FILE)
        turno = next((t for t in turnos if t["fecha"] == fecha), None)

        if not turno:
            msg.body("❌ Fecha no disponible.")
            return str(resp)

        libres = [h["hora"] for h in turno["horarios"] if h["disponible"]]

        if not libres:
            msg.body("❌ No hay horarios.")
            return str(resp)

        estado[from_number] = HORA
        estado[f"{from_number}_fecha"] = fecha
        msg.body("⏰ Horarios:\n" + "\n".join(libres) + "\n\nEscriba la hora.")
        return str(resp)

    # SELECCIÓN DE HORA
    if est == HORA:
        hora = body
        fecha = estado.get(f"{from_number}_fecha")

        turnos = cargar_json(TURNOS_FILE)
        for t in turnos:
            if t["fecha"] == fecha:
                for h in t["horarios"]:
                    if h["hora"] == hora and h["disponible"]:
                        h["disponible"] = False
                        guardar_json(TURNOS_FILE, turnos)

                        msg.body(f"✅ Turno: {fecha} a las {hora}")
                        estado[from_number] = MENU
                        msg.body(MENU_TXT)
                        return str(resp)

        msg.body("❌ Hora no disponible.")
        return str(resp)

    # MENSAJES LIBRES
    if est == MENSAJE:
        mensajes = cargar_json(MENSAJES_FILE)
        mensajes.append({
            "chat": from_number,
            "mensaje": body,
            "fecha": str(datetime.now())
        })
        guardar_json(MENSAJES_FILE, mensajes)

        msg.body("✅ Mensaje recibido.")
        estado[from_number] = MENU
        msg.body(MENU_TXT)
        return str(resp)

    return str(resp)


# --------------------------------------------------
# VERIFICACIÓN TWILIO (GET)
# --------------------------------------------------

@app.route("/webhook", methods=["GET"])
def verify():
    """
    Twilio usa GET para verificación inicial.
    Devuelve hub.challenge para validar URL.
    """
    return request.args.get("hub.challenge", "")


# --------------------------------------------------
# INICIO SERVIDOR
# --------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
