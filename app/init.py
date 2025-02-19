from flask import Flask
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "this-should-be-changed")
    
    # Register blueprints
    from app.auth import auth_bp
    from app.docs import docs_bp
    from app.wiki import wiki_bp
    from app.sources import sources_bp
    from app.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(wiki_bp)
    app.register_blueprint(sources_bp)
    app.register_blueprint(main_bp)
    
    return app
