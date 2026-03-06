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
ESTADO_FILE = "estado.json"

# -----------------------------
# UTILIDADES JSON
# -----------------------------

def cargar_json(path):

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def guardar_json(path, data):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# -----------------------------
# ESTADO PERSISTENTE
# -----------------------------

estado = cargar_json(ESTADO_FILE)

def set_estado(numero, valor):

    estado[numero] = valor
    guardar_json(ESTADO_FILE, estado)

def get_estado(numero):

    return estado.get(numero, "MENU")

# -----------------------------
# MENUS
# -----------------------------

MENU_PACIENTE = """
🦙 E-Bot Lite

1 Turno
2 Mensaje
3 Urgencia
4 Informes
5 Salir

Escriba número
"""

MENU_ADMIN = """
🛠 ADMIN

1 Turnos del día
2 Agenda semanal
3 Ver turnos futuros
4 Agregar turno
5 Cancelar turno
6 Ver mensajes
7 Mensajes no leídos
8 Salir
"""

# -----------------------------
# DATOS
# -----------------------------

def cargar_turnos():

    data = cargar_json(TURNOS_FILE)
    return data if isinstance(data, list) else []

def guardar_turnos(data):

    guardar_json(TURNOS_FILE, data)

def cargar_mensajes():

    data = cargar_json(MENSAJES_FILE)
    return data if isinstance(data, list) else []

def guardar_mensajes(data):

    guardar_json(MENSAJES_FILE, data)

# -----------------------------
# FUNCIONES
# -----------------------------

def guardar_turno(numero, fecha):

    turnos = cargar_turnos()

    turnos.append({
        "numero": numero,
        "fecha": fecha,
        "hora": "00:00"
    })

    guardar_turnos(turnos)

def guardar_mensaje(numero, texto):

    mensajes = cargar_mensajes()

    mensajes.append({
        "numero": numero,
        "mensaje": texto,
        "fecha": datetime.now().isoformat(),
        "leido": False
    })

    guardar_mensajes(mensajes)

# -----------------------------
# WEBHOOK
# -----------------------------

@app.route("/webhook", methods=["POST"])
def webhook():

    numero = request.values.get("From")
    body = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    estado_usuario = get_estado(numero)

    # -----------------------------
    # ACCESO ADMIN
    # -----------------------------

    if body.lower() in ["admin","adm"]:

        set_estado(numero,"ADMIN")

        msg.body(MENU_ADMIN)

        return str(resp)

    # -----------------------------
    # TURNO PACIENTE
    # -----------------------------

    if estado_usuario == "TURNO":

        try:

            datetime.strptime(body,"%d/%m/%Y")

            guardar_turno(numero,body)

            set_estado(numero,"MENU")

            msg.body(f"✅ Turno solicitado para {body}")

        except:

            msg.body("Formato inválido. Use dd/mm/yyyy")

        return str(resp)

    # -----------------------------
    # MENSAJE PACIENTE
    # -----------------------------

    if estado_usuario == "MENSAJE":

        guardar_mensaje(numero,body)

        set_estado(numero,"MENU")

        msg.body("📩 Mensaje recibido")

        return str(resp)

    # -----------------------------
    # ADMIN
    # -----------------------------

    if estado_usuario == "ADMIN":

        if body == "1":

            hoy = datetime.now().strftime("%d/%m/%Y")

            turnos = [t for t in cargar_turnos() if t["fecha"] == hoy]

            if not turnos:

                msg.body("No hay turnos hoy")

            else:

                texto="\n".join([t["numero"] for t in turnos])

                msg.body(texto)

            return str(resp)

        if body == "2":

            limite = datetime.now()+timedelta(days=7)

            turnos=[t for t in cargar_turnos()
                if datetime.strptime(t["fecha"],"%d/%m/%Y") <= limite]

            if not turnos:

                msg.body("Agenda vacía")

            else:

                texto="\n".join([f"{t['fecha']} {t['numero']}" for t in turnos])

                msg.body(texto)

            return str(resp)

        if body == "3":

            hoy=datetime.now()

            turnos=[t for t in cargar_turnos()
                if datetime.strptime(t["fecha"],"%d/%m/%Y") > hoy]

            if not turnos:

                msg.body("No hay turnos futuros")

            else:

                texto="\n".join([f"{t['fecha']} {t['numero']}" for t in turnos])

                msg.body(texto)

            return str(resp)

        if body == "6":

            mensajes=cargar_mensajes()

            if not mensajes:

                msg.body("Sin mensajes")

            else:

                texto="\n".join([f"{m['numero']}: {m['mensaje']}" for m in mensajes])

                msg.body(texto)

                for m in mensajes:
                    m["leido"]=True

                guardar_mensajes(mensajes)

            return str(resp)

        if body == "7":

            mensajes=[m for m in cargar_mensajes() if not m["leido"]]

            if not mensajes:

                msg.body("Sin mensajes nuevos")

            else:

                texto="\n".join([f"{m['numero']}: {m['mensaje']}" for m in mensajes])

                msg.body(texto)

            return str(resp)

        if body == "8":

            set_estado(numero,"MENU")

            msg.body("Saliendo admin")

            return str(resp)

        msg.body(MENU_ADMIN)

        return str(resp)

    # -----------------------------
    # MENU
    # -----------------------------

    if body.lower() in ["menu","hola","start","/start"]:

        set_estado(numero,"MENU")

        msg.body(MENU_PACIENTE)

        return str(resp)

    if estado_usuario == "MENU":

        if body == "1":

            set_estado(numero,"TURNO")

            msg.body("Ingrese fecha turno dd/mm/yyyy")

            return str(resp)

        if body == "2":

            set_estado(numero,"MENSAJE")

            msg.body("Escriba su mensaje")

            return str(resp)

        if body == "3":

            msg.body("Urgencias +549000000000")

            return str(resp)

        if body == "4":

            msg.body("Informes en desarrollo")

            return str(resp)

        if body == "5":

            msg.body("Gracias. Escriba MENU para volver")

            return str(resp)

        msg.body(MENU_PACIENTE)

        return str(resp)

    msg.body("Escriba MENU para comenzar")

    return str(resp)


# -----------------------------
# SERVER
# -----------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
