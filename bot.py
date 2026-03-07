"""
E-BOT LITE 🦙
Bot WhatsApp con Twilio + Flask
Agenda médica simple
"""

import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

estado = {}

# -----------------------------
# ADMINISTRADORES
# -----------------------------
ADMINS = [
    "whatsapp:+5493515645624"  # reemplazar por teléfono autorizado
]

# -----------------------------
# MENÚS
# -----------------------------
MENU_PACIENTE = """
🦙 E-Bot Lite
👤 Clínica Demo

1️⃣ Turno
2️⃣ Consultar mi turno
3️⃣ Mensaje 📩
4️⃣ Urgencia 🚑
5️⃣ Informes
6️⃣ Salir
"""

MENU_ADMIN = """
🛠 ADMIN

1️⃣ Turnos de hoy 📅
2️⃣ Próximos turnos ⏩
3️⃣ Ver mensajes 📩
4️⃣ Ingresar turno ➕
5️⃣ Cancelar turno ❌
6️⃣ Bloquear agenda 🔒
7️⃣ Salir
"""

# -----------------------------
# JSON helpers
# -----------------------------
def cargar_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# HORARIOS
# -----------------------------
def generar_horarios():
    horarios = []
    inicio = datetime.strptime("09:00", "%H:%M")
    fin = datetime.strptime("19:00", "%H:%M")
    actual = inicio
    while actual <= fin:
        horarios.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=30)
    return horarios

def buscar_horario_libre(fecha):
    turnos = cargar_json(TURNOS_FILE)
    horarios = generar_horarios()
    ocupados = [t["hora"] for t in turnos if t["fecha"] == fecha]
    for h in horarios:
        if h not in ocupados:
            return h
    return None

def obtener_turnos_futuros():
    hoy = datetime.now().date()
    turnos = cargar_json(TURNOS_FILE)
    futuros = [
        t for t in turnos
        if datetime.strptime(t["fecha"], "%d/%m/%Y").date() >= hoy
    ]
    return sorted(futuros, key=lambda x: (x["fecha"], x["hora"]))

# -----------------------------
# WEBHOOK
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    numero = request.values.get("From")
    body = request.values.get("Body", "").strip()
    texto = body.lower()
    resp = MessagingResponse()
    msg = resp.message()

    estado.setdefault(numero, "MENU")
    estado_actual = estado[numero]

    # Verificación admin
    es_admin = numero in ADMINS

    # Comandos generales
    if texto in ["menu", "/start"]:
        estado[numero] = "MENU"
        msg.body(MENU_PACIENTE if not es_admin else MENU_ADMIN)
        return str(resp)

    if es_admin and texto in ["admin", "administrador"]:
        estado[numero] = "ADMIN"
        msg.body(MENU_ADMIN)
        return str(resp)

    # -----------------------------
    # FLUJO ADMIN
    # -----------------------------
    if estado_actual == "ADMIN" and es_admin:
        return manejar_admin(numero, body, resp)

    # -----------------------------
    # FLUJO PACIENTE
    # -----------------------------
    if estado_actual == "MENU":
        return manejar_menu(numero, body, resp)

    # Turno flujo
    if estado_actual == "TURNO_NOMBRE":
        estado[numero + "_nombre"] = body
        estado[numero] = "TURNO_FECHA"
        msg.body("Ingrese fecha (dd/mm/yyyy)")
        return str(resp)

    if estado_actual == "TURNO_FECHA":
        try:
            datetime.strptime(body, "%d/%m/%Y")
        except:
            msg.body("Formato inválido. Use dd/mm/yyyy")
            return str(resp)
        hora = buscar_horario_libre(body)
        if not hora:
            msg.body("Día ocupado. Intente otra fecha")
            return str(resp)
        turnos = cargar_json(TURNOS_FILE)
        turnos.append({
            "nombre": estado[numero + "_nombre"],
            "telefono": numero,
            "fecha": body,
            "hora": hora
        })
        guardar_json(TURNOS_FILE, turnos)
        estado[numero] = "MENU"
        msg.body(f"✅ Turno confirmado\n{estado[numero + '_nombre']}\n{body} {hora}")
        return str(resp)

    # Mensaje flujo
    if estado_actual == "MENSAJE_NOMBRE":
        estado[numero + "_nombre"] = body
        estado[numero] = "MENSAJE_TEXTO"
        msg.body("Escriba su mensaje")
        return str(resp)

    if estado_actual == "MENSAJE_TEXTO":
        mensajes = cargar_json(MENSAJES_FILE)
        mensajes.append({
            "nombre": estado[numero + "_nombre"],
            "telefono": numero,
            "mensaje": body,
            "fecha": datetime.now().isoformat(),
            "leido": False
        })
        guardar_json(MENSAJES_FILE, mensajes)
        estado[numero] = "MENU"
        msg.body("Mensaje recibido")
        return str(resp)

    return str(resp)

