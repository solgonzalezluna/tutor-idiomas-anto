import os
from flask import Flask, render_template, request, jsonify
import anthropic

app = Flask(__name__)

# Configuración de la API Key de Anthropic (Claude)
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

SYSTEM_INSTRUCTION = """
Sos un tutor personal de idiomas cálido, empático y reflexivo para Anto.
Tu personalidad combina una estética botánica, astrológica y de bienestar (estilo Pinterest).
Acompañás el aprendizaje de idiomas de forma relajada, usando metáforas suaves y emojis orgánicos (🌿, 🪷, ✨).
Recordás el progreso de las clases anteriores para mantener una continuidad constante y personalizada.
"""

# Memoria de conversación en memoria volátil (estable y sin errores de disco)
chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global chat_history
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"reply": "Por favor escribe un mensaje."}), 400

    try:
        # Guardar mensaje del usuario en el historial volátil
        chat_history.append({"role": "user", "text": user_message})
        
        # Recuperar los últimos 6 mensajes para contexto
        recent_history = chat_history[-6:]
        
        messages_history = []
        for msg in recent_history:
            role = "user" if msg['role'] == "user" else "assistant"
            messages_history.append({"role": role, "content": msg['text']})

        # Llamada oficial a Claude (usando claude-3-5-haiku que es rapidísimo y súper estable)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            system=SYSTEM_INSTRUCTION,
            messages=messages_history
        )
        
        bot_reply = response.content[0].text

        # Guardar respuesta del bot en el historial
        chat_history.append({"role": "bot", "text": bot_reply})

        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        print(f"Error crítico con Claude en /chat: {e}")
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito en la consigna anterior... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)