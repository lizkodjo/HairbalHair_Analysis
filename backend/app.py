import os
import sys

from flask import Flask, send_from_directory
from flask_cors import CORS

from database.herb_repository import HerbRepository
from routes import api_routes
from services.ai_service import AIService
from services.classifier_service import ClassifierService
from services.recommendation_service import RecommendationService
from config import Config

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialise Flask app
app = Flask(__name__, static_folder=str(Config.FRONTEND_DIR), static_url_path="")
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
CORS(app)


print("\n" + "=" * 70)
print("🌿 AYURVEDIC HAIR GROWTH RECOMMENDER")
print("=" * 70)

# Initialise services
herb_repo = HerbRepository()
classifier_service = ClassifierService()
ai_service = AIService()
recommendation_service = RecommendationService(herb_repo, classifier_service, ai_service)

# Register routes
app.register_blueprint(api_routes.bp, url_prefix='/api')
api_routes.init_services(recommendation_service, herb_repo, classifier_service, ai_service)

# Frontend routes
@app.route("/")
def serve_frontend():
    return send_from_directory(str(Config.FRONTEND_DIR), "index.html")

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(str(Config.FRONTEND_DIR), path)

if __name__ == "__main__":
    print(f"\n🚀 Server running at http://localhost:{Config.PORT}")
    print("📋 Mode: Condition-First + Optional Image Classification")
    print(f"📚 Database: {herb_repo.count()} herbs")
    print("\n📋 Quick test:")
    print("   curl -X POST http://localhost:5000/api/recommend \\")
    print("   -H 'Content-Type: application/json' \\")
    print('   -d \'{"conditions": ["hair_growth", "hair_fall"]}\'')
    print("=" * 70 + "\n")
    
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
