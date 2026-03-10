"""
City Printers CRM - Application entry point.
Run with: python run.py
"""
import os
from app import create_app, db
from app.models import User, Customer, Service

app = create_app(os.environ.get('FLASK_ENV', 'default'))


@app.shell_context_processor
def make_shell_context():
    """Provide models in flask shell."""
    return {
        'db': db,
        'User': User,
        'Customer': Customer,
        'Service': Service,
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
