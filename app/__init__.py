import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    # Since __name__ is 'app', the app's root path is the 'app' folder.
    # Our templates and static folders are one level up.
    import os
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
    static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")

    app = Flask(__name__, template_folder=template_path, static_folder=static_path)

    # Use config key rather than app.secret_key directly:
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "this-should-be-changed")

    # Initialize databases (users.db and wiki.db)
    from app.database_setup import init_user_db, init_wiki_db
    init_user_db()
    init_wiki_db()

    # Import and register blueprints
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
