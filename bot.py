# ==========================================
# E-BOT LITE BUSINESS (DUAL MENU TEST)
# Twilio WhatsApp Sandbox + Flask
# ==========================================

import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# -----------------------------
# ARCHIVOS
# -----------------------------

CONFIG_FILE = "config.json"
AGENDA_FILE = "agenda_config.json"
TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

# -----------------------------
# HELPERS JSON
# -----------------------------

def cargar_json(path, default):
    if not os.path.exists(path):
        guardar_json(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# CONFIG INICIAL
# -----------------------------

cargar_json(CONFIG_FILE, {
    "bot_activo": True,
    "duracion_turno": 30,
    "modo_hibrido": True,
    "urgencia": {"numero": "+549000000000"},
    "admin_number": "whatsapp:+5493515645624"
})

cargar_json(AGENDA_FILE, {
    "lunes": {"activo": True, "modo": "manana"},
    "martes": {"activo": True, "modo": "corrido"},
    "miercoles": {"activo": True, "modo": "manana"},
    "jueves": {"activo": True, "modo": "tarde"},
    "viernes": {"activo": True, "modo": "manana"},
    "sabado": {"activo": False},
    "domingo": {"activo": False}
})

cargar_json(TURNOS_FILE, [])
cargar_json(MENSAJES_FILE, [])

# -----------------------------
# ESTADO
# -----------------------------

estado = {}

# -----------------------------
# GENERADOR DE SLOTS
# -----------------------------

def generar_slots(fecha):
    config = cargar_json(CONFIG_FILE, {})
    agenda = cargar_json(AGENDA_FILE, {})
    turnos = cargar_json(TURNOS_FILE, [])

    dia_nombre = fecha.strftime("%A").lower()
    traduccion = {
        "monday":"lunes","tuesday":"martes","wednesday":"miercoles",
        "thursday":"jueves","friday":"viernes",
        "saturday":"sabado","sunday":"domingo"
    }
    dia = traduccion.get(dia_nombre)

    if not agenda.get(dia, {}).get("activo"):
        return []

    modo = agenda[dia].get("modo", "manana")
    duracion = config.get("duracion_turno", 30)

    if modo == "manana":
        inicio, fin = 9, 12
    elif modo == "tarde":
        inicio, fin = 15, 19
    else:
        inicio, fin = 9, 18

    slots = []
    actual = datetime(fecha.year, fecha.month, fecha.day, inicio, 0)

    while actual.hour < fin:
        hora_str = actual.strftime("%H:%M")
        ocupado = any(
            t["fecha"] == fecha.strftime("%Y-%m-%d") and t["hora"] == hora_str
            for t in turnos
        )
        if not ocupado:
            slots.append(hora_str)
        actual += timedelta(minutes=duracion)

    return slots

# -----------------------------
# WEBHOOK
# -----------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.values.get("From")
    body = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    config = cargar_json(CONFIG_FILE, {})
    est = estado.get(from_number, "MENU")

    if not config.get("bot_activo", True):
        msg.body("El bot está desactivado.")
        return str(resp)

    # ACCESO ADMIN (dual)
    if body.lower() in ["admin", "adm"]:
        estado[from_number] = "ADMIN"
        msg.body("🛠 ADMIN\n1 Turnos hoy\n2 Mensajes\n3 Activar/Desactivar\n4 Salir")
        return str(resp)

    # ADMIN MENU
    if est == "ADMIN":
        if body == "1":
            hoy = datetime.now().strftime("%Y-%m-%d")
            turnos = cargar_json(TURNOS_FILE, [])
            lista = [t for t in turnos if t["fecha"] == hoy]

            if not lista:
                msg.body("No hay turnos hoy.")
            else:
                texto = "\n".join([f"{t['hora']} - {t['numero']}" for t in lista])
                msg.body(texto)
            return str(resp)

        if body == "2":
            mensajes = cargar_json(MENSAJES_FILE, [])
            pendientes = [m for m in mensajes if not m.get("leido")]

            if not pendientes:
                msg.body("Sin mensajes pendientes.")
            else:
                texto = "\n".join([f"{m['numero']}: {m['mensaje']}" for m in pendientes])
                msg.body(texto)
            return str(resp)

        if body == "3":
            config["bot_activo"] = not config.get("bot_activo", True)
            guardar_json(CONFIG_FILE, config)
            msg.body("Bot activo." if config["bot_activo"] else "Bot desactivado.")
            return str(resp)

        if body == "4":
            estado[from_number] = "MENU"
            msg.body("Saliendo admin.")
            return str(resp)

    # MENU PRINCIPAL (paciente)
    if body.lower() in ["menu", "/start"]:
        estado[from_number] = "MENU"
        msg.body("🦙 E-Bot Lite Business\n1 Turno\n2 Mensaje\n3 Urgencia\n4 Salir\nEscriba opción.")
        return str(resp)

    if est == "MENU":

        if body == "1":
            estado[from_number] = "FECHA"
            msg.body("Ingrese fecha (dd/mm/yyyy)")
            return str(resp)

        if body == "2":
            estado[from_number] = "MENSAJE"
            msg.body("Escriba su mensaje:")
            return str(resp)

        if body == "3":
            urg = config.get("urgencia", {}).get("numero", "sin número")
            msg.body(f"En caso de urgencia: {urg}")
            return str(resp)

        if body == "4":
            if config.get("modo_hibrido", True):
                estado[from_number] = "LIBRE"
                msg.body("Puede escribir libremente.")
            else:
                estado[from_number] = "MENU"
                msg.body("Menú cerrado. Escriba MENU.")
            return str(resp)

    # FECHA
    if est == "FECHA":
        try:
            fecha = datetime.strptime(body, "%d/%m/%Y")
        except:
            msg.body("Formato inválido (dd/mm/yyyy)")
            return str(resp)

        slots = generar_slots(fecha)
        if not slots:
            msg.body("No hay disponibilidad ese día.")
            return str(resp)

        estado[from_number] = {"confirmando": fecha.strftime("%Y-%m-%d"), "slots": slots}
        texto = "\n".join([f"{i+1} {h}" for i, h in enumerate(slots)])
        msg.body("Horarios:\n" + texto + "\nSeleccione número.")
        return str(resp)

    # CONFIRMACIÓN SLOT
    if isinstance(est, dict):
        try:
            seleccion = int(body) - 1
        except:
            msg.body("Seleccione número válido.")
            return str(resp)

        slots = est.get("slots", [])
        if 0 <= seleccion < len(slots):
            turno = {
                "fecha": est["confirmando"],
                "hora": slots[seleccion],
                "numero": from_number
            }

            turnos = cargar_json(TURNOS_FILE, [])

            if any(t["fecha"] == turno["fecha"] and t["hora"] == turno["hora"] and t["numero"] == turno["numero"] for t in turnos):
                msg.body("Ya tiene turno en ese horario.")
                estado[from_number] = "MENU"
                return str(resp)

            turnos.append(turno)
            guardar_json(TURNOS_FILE, turnos)

            estado[from_number] = "MENU"
            msg.body(f"Turno confirmado {turno['fecha']} {turno['hora']}")
            return str(resp)

    # MENSAJE LIBRE
    if est == "MENSAJE":
        mensajes = cargar_json(MENSAJES_FILE, [])
        mensajes.append({
            "numero": from_number,
            "mensaje": body,
            "fecha": datetime.now().isoformat(),
            "leido": False
        })
        guardar_json(MENSAJES_FILE, mensajes)

        estado[from_number] = "MENU"
        msg.body("Mensaje enviado.")
        return str(resp)

    return str(resp)


# -----------------------------
# INICIO
# -----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
