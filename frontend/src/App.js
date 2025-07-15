import React, { useState } from 'react';

function App() {
  const [result, setResult] = useState(null);

  const uploadImages = async (event) => {
    const originalFile = document.getElementById('originalFile').files[0];
    const signatureFile = document.getElementById('signatureFile').files[0];

    if (!originalFile || !signatureFile) {
      alert('Please select both Original and Signature images.');
      return;
    }

    const formData = new FormData();
    formData.append('Original', originalFile);
    formData.append('Signature', signatureFile);

    const response = await fetch('http://localhost:8000/verify_signature', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) return alert('Upload failed.');

    const data = await response.json();
    setResult(data);
  };

  return (
    <div className="App">
      <h1>Signature Verification</h1>
      <p>Select the two images to verify:</p>

      <div>
        <label>Original Image:</label>
        <input type="file" id="originalFile" accept="image/*" />
      </div>

      <div>
        <label>Signature Image:</label>
        <input type="file" id="signatureFile" accept="image/*" />
      </div>

      <button onClick={uploadImages}>Verify Signature</button>

      {result && (
        <div>
          <h2>Verification Result:</h2>
          <p><strong>Score:</strong> {result.score}</p>
          <p><strong>Status:</strong> {result.status}</p>
          <p><strong>Explanation:</strong> {result.explanation}</p>
        </div>
      )}
    </div>
  );
}

export default App;
