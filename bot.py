"""
E-BOT LITE 🦙
Bot WhatsApp con Twilio + Flask

Funciones
---------
Paciente
- Solicitar turno
- Enviar mensaje
- Urgencia
- Informes

Administrador
- Turnos del día
- Agenda semanal
- Turnos futuros
- Agregar turno manual
- Cancelar turno
- Ver mensajes
- Mensajes no leídos
- Bloquear día

Agenda
------
Horario: 09:00 a 19:00
Intervalo: 30 minutos
"""

import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"
BLOQUEOS_FILE = "bloqueos.json"

estado = {}

# --------------------------------
# JSON helpers
# --------------------------------

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

# --------------------------------
# Horarios
# --------------------------------

def generar_horarios():

    horarios = []

    inicio = datetime.strptime("09:00", "%H:%M")
    fin = datetime.strptime("19:00", "%H:%M")

    actual = inicio

    while actual <= fin:

        horarios.append(actual.strftime("%H:%M"))

        actual += timedelta(minutes=30)

    return horarios

# --------------------------------
# Buscar horario libre
# --------------------------------

def buscar_horario_libre(fecha):

    turnos = cargar_json(TURNOS_FILE)

    horarios = generar_horarios()

    ocupados = [
        t["hora"] for t in turnos if t["fecha"] == fecha
    ]

    for h in horarios:

        if h not in ocupados:
            return h

    return None

# --------------------------------
# MENUS
# --------------------------------

MENU_PACIENTE = """
🦙 E-Bot Lite

1 Turno
2 Mensaje
3 Urgencia
4 Informes
5 Salir

Escriba opción
"""

MENU_ADMIN = """
🛠 ADMIN

1 Turnos del día
2 Agenda semanal
3 Turnos futuros
4 Agregar turno
5 Cancelar turno
6 Ver mensajes
7 Mensajes no leídos
8 Bloquear día
9 Salir
"""

# --------------------------------
# WEBHOOK
# --------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():

    numero = request.values.get("From")
    body = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    est = estado.get(numero, "MENU")

    texto = body.lower()

    # ---- ADMIN ----

    if texto in ["admin", "administrador"]:

        estado[numero] = "ADMIN"

        msg.body(MENU_ADMIN)

        return str(resp)

    # ---- MENU ----

    if texto in ["menu", "/start"]:

        estado[numero] = "MENU"

        msg.body(MENU_PACIENTE)

        return str(resp)

    # ---- ADMIN FLOW ----

    if est == "ADMIN":

        return manejar_admin(numero, body, resp)

    # ---- PACIENTE FLOW ----

    if est == "MENU":

        return manejar_menu(numero, body, resp)

    if est == "TURNO_NOMBRE":

        estado[numero] = "TURNO_FECHA"

        estado[numero+"_nombre"] = body

        msg.body("Ingrese fecha (dd/mm/yyyy)")

        return str(resp)

    if est == "TURNO_FECHA":

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

            "nombre": estado[numero+"_nombre"],
            "telefono": numero,
            "fecha": body,
            "hora": hora

        })

        guardar_json(TURNOS_FILE, turnos)

        estado[numero] = "MENU"

        msg.body(f"Turno confirmado\n{body} {hora}")

        return str(resp)

    if est == "MENSAJE_NOMBRE":

        estado[numero+"_nombre"] = body

        estado[numero] = "MENSAJE_TEXTO"

        msg.body("Escriba su mensaje")

        return str(resp)

    if est == "MENSAJE_TEXTO":

        mensajes = cargar_json(MENSAJES_FILE)

        mensajes.append({

            "nombre": estado[numero+"_nombre"],
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

# --------------------------------
# MENU PACIENTE
# --------------------------------

def manejar_menu(numero, body, resp):

    msg = resp.message()

    if body == "1":

        estado[numero] = "TURNO_NOMBRE"

        msg.body("Ingrese nombre y apellido")

        return str(resp)

    if body == "2":

        estado[numero] = "MENSAJE_NOMBRE"

        msg.body("Nombre y apellido")

        return str(resp)

    if body == "3":

        msg.body("Urgencias: +549000000000")

        return str(resp)

    if body == "4":

        msg.body("Informes en desarrollo")

        return str(resp)

    if body == "5":

        estado[numero] = "MENU"

        msg.body("Hasta pronto. Escriba MENU")

        return str(resp)

    msg.body(MENU_PACIENTE)

    return str(resp)

# --------------------------------
# ADMIN
# --------------------------------

def manejar_admin(numero, body, resp):

    msg = resp.message()

    turnos = cargar_json(TURNOS_FILE)

    mensajes = cargar_json(MENSAJES_FILE)

    hoy = datetime.now().strftime("%d/%m/%Y")

    # 1

    if body == "1":

        lista = [t for t in turnos if t["fecha"] == hoy]

        if not lista:

            msg.body("No hay turnos hoy")

        else:

            texto = "\n".join(

                [f"{t['hora']} {t['nombre']} {t['telefono']}" for t in lista]

            )

            msg.body(texto)

        return str(resp)

    # 2

    if body == "2":

        limite = datetime.now() + timedelta(days=7)

        lista = [

            t for t in turnos

            if datetime.strptime(t["fecha"], "%d/%m/%Y") <= limite

        ]

        if not lista:

            msg.body("Agenda vacía")

        else:

            texto = "\n".join(

                [f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista]

            )

            msg.body(texto)

        return str(resp)

    # 3

    if body == "3":

        hoy_dt = datetime.now()

        lista = [

            t for t in turnos

            if datetime.strptime(t["fecha"], "%d/%m/%Y") > hoy_dt

        ]

        if not lista:

            msg.body("No hay turnos futuros")

        else:

            texto = "\n".join(

                [f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista]

            )

            msg.body(texto)

        return str(resp)

    # 4 agregar turno

    if body == "4":

        msg.body("Agregar turno manual aún en desarrollo")

        return str(resp)

    # 5 cancelar

    if body == "5":

        msg.body("Cancelar turno aún en desarrollo")

        return str(resp)

    # 6 mensajes

    if body == "6":

        if not mensajes:

            msg.body("Sin mensajes")

        else:

            texto = "\n".join(

                [f"{m['nombre']} {m['telefono']}\n{m['mensaje']}" for m in mensajes]

            )

            msg.body(texto)

        return str(resp)

    # 7 nuevos

    if body == "7":

        nuevos = [m for m in mensajes if not m["leido"]]

        if not nuevos:

            msg.body("Sin mensajes nuevos")

        else:

            texto = "\n".join(

                [f"{m['nombre']} {m['telefono']}\n{m['mensaje']}" for m in nuevos]

            )

            msg.body(texto)

        return str(resp)

    # 8 bloquear

    if body == "8":

        msg.body("Bloqueo aún en desarrollo")

        return str(resp)

    # 9 salir

    if body == "9":

        estado[numero] = "MENU"

        msg.body("Saliendo admin")

        return str(resp)

    msg.body(MENU_ADMIN)

    return str(resp)

# --------------------------------
# RUN
# --------------------------------

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)