# -----------------------------
# MENÚ PACIENTE
# -----------------------------
def manejar_menu(numero, body, resp):
    msg = resp.message()
    if body == "1":
        estado[numero] = "TURNO_NOMBRE"
        msg.body("Ingrese nombre y apellido")
        return str(resp)
    if body == "2":
        # Consultar turno
        turnos = cargar_json(TURNOS_FILE)
        lista = [t for t in turnos if t["telefono"] == numero]
        if not lista:
            msg.body("No se encontraron turnos para su número")
        else:
            salida = "\n".join([f"{t['fecha']} {t['hora']}" for t in lista])
            msg.body(f"📅 Sus turnos:\n{salida}")
        return str(resp)
    if body == "3":
        estado[numero] = "MENSAJE_NOMBRE"
        msg.body("Nombre y apellido")
        return str(resp)
    if body == "4":
        msg.body("Urgencias 🚑: +549000000000")
        return str(resp)
    if body == "5":
        msg.body("""
📄 Informes

🕒 Horario: 08:00 – 18:00
🏥 Obras sociales: Sí
""")
        return str(resp)
    if body == "6":
        msg.body("Hasta pronto. Escriba MENU para volver")
        return str(resp)
    msg.body(MENU_PACIENTE)
    return str(resp)

# -----------------------------
# ADMIN
# -----------------------------
def manejar_admin(numero, body, resp):
    msg = resp.message()
    turnos = cargar_json(TURNOS_FILE)
    mensajes = cargar_json(MENSAJES_FILE)

    if body == "1":
        hoy = datetime.now().strftime("%d/%m/%Y")
        lista = [t for t in turnos if t["fecha"] == hoy]
        msg.body("No hay turnos hoy" if not lista else "\n".join([f"{t['hora']} {t['nombre']} {t['telefono']}" for t in lista]))
        return str(resp)
    if body == "2":
        lista = obtener_turnos_futuros()
        msg.body("No hay próximos turnos" if not lista else "\n".join([f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista]))
        return str(resp)
    if body == "3":
        msg.body("Sin mensajes" if not mensajes else "\n".join([f"{m['nombre']} {m['telefono']}\n{m['mensaje']}" for m in mensajes]))
        return str(resp)
    if body == "4":
        estado[numero] = "TURNO_NOMBRE"
        msg.body("Ingrese nombre y apellido para ingresar turno")
        return str(resp)
    if body == "5":
        msg.body("Función cancelar turno en desarrollo")
        return str(resp)
    if body == "6":
        msg.body("Función bloquear agenda en desarrollo")
        return str(resp)
    if body == "7":
        estado[numero] = "MENU"
        msg.body("Saliendo admin")
        return str(resp)
    msg.body(MENU_ADMIN)
    return str(resp)

# -----------------------------
# HEALTHCHECK
# -----------------------------
@app.route("/")
def home():
    return "E-Bot activo"

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
