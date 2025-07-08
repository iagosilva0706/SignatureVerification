import os
import openai
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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

        original_b64 = base64.b64encode(original_file.read()).decode("utf-8")
        amostra_b64 = base64.b64encode(amostra_file.read()).decode("utf-8")

        prompt = (
            "Estas são duas assinaturas manuscritas. Analisa visualmente os traços, a coerência estrutural, proporções e fluidez.\n"
            "Indica:\n- Pontos de semelhança e diferença entre ambas\n- Se parecem assinaturas da mesma pessoa (com explicação)\n"
            "- Dá uma pontuação de similaridade de 0 a 1\n- Classifica como: Provavelmente Legítima, Suspeita ou Provavelmente Falsa.\n"
            "Sê detalhado mas direto."
        )

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "És um perito em grafoscopia e verificação de assinaturas."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{original_b64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{amostra_b64}"}},
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()

        similaridade = re.search(r"Pontuação\s+de\s+Similaridade.*?[-–—]?\s*\**(\d(?:\.\d+)?)", output, re.IGNORECASE)
        classificacao = re.search(r"Classifica(?:do|ção).*?:\s*[-–—]?\s*\**(.*)", output, re.IGNORECASE)

        resultado = {
            "analise": output,
            "similaridade": similaridade.group(1) if similaridade else "Não extraída",
            "classificacao": classificacao.group(1).strip() if classificacao else "Não extraída"
        }

        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "resultado": resultado
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
