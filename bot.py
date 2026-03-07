import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

estado = {}

ADMINS = [
"whatsapp:+549XXXXXXXXXX"
]

# -----------------------------
# JSON
# -----------------------------

def cargar_json(path):
    if not os.path.exists(path):
        return []
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def guardar_json(path,data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)

# -----------------------------
# horarios
# -----------------------------

def generar_horarios():

    horarios=[]
    inicio=datetime.strptime("09:00","%H:%M")
    fin=datetime.strptime("19:00","%H:%M")

    actual=inicio

    while actual<=fin:
        horarios.append(actual.strftime("%H:%M"))
        actual+=timedelta(minutes=30)

    return horarios


def buscar_horario_libre(fecha):

    turnos=cargar_json(TURNOS_FILE)
    horarios=generar_horarios()

    ocupados=[t["hora"] for t in turnos if t["fecha"]==fecha]

    for h in horarios:
        if h not in ocupados:
            return h

    return None


# -----------------------------
# menus
# -----------------------------

MENU_PACIENTE="""
🦙 E-Bot Lite

1 Turno
2 Consultar mi turno
3 Mensaje 📩
4 Urgencia 🚑
5 Informes
6 Salir

Escriba opción
"""

MENU_ADMIN="""
🛠 ADMIN

1 Turnos de hoy
2 Próximos turnos
3 Ver mensajes

4 Ingresar turno
5 Cancelar turno
6 Bloquear agenda

7 Salir
"""

# -----------------------------
# WEBHOOK
# -----------------------------

@app.route("/webhook",methods=["POST"])
def webhook():

    numero=request.values.get("From")
    body=request.values.get("Body","").strip()
    texto=body.lower()

    resp=MessagingResponse()
    msg=resp.message()

    estado.setdefault(numero,"MENU")
    estado_actual=estado[numero]

    es_admin=numero in ADMINS

    # comandos generales

    if texto in ["menu","menú","/start"]:
        estado[numero]="ADMIN" if es_admin else "MENU"
        msg.body(MENU_ADMIN if es_admin else MENU_PACIENTE)
        return str(resp)

    # -------------------------
    # ADMIN
    # -------------------------

    if estado_actual=="ADMIN":

        turnos=cargar_json(TURNOS_FILE)
        mensajes=cargar_json(MENSAJES_FILE)

        if body=="1":

            hoy=datetime.now().strftime("%d/%m/%Y")

            lista=[t for t in turnos if t["fecha"]==hoy]

            if not lista:
                msg.body("No hay turnos hoy")
            else:
                txt="\n".join([f"{t['hora']} {t['nombre']}" for t in lista])
                msg.body(txt)

            return str(resp)

        if body=="2":

            hoy=datetime.now().date()

            lista=[t for t in turnos if datetime.strptime(t["fecha"],"%d/%m/%Y").date()>=hoy]

            lista=sorted(lista,key=lambda x:(x["fecha"],x["hora"]))

            if not lista:
                msg.body("Agenda vacía")
            else:
                txt="\n".join([f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista])
                msg.body(txt)

            return str(resp)

        if body=="3":

            if not mensajes:
                msg.body("Sin mensajes")
            else:
                txt="\n\n".join([f"{m['nombre']}\n{m['mensaje']}" for m in mensajes])
                msg.body(txt)

            return str(resp)

        if body=="7":
            estado[numero]="MENU"
            msg.body("Saliendo admin")
            return str(resp)

        msg.body(MENU_ADMIN)
        return str(resp)

    # -------------------------
    # MENU PACIENTE
    # -------------------------

    if estado_actual=="MENU":

        if body=="1":
            estado[numero]="TURNO_NOMBRE"
            msg.body("Ingrese nombre y apellido")
            return str(resp)

        if body=="2":

            turnos=cargar_json(TURNOS_FILE)

            lista=[t for t in turnos if t["telefono"]==numero]

            if not lista:
                estado[numero]="CONSULTA_TURNO"
                msg.body("No encontramos turno.\n\nEnvíe:\nNombre y apellido\nMotivo del mensaje")
                return str(resp)

            txt="\n".join([f"{t['fecha']} {t['hora']}" for t in lista])
            msg.body(f"Sus turnos:\n{txt}")

            return str(resp)

        if body=="3":
            estado[numero]="MENSAJE_NOMBRE"
            msg.body("Nombre y apellido")
            return str(resp)

        if body=="4":
            msg.body("Urgencias: +549XXXXXXXXXX")
            return str(resp)

        if body=="5":
            msg.body("Informes en desarrollo")
            return str(resp)

        if body=="6":
            msg.body("Hasta pronto. Escriba MENU")
            return str(resp)

        msg.body(MENU_PACIENTE)
        return str(resp)

    # -------------------------
    # TURNO
    # -------------------------

    if estado_actual=="TURNO_NOMBRE":

        estado[numero+"_nombre"]=body
        estado[numero]="TURNO_FECHA"

        msg.body("Ingrese fecha (dd/mm/yyyy)")
        return str(resp)

    if estado_actual=="TURNO_FECHA":

        try:
            datetime.strptime(body,"%d/%m/%Y")
        except:
            msg.body("Formato inválido. Use dd/mm/yyyy")
            return str(resp)

        hora=buscar_horario_libre(body)

        if not hora:
            msg.body("Día completo. Intente otra fecha")
            return str(resp)

        turnos=cargar_json(TURNOS_FILE)

        turnos.append({
        "nombre":estado[numero+"_nombre"],
        "telefono":numero,
        "fecha":body,
        "hora":hora
        })

        guardar_json(TURNOS_FILE,turnos)

        estado[numero]="MENU"

        msg.body(f"✅ Turno confirmado\n{estado[numero+'_nombre']}\n{body} {hora}")

        return str(resp)

    # -------------------------
    # MENSAJES
    # -------------------------

    if estado_actual=="MENSAJE_NOMBRE":

        estado[numero+"_nombre"]=body
        estado[numero]="MENSAJE_TEXTO"

        msg.body("Escriba su mensaje")
        return str(resp)

    if estado_actual=="MENSAJE_TEXTO":

        mensajes=cargar_json(MENSAJES_FILE)

        mensajes.append({
        "nombre":estado[numero+"_nombre"],
        "telefono":numero,
        "mensaje":body,
        "fecha":datetime.now().isoformat()
        })

        guardar_json(MENSAJES_FILE,mensajes)

        estado[numero]="MENU"

        msg.body("Mensaje recibido")

        return str(resp)

    # -------------------------
    # CONSULTA TURNO
    # -------------------------

    if estado_actual=="CONSULTA_TURNO":

        mensajes=cargar_json(MENSAJES_FILE)

        mensajes.append({
        "nombre":"Consulta turno",
        "telefono":numero,
        "mensaje":body,
        "fecha":datetime.now().isoformat()
        })

        guardar_json(MENSAJES_FILE,mensajes)

        estado[numero]="MENU"

        msg.body("Consulta enviada al profesional")

        return str(resp)

    return str(resp)


# -----------------------------
# healthcheck
# -----------------------------

@app.route("/")
def home():
    return "E-Bot activo"


# -----------------------------
# run
# -----------------------------

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
