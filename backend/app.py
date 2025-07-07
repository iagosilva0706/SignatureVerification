import os
import openai
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import re
import io

@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files.get("original")
        amostra_file = request.files.get("amostra")

        if not original_file or not amostra_file:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

        # Lê os bytes e cria arquivos virtuais compatíveis com OpenAI
        original_bytes = original_file.read()
        amostra_bytes = amostra_file.read()

        original_io = io.BytesIO(original_bytes)
        amostra_io = io.BytesIO(amostra_bytes)

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
                        {"type": "image", "image": {"source": {"type": "file", "file": original_io}}},
                        {"type": "image", "image": {"source": {"type": "file", "file": amostra_io}}},
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()
        similaridade = re.search(r"similaridade.*?(\d\.\d{2})", output, re.IGNORECASE)
        classificacao = re.search(r"Classifica(?:do|ção).*?:\s*(.*)", output, re.IGNORECASE)

        resultado = {
            "analise": output,
            "similaridade": similaridade.group(1) if similaridade else "Não extraída",
            "classificacao": classificacao.group(1) if classificacao else "Não extraída"
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
