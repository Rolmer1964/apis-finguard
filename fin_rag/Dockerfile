FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Pré-baixa o modelo de embedding local no build, para o container não
# precisar de rede no startup/runtime (e o boot ser rápido).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY app ./app

# Seed da Política Interna. Em produção, monte um volume em /app/assets/docs
# (leitura) e outro em /app/assets/index (escrita, persiste o índice).
COPY assets ./assets

ENV RAG_DOCS_DIR=/app/assets/docs \
    RAG_INDEX_DIR=/app/assets/index

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
