from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    resp = MessagingResponse()
    resp.message("🦙 E-Bot Lite prueba")
    return str(resp)

@app.route("/")
def home():
    return "E-Bot activo"

if __name__ == "__main__":
    app.run(host="0.0.0.0")
