# backend/app.py
import os
import openai
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
        original = request.files.get("original")
        amostra = request.files.get("amostra")
        if not original or not amostra:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

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
                        {"type": "image", "image": {"source": {"type": "file", "file": original.stream.read()}}},
                        {"type": "image", "image": {"source": {"type": "file", "file": amostra.stream.read()}}},
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()
        similaridade = extrair_valor(output, r"similaridade.*?(\d\.\d{2})")
        classificacao = extrair_valor(output, r"Classifica(?:do|ção).*?:\s*(.*)")

        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "resultado": {
                "analise": output,
                "similaridade": similaridade or "Não extraída",
                "classificacao": classificacao or "Não extraída"
            }
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(str(log) + "\n")

        return jsonify(log["resultado"])

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

def extrair_valor(texto, padrao):
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(1).strip() if match else None

if __name__ == "__main__":
    app.run(debug=True, port=5000)
