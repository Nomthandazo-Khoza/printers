"""
City Printers CRM System - Flask Application Factory
Creates and configures the Flask app with extensions and blueprints.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config_by_name

# Extensions (initialized without app, bound in create_app)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name=None):
    """
    Application factory. Creates Flask app, loads config, initializes
    extensions, registers blueprints.
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = 'default'
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Login manager settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.cashier import cashier_bp
    from app.routes.customer_portal import customer_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(cashier_bp, url_prefix='/cashier')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    
    return app
