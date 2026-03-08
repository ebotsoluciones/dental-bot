const express = require("express");
const app = express();
app.use(express.json());

const VERIFY_TOKEN = "ebot-token";

app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  if (mode && token === VERIFY_TOKEN) {
    return res.status(200).send(challenge);
  } else {
    return res.sendStatus(403);
  }
});

app.post("/webhook", (req, res) => {
  console.log("Evento recibido:", req.body);
  res.sendStatus(200);
});

app.listen(process.env.PORT || 3000);
