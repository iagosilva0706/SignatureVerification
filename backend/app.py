import os
import json
import base64
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment and API setup
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs/verificacoes.jsonl"
os.makedirs("logs", exist_ok=True)

# Function to extract handwritten signature (excluding printed labels)
def extract_cropped_signature(file_storage):
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    height, width = image.shape[:2]

    # Focus on lower section, but allow adjusting as needed
    roi = image[int(height * 0.60):int(height * 0.95), 0:width]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = 250
    max_height = 0.4 * roi.shape[0]

    bounding_boxes = [
        cv2.boundingRect(c) for c in contours
        if min_area < cv2.contourArea(c) and cv2.boundingRect(c)[3] < max_height
    ]

    if bounding_boxes:
        x_vals = [x for x, y, w, h in bounding_boxes] + [x + w for x, y, w, h in bounding_boxes]
        y_vals = [y for x, y, w, h in bounding_boxes] + [y + h for x, y, w, h in bounding_boxes]
        x_min, x_max = max(min(x_vals) - 5, 0), min(max(x_vals) + 5, width)
        y_min, y_max = max(min(y_vals) - 10, 0), min(max(y_vals) + 5, roi.shape[0])

        y_min += int(height * 0.60)
        y_max += int(height * 0.60)

        cropped_handwriting = image[y_min:y_max, x_min:x_max]

        cropped_gray = cv2.cvtColor(cropped_handwriting, cv2.COLOR_BGR2GRAY)
        _, handwriting_mask = cv2.threshold(cropped_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        handwriting_mask_inv = cv2.bitwise_not(handwriting_mask)
        final_signature = cv2.cvtColor(handwriting_mask_inv, cv2.COLOR_GRAY2BGR)

        _, buffer = cv2.imencode('.png', final_signature)
        b64_cropped = base64.b64encode(buffer).decode('utf-8')
        return b64_cropped

    # fallback: encode whole ROI
    _, buffer = cv2.imencode('.png', roi)
    return base64.b64encode(buffer).decode('utf-8')


@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files.get("original")
        amostra_file = request.files.get("amostra")

        if not original_file or not amostra_file:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

        # Convert images to base64
        original_b64 = base64.b64encode(original_file.read()).decode("utf-8")
        amostra_b64 = extract_cropped_signature(amostra_file)
        amostra_file.seek(0)

        # OpenAI prompt
        prompt = (
            "Compare visually two handwritten signature images. "
            "Analyze carefully the stroke pressure and thickness, writing rhythm and fluidity, proportions between letters, overall slant, spacing, and consistency of graphical style. "
            "Pay close attention to any signs of forgery, such as unnatural tremors, hesitation marks, inconsistent pressure, interrupted flow, or abnormal angularity.\n"
            "Carefully assess visual characteristics such as:\n"
            "- Stroke pressure and thickness\n"
            "- Writing rhythm and flow\n"
            "- Letter and word proportions\n"
            "- General slant\n"
            "- Consistency in graphical style\n"
            "Provide:\n"
            "- Noted similarities\n"
            "- Relevant differences\n"
            "- A similarity score (0.00 to 1.00)\n"
            "- Overall classification: Very Similar, Somewhat Different, Clearly Different\n"
            "Respond strictly in this JSON format:\n"
            "{\n"
            "  \"similaridade\": \"<score between 0.00 and 1.00>\",\n"
            "  \"classificacao\": \"<classification>\",\n"
            "  \"analise\": \"<clear and concise explanation>\"\n"
            "}"
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
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{amostra_b64}"}},
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
