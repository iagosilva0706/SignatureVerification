# Assinatura Verificação App

Aplicação web que compara duas assinaturas e indica se são semelhantes, suspeitas ou falsas usando GPT-4o da OpenAI.

## Estrutura

- `frontend/`: Interface React
- `backend/`: API Flask
- Logs são guardados em `backend/logs/verificacoes.jsonl`

## Como executar localmente

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
cp .env.example .env  # e insere tua chave OpenAI
python app.py
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

---

