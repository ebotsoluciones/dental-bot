// server.js - Dental Bot / WhatsApp Cloud API sin Express

const http = require("http");
const url = require("url");

// Token de verificación definido en WhatsApp Cloud API
const VERIFY_TOKEN = "ebot-token";

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // -------------------------------
  // GET /webhook → Verificación Meta
  // -------------------------------
  if (req.method === "GET" && pathname === "/webhook") {
    const query = parsedUrl.query;
    if (query["hub.mode"] && query["hub.verify_token"] === VERIFY_TOKEN) {
      console.log("Recibido GET /webhook");
      res.writeHead(200, { "Content-Type": "text/plain" });
      res.end(query["hub.challenge"]);
    } else {
      res.writeHead(403);
      res.end("Forbidden");
    }
    return;
  }

  // -------------------------------
  // POST /webhook → Recepción de eventos
  // -------------------------------
  if (req.method === "POST" && pathname === "/webhook") {
    let body = "";
    req.on("data", chunk => { body += chunk.toString(); });
    req.on("end", () => {
      try {
        const data = JSON.parse(body);
        console.log("Recibido POST /webhook");
        console.log("Evento recibido:", data);
      } catch (err) {
        console.log("Error parseando body:", err);
      }
      res.writeHead(200);
      res.end("EVENT_RECEIVED");
    });
    return;
  }

  // -------------------------------
  // Cualquier otro método / ruta
  // -------------------------------
  res.writeHead(405, { "Content-Type": "text/plain" });
  res.end("Método no permitido");
});

// Puerto dinámico de Railway
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`Server listening on port ${PORT}`));
