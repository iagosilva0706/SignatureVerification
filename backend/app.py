import os
import json
import base64
import cv2
import numpy as np
import shutil
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image  # Added dependency

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs/verificacoes.jsonl"
os.makedirs("logs", exist_ok=True)

def extract_signature(image_path, output_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    signature_contour = None
    max_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 500 < area < 50000:
            if area > max_area:
                max_area = area
                signature_contour = cnt

    if signature_contour is None:
        raise ValueError("No signature found.")

    x, y, w, h = cv2.boundingRect(signature_contour)
    cropped = image[y:y+h, x:x+w]
    cv2.imwrite(output_path, cropped)

@app.route("/extract_signature", methods=["POST"])
def extract_signature_route():
    try:
        uploaded_file = request.files.get("file")
        if not uploaded_file:
            return jsonify({"error": "No file uploaded."}), 400

        temp_input = f"temp_{uuid.uuid4().hex}.png"
        temp_output = f"cropped_{uuid.uuid4().hex}.png"

        with open(temp_input, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.stream, buffer)

        extract_signature(temp_input, temp_output)
        os.remove(temp_input)

        return send_file(temp_output, mimetype='image/png', as_attachment=True, download_name='signature.png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            "Compare visually two handwritten signature images. "
            "Analyze carefully the stroke pressure and thickness, writing rhythm and fluidity, proportions between letters, overall slant, spacing, and consistency of graphical style. "
            "Pay attention to signs of forgery: unnatural tremors, hesitation marks, inconsistent pressure, interrupted flow, or abnormal angularity. "
            "Respond strictly in JSON format with similarity score, classification, and analysis."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a handwriting forensics expert specializing in signature verification."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{original_b64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{amostra_b64}"}},
                ]}
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
