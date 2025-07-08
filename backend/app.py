import os
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import re
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

        # Converter para base64
        original_base64 = base64.b64encode(original_file.read()).decode("utf-8")
        amostra_base64 = base64.b64encode(amostra_file.read()).decode("utf-8")

        prompt = (
            "Analisa duas imagens de assinaturas manuscritas com foco forense. Avalia rigorosamente os seguintes critérios:\n"
            "1. Semelhanças estruturais (forma geral, ordem dos traços, ritmo)\n"
            "2. Diferenças relevantes (pressão, hesitações, deformações, ângulo e proporção)\n"
            "3. Indícios de falsificação (traços tremidos, sobreposição, hesitação visível)\n"
            "4. Nível de confiança na autoria comum, numa escala de 0.00 a 1.00\n"
            "5. Classificação final com base nos critérios: \n"
            "   - “Provavelmente Legítima” (alta confiança e variações naturais)\n"
            "   - “Suspeita” (algumas inconsistências relevantes)\n"
            "   - “Provavelmente Falsa” (múltiplos indícios de falsificação)\n\n"
            "Retorna os resultados neste formato JSON:\n"
            "```json\n"
            "{\n"
            "  \"similaridade\": \"<valor entre 0.00 e 1.00>\",\n"
            "  \"classificacao\": \"<uma das 3 opções>\",\n"
            "  \"analise\": \"<explicação objetiva e detalhada>\"\n"
            "}" 
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "És um perito em grafoscopia e verificação de assinaturas."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{original_base64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{amostra_base64}"}},
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()

        try:
            resultado = json.loads(output)
        except json.JSONDecodeError:
            resultado = {
                "analise": output,
                "similaridade": re.search(r"[\d\.]+", output).group(0) if re.search(r"[\d\.]+", output) else "Não extraída",
                "classificacao": re.search(r"(Provavelmente Legítima|Suspeita|Provavelmente Falsa)", output).group(0) if re.search(r"(Provavelmente Legítima|Suspeita|Provavelmente Falsa)", output) else "Não extraída"
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
