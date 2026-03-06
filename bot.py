"""
E-BOT LITE BUSINESS
BOT WHATSAPP CON TWILIO + FLASK
================================

Funciones:
- Turnos
- Mensajes
- Agenda
- Administración
- Mensajes no leídos
- Cancelación

Almacenamiento:
- JSON locales (turnos.json, mensajes.json)

Flujo:
- Webhook Twilio
- Estado por usuario
"""

import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# -----------------------------
# ARCHIVOS
# -----------------------------

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

def cargar_json(path):
    """Carga JSON o retorna lista vacía."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_json(path, data):
    """Guarda JSON con formato legible."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# ESTADO (memoria en runtime)
# -----------------------------

estado = {}

# -----------------------------
# MENÚS
# -----------------------------

MENU_PACIENTE = """
🦙 E-Bot Lite
1️⃣ Turno
2️⃣ Mensaje
3️⃣ Urgencia
4️⃣ Informes
5️⃣ Salir
Escriba opción.
"""

MENU_ADMIN = """
🛠 ADMIN
1️⃣ Turnos del día
2️⃣ Agenda semanal
3️⃣ Ver turnos futuros
4️⃣ Agregar turno
5️⃣ Cancelar turno
6️⃣ Ver mensajes
7️⃣ Mensajes no leídos
8️⃣ Salir
"""

# -----------------------------
# WEBHOOK TWILIO
# -----------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.values.get("From")
    body = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    est = estado.get(from_number, "MENU")

    # COMANDO PARA ENTRAR ADMIN
    if body.lower() in ["admin", "adm"]:
        estado[from_number] = "ADMIN"
        msg.body(MENU_ADMIN)
        return str(resp)

    # ADMIN FLOW
    if est == "ADMIN":
        return manejar_admin(from_number, body, resp)

    # MENU PACIENTE
    if body.lower() in ["menu", "/start"]:
        estado[from_number] = "MENU"
        msg.body(MENU_PACIENTE)
        return str(resp)

    if est == "MENU":
        return manejar_menu(from_number, body, resp)

    return str(resp)


# -----------------------------
# MENÚ PACIENTE
# -----------------------------

def manejar_menu(numero, body, resp):
    msg = resp.message()

    if body == "1":
        estado[numero] = "TURNO"
        msg.body("Ingrese fecha (dd/mm/yyyy)")
        return str(resp)

    if body == "2":
        estado[numero] = "MENSAJE"
        msg.body("Escriba su mensaje:")
        return str(resp)

    if body == "3":
        msg.body("En caso de urgencia: +549000000000")
        return str(resp)

    if body == "4":
        msg.body("Informes: servicio en desarrollo.")
        return str(resp)

    if body == "5":
        estado[numero] = "MENU"
        msg.body("👋 Hasta pronto. Escriba MENU para volver.")
        return str(resp)

    msg.body(MENU_PACIENTE)
    return str(resp)


# -----------------------------
# MENSAJE LIBRE (paciente)
# -----------------------------

def guardar_mensaje(numero, body):
    mensajes = cargar_json(MENSAJES_FILE)
    mensajes.append({
        "numero": numero,
        "mensaje": body,
        "fecha": datetime.now().isoformat(),
        "leido": False
    })
    guardar_json(MENSAJES_FILE, mensajes)


# -----------------------------
# TURNO (paciente)
# -----------------------------

def guardar_turno(numero, fecha):
    turnos = cargar_json(TURNOS_FILE)
    turnos.append({
        "numero": numero,
        "fecha": fecha,
        "hora": "00:00"
    })
    guardar_json(TURNOS_FILE, turnos)


# -----------------------------
# MENSAJE TURNO
# -----------------------------

@app.route("/webhook", methods=["POST"])
def flujo_turno():
    from_number = request.values.get("From")
    body = request.values.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    est = estado.get(from_number)

    if est == "TURNO":
        try:
            datetime.strptime(body, "%d/%m/%Y")
            guardar_turno(from_number, body)
            estado[from_number] = "MENU"
            msg.body(f"Turno solicitado para {body}")
        except:
            msg.body("Formato inválido. Use dd/mm/yyyy")
        return str(resp)

    if est == "MENSAJE":
        guardar_mensaje(from_number, body)
        estado[from_number] = "MENU"
        msg.body("Mensaje recibido.")
        return str(resp)

    return str(resp)


# -----------------------------
# ADMIN
# -----------------------------

def manejar_admin(numero, body, resp):
    msg = resp.message()

    if body == "1":
        hoy = datetime.now().strftime("%d/%m/%Y")
        turnos = [t for t in cargar_json(TURNOS_FILE) if t["fecha"] == hoy]
        if not turnos:
            msg.body("No hay turnos hoy.")
        else:
            texto = "\n".join([t["numero"] for t in turnos])
            msg.body(texto)
        return str(resp)

    if body == "2":
        semana = datetime.now() + timedelta(days=7)
        turnos = [t for t in cargar_json(TURNOS_FILE)
                 if datetime.strptime(t["fecha"], "%d/%m/%Y") <= semana]
        if not turnos:
            msg.body("Agenda vacía.")
        else:
            texto = "\n".join([f"{t['fecha']} - {t['numero']}" for t in turnos])
            msg.body(texto)
        return str(resp)

    if body == "3":
        hoy = datetime.now()
        turnos = [t for t in cargar_json(TURNOS_FILE)
                 if datetime.strptime(t["fecha"], "%d/%m/%Y") > hoy]
        if not turnos:
            msg.body("No hay turnos futuros.")
        else:
            texto = "\n".join([f"{t['fecha']} - {t['numero']}" for t in turnos])
            msg.body(texto)
        return str(resp)

    if body == "4":
        estado[numero] = "ADMIN_TURNO"
        msg.body("Agregar turno: fecha dd/mm/yyyy")
        return str(resp)

    if body == "5":
        estado[numero] = "ADMIN_CANCEL"
        msg.body("Cancelar turno: fecha dd/mm/yyyy")
        return str(resp)

    if body == "6":
        mensajes = cargar_json(MENSAJES_FILE)
        texto = "\n".join([f"{m['numero']}: {m['mensaje']}" for m in mensajes])
        msg.body(texto or "Sin mensajes.")
        return str(resp)

    if body == "7":
        mensajes = [m for m in cargar_json(MENSAJES_FILE) if not m["leido"]]
        texto = "\n".join([f"{m['numero']}: {m['mensaje']}" for m in mensajes])
        msg.body(texto or "Sin mensajes nuevos.")
        return str(resp)

    if body == "8":
        estado[numero] = "MENU"
        msg.body("Saliendo admin.")
        return str(resp)

    msg.body(MENU_ADMIN)
    return str(resp)


# -----------------------------
# INICIO
# -----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
