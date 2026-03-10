"""
City Printers CRM - Application Configuration
Central configuration for Flask app, database, and security.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database - MySQL (or SQLite if DATABASE_URI not set, for quick local dev)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        os.environ.get('DEV_DATABASE_URI') or \
        'mysql+pymysql://root:@localhost/city_printers_crm'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Session
    SESSION_PROTECTION = 'strong'
    REMEMBER_COOKIE_DURATION = 86400  # 24 hours


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
