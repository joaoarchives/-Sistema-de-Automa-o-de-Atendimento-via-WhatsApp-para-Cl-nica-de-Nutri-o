# Adicione isso no seu app.py existente, após criar o app Flask:

from flask_cors import CORS
from api import api as api_blueprint

# Permite o React (Vite :5173) se comunicar com o Flask (:5000)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# Registra as rotas da API
app.register_blueprint(api_blueprint)
