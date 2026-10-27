import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------
# ¿Con qué IA conversa el tutor? Se elige con variables en Render:
#   AI_PROVIDER = gemini   (por defecto, tiene plan gratuito)
#   AI_PROVIDER = claude   (cuando quieras pasarte a Claude)
# Las llaves también van en Render, nunca en el código:
#   GEMINI_API_KEY   /   ANTHROPIC_API_KEY
# ---------------------------------------------------------------
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()

# Los modelos se retiran cada tanto. Si uno deja de funcionar, no hace falta tocar el
# código: basta cambiar GEMINI_MODEL o CLAUDE_MODEL en Render.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")

print(f"Tutor iniciado con proveedor: {AI_PROVIDER}")

SYSTEM_INSTRUCTION = """
Sos un tutor personal de idiomas cálido, empático y reflexivo para Anto.
Tu personalidad combina una estética botánica, astrológica y de bienestar (estilo Pinterest).
Acompañás el aprendizaje de idiomas de forma relajada, usando metáforas suaves y emojis orgánicos (🌿, 🪷, ✨).
Recordás el progreso de las clases anteriores para mantener una continuidad constante y personalizada.

Anto habla español (rioplatense) y está aprendiendo inglés. Sos su tutor de inglés:
conversá con ella en español, introducí inglés de a poco y animala a practicar en voz alta y a responderte en inglés.
Corregí con suavidad, explicando brevemente el porqué, y celebrá sus avances.

IMPORTANTE: tus respuestas se leen en voz alta, así que:
- Escribí frases cortas y naturales, como si estuvieras hablando. Máximo 4 o 5 frases por respuesta.
- No uses markdown (nada de asteriscos, listas, títulos ni tablas). Usá a lo sumo 1 o 2 emojis.
- Cada vez que escribas algo en inglés (palabras, frases de ejemplo, preguntas para que ella practique),
  envolvelo entre las etiquetas <en> y </en>, por ejemplo: Probá decir <en>How are you today?</en>
  Todo lo que NO esté entre esas etiquetas se lee con voz en español.
- Nunca uses esas etiquetas para texto en español.
"""

# Memoria de conversación en memoria volátil
chat_history = []
MAX_HISTORY = 6

# Los clientes se crean la primera vez que se usan (así no hace falta tener las dos llaves)
_clients = {}


@app.route("/")
def index():
    return render_template("index.html")


def build_messages():
    """Arma la lista de mensajes: debe empezar con 'user'. Roles: 'user' y 'assistant'."""
    recent = chat_history[-MAX_HISTORY:]
    # Las APIs exigen que el primer mensaje sea del usuario
    while recent and recent[0]["role"] != "user":
        recent = recent[1:]
    return [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["text"]}
        for m in recent
    ]


def ask_gemini(messages):
    from google import genai
    from google.genai import types

    if "gemini" not in _clients:
        _clients["gemini"] = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # Gemini llama "model" a lo que Claude llama "assistant"
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]

    response = _clients["gemini"].models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            # Más margen que con Claude: los modelos Gemini "piensan" y eso consume tokens
            max_output_tokens=1500,
        ),
    )

    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini devolvió una respuesta vacía (bloqueo de seguridad o límite de tokens)")
    return text


def ask_claude(messages):
    import anthropic

    if "claude" not in _clients:
        _clients["claude"] = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = _clients["claude"].messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=SYSTEM_INSTRUCTION,
        messages=messages,
    )
    return response.content[0].text


def ask_ai(messages):
    if AI_PROVIDER == "claude":
        return ask_claude(messages)
    if AI_PROVIDER == "gemini":
        return ask_gemini(messages)
    raise ValueError(f"AI_PROVIDER inválido: '{AI_PROVIDER}'. Usá 'gemini' o 'claude'.")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Por favor escribe un mensaje."}), 400

    chat_history.append({"role": "user", "text": user_message})

    try:
        bot_reply = ask_ai(build_messages())
        chat_history.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})

    except Exception as e:
        # Si falla, sacamos el mensaje del usuario para no dejar el historial desalineado
        chat_history.pop()
        # Este print aparece en los Logs de Render con el error real
        print(f"Error crítico con {AI_PROVIDER} en /chat: {type(e).__name__}: {e}")
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito en la consigna anterior... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
