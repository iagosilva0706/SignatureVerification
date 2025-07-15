import os
import cv2
import numpy as np
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from skimage.metrics import structural_similarity
from ultralytics import YOLO

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Load YOLO Model (You should train your model and replace 'signature_model.pt')
yolo_model = YOLO('signature_model.pt')

# Helper: Preprocess Image
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return thresh

# Helper: Extract Signature using YOLO
def extract_signature(image):
    temp_file = f"temp_{uuid.uuid4().hex}.png"
    cv2.imwrite(temp_file, image)
    results = yolo_model(temp_file)
    os.remove(temp_file)
    if not results[0].boxes.xyxy.tolist():
        raise ValueError("No signature detected.")
    x1, y1, x2, y2 = map(int, results[0].boxes.xyxy[0])
    cropped = image[y1:y2, x1:x2]
    return cropped

# Helper: Compare using SSIM + Explanation
def compare_signatures(img1, img2):
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    img1 = cv2.resize(img1, (500, 200))
    img2 = cv2.resize(img2, (500, 200))
    score, _ = structural_similarity(img1, img2, full=True)
    return round(score, 4), "Comparison performed using structural similarity (SSIM) focused on overall stroke pattern consistency."

# API Route
@app.route('/verify_signature', methods=['POST'])
def verify_signature():
    try:
        original_file = request.files.get("Original")
        signature_file = request.files.get("Signature")

        if not original_file or not signature_file:
            return jsonify({"error": "Both 'Original' and 'Signature' files are required."}), 400

        original_image = cv2.imdecode(np.frombuffer(original_file.read(), np.uint8), cv2.IMREAD_COLOR)
        signature_image = cv2.imdecode(np.frombuffer(signature_file.read(), np.uint8), cv2.IMREAD_COLOR)

        cropped_signature = extract_signature(signature_image)
        score, explanation = compare_signatures(original_image, cropped_signature)

        status = "Match" if score > 0.75 else "Partial Match" if score > 0.5 else "Mismatch"

        return jsonify({
            "score": score,
            "status": status,
            "explanation": explanation
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
