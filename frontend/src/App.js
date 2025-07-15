import React, { useState } from 'react';
import './App.css';

function App() {
  const [imageUrl, setImageUrl] = useState(null);

  const uploadImage = async (event) => {
    const file = event.target.files[0];
    if (!file) return alert('Select an image.');

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('http://localhost:8000/extract_signature', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) return alert('Upload failed.');

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    setImageUrl(url);
  };

  return (
    <div className="App">
      <h1>Signature Extraction</h1>
      <p>Select an image with a handwritten signature to test extraction.</p>

      <input type="file" onChange={uploadImage} accept="image/*" />

      {imageUrl && (
        <div>
          <h2>Cropped Signature:</h2>
          <img
            src={imageUrl}
            alt="Signature"
            style={{ maxWidth: '400px', cursor: 'pointer' }}
            onClick={() => window.open(imageUrl, '_blank')}
          />
        </div>
      )}
    </div>
  );
}

export default App;
