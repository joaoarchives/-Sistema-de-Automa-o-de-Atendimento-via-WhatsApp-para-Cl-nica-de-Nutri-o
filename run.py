"""
Ponto de entrada para rodar o servidor a partir da raiz do projeto.

Uso:
    python run.py
    flask --app run:app run --port 5000

Isso permite rodar o backend sem precisar entrar na pasta backend/.
"""
import sys
import os

# Adiciona backend/ ao path para que os imports funcionem normalmente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import app  # noqa: E402 — importado após ajuste de path

if __name__ == "__main__":
    app.run(port=5000, debug=True)