import os
import json
from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
from datetime import datetime
import base64
import openai

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
LOG_FILE = "verificacoes_log.jsonl"

def encode_image(image_file):
    image = Image.open(image_file)
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files["original"]
        amostra_file = request.files["amostra"]

        original_encoded = encode_image(original_file)
        amostra_encoded = encode_image(amostra_file)

        prompt = (
            "Analisa duas imagens de assinaturas manuscritas com foco forense. Avalia rigorosamente os seguintes critérios:\n"
            "1. Semelhanças estruturais (forma geral, ordem dos traços, ritmo)\n"
            "2. Diferenças relevantes (pressão, hesitações, deformações, ângulo e proporção)\n"
            "3. Indícios de falsificação (traços tremidos, sobreposição, hesitação visível)\n"
            "4. Nível de confiança na autoria comum, numa escala de 0.00 a 1.00\n"
            "5. Classificação final com base nos critérios: \n"
            "   - 'Provavelmente Legítima' (alta confiança e variações naturais)\n"
            "   - 'Suspeita' (algumas inconsistências relevantes)\n"
            "   - 'Provavelmente Falsa' (múltiplos indícios de falsificação)\n\n"
            "Retorna os resultados *exatamente* neste formato JSON, sem texto adicional:\n"
            "{\n"
            "  \"similaridade\": \"<valor entre 0.00 e 1.00>\",\n"
            "  \"classificacao\": \"<uma das 3 opções>\",\n"
            "  \"analise\": \"<explicação objetiva e detalhada>\"\n"
            "}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{original_encoded}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{amostra_encoded}"}}
                    ]
                }
            ],
            max_tokens=1000
        )

        output = response.choices[0].message.content.strip()

        try:
            resultado = json.loads(output)
        except json.JSONDecodeError:
            resultado = {
                "similaridade": "Não extraída",
                "classificacao": "Não extraída",
                "analise": output
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
