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

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs/verificacoes.jsonl"
os.makedirs("logs", exist_ok=True)

# Function to automatically crop the handwritten signature from the "amostra" image
def crop_signature_from_amostra(file_storage):
    # Read image bytes and convert to OpenCV image
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # Convert to grayscale and threshold
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find contours of handwriting
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = 500  # Minimum contour area to consider as part of signature
    bounding_boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > min_area]

    # Create a combined bounding box around all significant contours
    if bounding_boxes:
        x_vals = [x for x, y, w, h in bounding_boxes] + [x + w for x, y, w, h in bounding_boxes]
        y_vals = [y for x, y, w, h in bounding_boxes] + [y + h for x, y, w, h in bounding_boxes]
        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        signature_crop = image[y_min:y_max, x_min:x_max]
    else:
        signature_crop = image  # fallback: no contours found, return full image

    # Encode cropped image to base64
    _, buffer = cv2.imencode('.png', signature_crop)
    b64_cropped = base64.b64encode(buffer).decode('utf-8')

    return b64_cropped


@app.route("/verify_signature", methods=["POST"])
def verify_signature():
    try:
        original_file = request.files.get("original")
        amostra_file = request.files.get("amostra")

        if not original_file or not amostra_file:
            return jsonify({"erro": "Ambas as imagens são obrigatórias."}), 400

        # Convert "original" image to base64 (no cropping)
        original_b64 = base64.b64encode(original_file.read()).decode("utf-8")

        # Crop "amostra" image before converting to base64
        amostra_b64 = crop_signature_from_amostra(amostra_file)
        amostra_file.seek(0)  # Reset pointer in case needed later

        # Prompt to OpenAI
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
