"""
City Printers CRM - Application Configuration
Central configuration for Flask app, database, and security.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    # Flask (SECRET_KEY required for session and CSRF)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # CSRF protection (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # token valid until session ends (recommended for forms with file upload)
    
    # Database - MySQL (or SQLite if DATABASE_URI not set, for quick local dev)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        os.environ.get('DEV_DATABASE_URI') or \
        'mysql+pymysql://root:@localhost/city_printers_crm'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Session (ensure cookie is sent with form POSTs)
    SESSION_PROTECTION = 'strong'
    REMEMBER_COOKIE_DURATION = 86400  # 24 hours
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Uploads (relative to instance folder)
    UPLOAD_ORDER_FOLDER = 'uploads/orders'


class DevelopmentConfig(Config):
    """Development environment config."""
    DEBUG = True
    TESTING = False
    # Use SQLite when DATABASE_URI not set (run without MySQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///city_printers.db'


class ProductionConfig(Config):
    """Production environment config."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing environment config."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Config mapping for FLASK_ENV
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
