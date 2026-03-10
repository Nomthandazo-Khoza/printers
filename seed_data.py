"""
Seed initial data: admin user, cashier user, and default services.
Run after: flask db upgrade
"""
import sys
from run import app
from app import db
from app.models.user import User
from app.models.service import Service


def seed():
    with app.app_context():
        if User.query.filter_by(email='admin@cityprinters.com').first():
            print('Seed data already exists. Skipping.')
            return

        # Admin and Cashier users
        admin = User(full_name='System Admin', email='admin@cityprinters.com', role='admin')
        admin.set_password('admin123')
        cashier = User(full_name='Cashier User', email='cashier@cityprinters.com', role='cashier')
        cashier.set_password('cashier123')
        db.session.add_all([admin, cashier])

        # Default services (as per requirements)
        services = [
            Service(service_name='Black & White Printing', description='Per page', unit_price=2.00, active_status=True),
            Service(service_name='Colour Printing', description='Per page', unit_price=5.00, active_status=True),
            Service(service_name='Photocopying', description='Per page', unit_price=1.50, active_status=True),
            Service(service_name='Scanning', description='Per page', unit_price=3.00, active_status=True),
            Service(service_name='Laminating', description='Per item', unit_price=15.00, active_status=True),
            Service(service_name='Binding', description='Per document', unit_price=25.00, active_status=True),
        ]
        db.session.add_all(services)
        db.session.commit()
        print('Seeded: 1 admin, 1 cashier, 6 services.')


if __name__ == '__main__':
    seed()
    sys.exit(0)
