<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signature Extraction Demo</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .preview { margin-top: 20px; }
        img { max-width: 400px; display: block; margin-top: 10px; cursor: pointer; }
        .modal {
            display: none;
            position: fixed;
            z-index: 999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.9);
        }
        .modal-content {
            margin: 5% auto;
            display: block;
            max-width: 90%;
        }
        .modal-content img {
            width: 100%;
            height: auto;
        }
        .close {
            position: absolute;
            top: 20px;
            right: 35px;
            color: #fff;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Signature Extraction Service</h1>
    <p>Select an image with a handwritten signature to test extraction.</p>

    <input type="file" id="imageInput" accept="image/*">
    <button onclick="uploadImage()">Extract Signature</button>

    <div class="preview" id="previewContainer"></div>

    <div id="modal" class="modal" onclick="closeModal()">
        <span class="close" onclick="closeModal()">&times;</span>
        <div class="modal-content" id="modalContent"></div>
    </div>

    <script>
        function uploadImage() {
            const input = document.getElementById('imageInput');
            if (!input.files.length) {
                alert('Please select an image.');
                return;
            }
            const formData = new FormData();
            formData.append('file', input.files[0]);

            fetch('http://localhost:8000/extract-signature/', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) throw new Error('Failed to extract signature.');
                return response.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                document.getElementById('previewContainer').innerHTML = `<h2>Cropped Signature:</h2><img src="${url}" alt="Signature" onclick="openModal('${url}')">`;
            })
            .catch(err => alert(err.message));
        }

        function openModal(imageUrl) {
            const modal = document.getElementById("modal");
            const modalContent = document.getElementById("modalContent");
            modalContent.innerHTML = `<img src="${imageUrl}" alt="Signature Full Size">`;
            modal.style.display = "block";
        }

        function closeModal() {
            document.getElementById("modal").style.display = "none";
        }
    </script>
</body>
</html>
