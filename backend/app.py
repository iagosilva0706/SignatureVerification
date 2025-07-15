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
from PIL import Image
from skimage.metrics import structural_similarity

load_dotenv()

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

def compare_signatures(image1_path, image2_path):
    img1 = cv2.imread(image1_path, 0)
    img2 = cv2.imread(image2_path, 0)

    img1 = cv2.resize(img1, (500, 200))
    img2 = cv2.resize(img2, (500, 200))

    score, _ = structural_similarity(img1, img2, full=True)
    return round(score, 4)

@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files.get("original")
        amostra_file = request.files.get("amostra")

        if not original_file or not amostra_file:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

        temp_original = f"temp_{uuid.uuid4().hex}.png"
        temp_amostra = f"temp_{uuid.uuid4().hex}.png"

        with open(temp_original, "wb") as buffer:
            shutil.copyfileobj(original_file.stream, buffer)
        with open(temp_amostra, "wb") as buffer:
            shutil.copyfileobj(amostra_file.stream, buffer)

        score = compare_signatures(temp_original, temp_amostra)

        if score > 0.75:
            classification = "Very Similar"
        elif score > 0.5:
            classification = "Somewhat Different"
        else:
            classification = "Clearly Different"

        resultado = {
            "similaridade": str(score),
            "classificacao": classification,
            "analise": "Similarity score based on SSIM (Structural Similarity Index)."
        }

        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "resultado": resultado
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

        os.remove(temp_original)
        os.remove(temp_amostra)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"erro": f"Internal error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
