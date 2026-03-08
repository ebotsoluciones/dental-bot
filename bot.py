import json
import os
import requests
from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"
BLOQUEOS_FILE = "agenda_config.json"

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

estado = {}

ADMINS = [
    "5493515645624"
]

MENU_PACIENTE = """
🦙 E-Bot Lite

🔢 1 Turno
🔢 2 Consultar mi turno
🔢 3 Mensaje 📩
🔢 4 Urgencia 🚑
🔢 5 Informes
🔢 6 Salir
"""

MENU_ADMIN = """
🛠 ADMIN

🔢 1 Turnos del día
🔢 2 Próximos turnos
🔢 3 Ver mensajes
🔢 4 Ingresar turno
🔢 5 Cancelar turno
🔢 6 Bloquear agenda
🔢 7 Salir
"""


# ---------------- MENSAJES WHATSAPP ----------------

def enviar(numero, texto):

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }

    requests.post(url, headers=headers, json=payload)


# ---------------- JSON ----------------

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


# ---------------- HORARIOS ----------------

def generar_horarios():

    horarios = []

    inicio = datetime.strptime("09:00", "%H:%M")
    fin = datetime.strptime("19:00", "%H:%M")

    actual = inicio

    while actual <= fin:

        horarios.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=30)

    return horarios


# ---------------- TURNOS FUTUROS ----------------

def obtener_turnos_futuros():

    hoy = datetime.now().date()
    turnos = cargar_json(TURNOS_FILE)

    futuros = [
        t for t in turnos
        if datetime.strptime(t["fecha"], "%d/%m/%Y").date() >= hoy
    ]

    return sorted(futuros, key=lambda x: (x["fecha"], x["hora"]))


# ---------------- BLOQUEOS ----------------

def horario_bloqueado(fecha, hora):

    bloqueos = cargar_json(BLOQUEOS_FILE)

    for b in bloqueos:

        if b["fecha"] == fecha and b["hora"] == hora:
            return True

    return False


# ---------------- WEBHOOK ----------------

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    try:

        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]
        body = mensaje["text"]["body"].strip()

    except:

        return "ok"

    procesar(numero, body)

    return "ok"


# ---------------- PROCESAR ----------------

def procesar(numero, body):

    texto = body.lower()

    estado.setdefault(numero, "MENU")
    estado_actual = estado[numero]

    # MENU
    if texto in ["menu", "hola", "/start"]:

        estado[numero] = "MENU"

        if numero in ADMINS:
            enviar(numero, MENU_ADMIN)
        else:
            enviar(numero, MENU_PACIENTE)

        return

    # ADMIN
    if texto in ["admin", "adm"]:

        estado[numero] = "ADMIN"
        enviar(numero, MENU_ADMIN)
        return

    # ADMIN FLOW
    if estado_actual == "ADMIN" and numero in ADMINS:

        manejar_admin(numero, body)
        return

    # PACIENTE MENU
    if estado_actual == "MENU":

        manejar_menu(numero, body)
        return

    # TURNO NOMBRE
    if estado_actual == "TURNO_NOMBRE":

        estado[numero + "_nombre"] = body
        estado[numero] = "TURNO_FECHA"

        enviar(numero, "Ingrese fecha (dd/mm/yyyy)")
        return

    # TURNO FECHA
    if estado_actual == "TURNO_FECHA":

        try:
            fecha = datetime.strptime(body, "%d/%m/%Y").date()

        except:
            enviar(numero, "Formato inválido")
            return

        if fecha < datetime.now().date():

            enviar(numero, "Fecha pasada")
            return

        estado[numero + "_fecha"] = body
        estado[numero] = "TURNO_HORA"

        horarios = generar_horarios()

        turnos = cargar_json(TURNOS_FILE)

        ocupados = [t["hora"] for t in turnos if t["fecha"] == body]

        libres = [
            h for h in horarios
            if h not in ocupados and not horario_bloqueado(body, h)
        ]

        if not libres:

            enviar(numero, "No hay horarios disponibles")
            estado[numero] = "MENU"
            return

        enviar(numero, "Elija hora:\n" + "\n".join(libres))
        return

    # TURNO HORA
    if estado_actual == "TURNO_HORA":

        hora = body.strip()

        horarios = generar_horarios()

        if hora not in horarios:

            enviar(numero, "Hora inválida")
            return

        fecha = estado[numero + "_fecha"]

        if horario_bloqueado(fecha, hora):

            enviar(numero, "Horario bloqueado")
            return

        turnos = cargar_json(TURNOS_FILE)

        if any(t["fecha"] == fecha and t["hora"] == hora for t in turnos):

            enviar(numero, "Hora ocupada")
            return

        turnos.append({

            "nombre": estado[numero + "_nombre"],
            "telefono": numero,
            "fecha": fecha,
            "hora": hora

        })

        guardar_json(TURNOS_FILE, turnos)

        enviar(numero, f"✅ Turno confirmado\n{fecha} {hora}")

        estado[numero] = "MENU"

        return


# ---------------- MENU PACIENTE ----------------

def manejar_menu(numero, body):

    if body == "1":

        estado[numero] = "TURNO_NOMBRE"
        enviar(numero, "Ingrese nombre y apellido")
        return

    if body == "2":

        turnos = cargar_json(TURNOS_FILE)

        lista = [t for t in turnos if t["telefono"] == numero]

        if not lista:

            enviar(numero, "No se encontraron turnos")

        else:

            salida = "\n".join(
                [f"{t['fecha']} {t['hora']}" for t in lista]
            )

            enviar(numero, f"📅 Sus turnos:\n{salida}")

        return

    if body == "3":

        estado[numero] = "MENSAJE_NOMBRE"
        enviar(numero, "Nombre y apellido")
        return

    if body == "4":

        enviar(numero, "Urgencias 🚑: +549000000000")
        return

    if body == "5":

        enviar(numero,
"""
📄 Informes

🕒 Horario: 08:00 – 18:00
🏥 Obras sociales: Sí
"""
)

        return

    if body == "6":

        enviar(numero, "Hasta pronto. Escriba MENU para volver")
        return

    enviar(numero, MENU_PACIENTE)


# ---------------- ADMIN ----------------

def manejar_admin(numero, body):

    turnos = cargar_json(TURNOS_FILE)
    mensajes = cargar_json(MENSAJES_FILE)

    if body == "1":

        hoy = datetime.now().strftime("%d/%m/%Y")

        lista = [t for t in turnos if t["fecha"] == hoy]

        if not lista:

            enviar(numero, "No hay turnos hoy")

        else:

            salida = "\n".join(
                [f"{t['hora']} {t['nombre']} {t['telefono']}" for t in lista]
            )

            enviar(numero, salida)

        return

    if body == "2":

        lista = obtener_turnos_futuros()

        if not lista:

            enviar(numero, "No hay próximos turnos")

        else:

            salida = "\n".join(
                [f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista]
            )

            enviar(numero, salida)

        return

    if body == "3":

        if not mensajes:

            enviar(numero, "Sin mensajes")

        else:

            salida = "\n".join(
                [f"{m['nombre']} {m['mensaje']}" for m in mensajes]
            )

            enviar(numero, salida)

        return

    if body == "6":

        estado[numero] = "BLOQUEO_FECHA"

        enviar(numero, "Ingrese fecha a bloquear (dd/mm/yyyy)")
        return

    if body == "7":

        estado[numero] = "MENU"
        enviar(numero, "Saliendo admin")
        return

    enviar(numero, MENU_ADMIN)


# ---------------- HEALTH ----------------

@app.route("/")
def home():

    return "E-Bot activo"


# ---------------- RUN ----------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)
