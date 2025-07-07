// frontend/src/App.js
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

export default function AssinaturaVerifier() {
  const [original, setOriginal] = useState(null);
  const [amostra, setAmostra] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);

  const onDropOriginal = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) setOriginal(acceptedFiles[0]);
  }, []);

  const onDropAmostra = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) setAmostra(acceptedFiles[0]);
  }, []);

  const { getRootProps: getRootPropsOriginal, getInputProps: getInputPropsOriginal } = useDropzone({
    onDrop: onDropOriginal,
    accept: { 'image/*': [] },
    maxFiles: 1
  });

  const { getRootProps: getRootPropsAmostra, getInputProps: getInputPropsAmostra } = useDropzone({
    onDrop: onDropAmostra,
    accept: { 'image/*': [] },
    maxFiles: 1
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!original || !amostra) return;
    setLoading(true);
    setResultado(null);
    const formData = new FormData();
    formData.append('original', original);
    formData.append('amostra', amostra);

    try {
      const res = await axios.post('http://localhost:5000/verify_signature', formData);
      setResultado(res.data);
    } catch (err) {
      setResultado({ erro: 'Erro ao verificar assinatura.' });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-white text-gray-800 font-sans p-6 max-w-4xl mx-auto">
      <header className="mb-8 border-b pb-4">
        <img src="/logo-papiro.png" alt="Logo Papiro" className="h-16 mb-4" />
        <h1 className="text-3xl font-bold">Verificação de Assinatura</h1>
        <p className="text-sm text-gray-600">Comparação entre duas assinaturas manuscritas com IA</p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block mb-1 font-medium">Assinatura Original:</label>
          <div {...getRootPropsOriginal()} className="border-2 border-dashed rounded p-4 text-center cursor-pointer hover:bg-gray-50">
            <input {...getInputPropsOriginal()} />
            {original ? (
              <p className="text-green-700">{original.name}</p>
            ) : (
              <p className="text-gray-500">Arraste a imagem aqui ou clique para escolher</p>
            )}
          </div>
        </div>

        <div>
          <label className="block mb-1 font-medium">Assinatura a Verificar:</label>
          <div {...getRootPropsAmostra()} className="border-2 border-dashed rounded p-4 text-center cursor-pointer hover:bg-gray-50">
            <input {...getInputPropsAmostra()} />
            {amostra ? (
              <p className="text-green-700">{amostra.name}</p>
            ) : (
              <p className="text-gray-500">Arraste a imagem aqui ou clique para escolher</p>
            )}
          </div>
        </div>

        <button type="submit" disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
          {loading ? 'A verificar...' : 'Verificar Assinatura'}
        </button>
      </form>

      {resultado && (
        <div className="mt-8 border-t pt-6">
          <h2 className="text-xl font-semibold mb-2">Resultado:</h2>
          {resultado.erro ? (
            <p className="text-red-600">{resultado.erro}</p>
          ) : (
            <div className="space-y-2">
              <p><strong>Pontuação de Similaridade:</strong> {resultado.similaridade}</p>
              <p><strong>Classificação:</strong> {resultado.classificacao}</p>
              <p><strong>Análise:</strong> {resultado.analise}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
