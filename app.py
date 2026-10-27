import os
from flask import Flask, render_template, request, jsonify
import anthropic

app = Flask(__name__)

# Configuración de la API Key de Anthropic (Claude)
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ATENCIÓN: falta la variable de entorno ANTHROPIC_API_KEY en Render.")
client = anthropic.Anthropic(api_key=api_key)

# Modelo vigente (claude-3-5-haiku-20241022 fue retirado en febrero de 2026)
MODEL = "claude-haiku-5-5"

SYSTEM_INSTRUCTION = """
Sos un tutor personal de idiomas cálido, empático y reflexivo para Anto.
Tu personalidad combina una estética botánica, astrológica y de bienestar (estilo Pinterest).
Acompañás el aprendizaje de idiomas de forma relajada, usando metáforas suaves y emojis orgánicos (🌿, 🪷, ✨).
Recordás el progreso de las clases anteriores para mantener una continuidad constante y personalizada.
"""

# Memoria de conversación en memoria volátil
chat_history = []
MAX_HISTORY = 6


@app.route("/")
def index():
    return render_template("index.html")


def build_messages():
    """Arma la lista de mensajes para la API: debe empezar con 'user' y alternar roles."""
    recent = chat_history[-MAX_HISTORY:]
    # La API exige que el primer mensaje sea del usuario
    while recent and recent[0]["role"] != "user":
        recent = recent[1:]
    return [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["text"]}
        for m in recent
    ]


@app.route("/chat", methods=["POST"])
def chat():
    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Por favor escribe un mensaje."}), 400

    chat_history.append({"role": "user", "text": user_message})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM_INSTRUCTION,
            messages=build_messages(),
        )

        bot_reply = response.content[0].text
        chat_history.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})

    except Exception as e:
        # Si falla, sacamos el mensaje del usuario para no dejar el historial desalineado
        chat_history.pop()
        # Este print aparece en los Logs de Render con el error real
        print(f"Error crítico con Claude en /chat: {type(e).__name__}: {e}")
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito en la consigna anterior... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
