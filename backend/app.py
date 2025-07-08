import os
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs/verificacoes.jsonl"
os.makedirs("logs", exist_ok=True)

@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files.get("original")
        amostra_file = request.files.get("amostra")

        if not original_file or not amostra_file:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

        # Converter imagens para base64
        original_b64 = base64.b64encode(original_file.read()).decode("utf-8")
        amostra_b64 = base64.b64encode(amostra_file.read()).decode("utf-8")

        # Prompt atualizado
        prompt = (
            "Compare visually two handwritten signature images. "
            "Analyze carefully the stroke pressure and thickness, writing rhythm and fluidity, proportions between letters, overall slant, spacing, and consistency of graphical style. "
            "Pay close attention to any signs of forgery, such as unnatural tremors, hesitation marks, inconsistent pressure, interrupted flow, or abnormal angularity.\n"
            "Provide your analysis in the following JSON format:\n"
            "{\n"
            "  \"similarity_score\": \"<value between 0.00 and 1.00>\",\n"
            "  \"classification\": \"<Very Similar | Somewhat Different | Clearly Different>\",\n"
            "  \"analysis\": \"<objective and detailed explanation>\"\n"
            "}\n"
            "Be strict in your assessment: if there are clear differences in style, structure, or fluency, reduce the similarity score and explain why."
)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a handwriting forensics expert specializing in signature verification."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{original_b64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{amostra_b64}"}},
                    ]
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )

        output_raw = response.choices[0].message.content.strip()

        try:
            resultado = json.loads(output_raw)
        except json.JSONDecodeError:
            resultado = {
                "similaridade": "Not extracted",
                "classificacao": "Not extracted",
                "analise": output_raw
            }

        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "resultado": resultado
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"erro": f"Internal error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
