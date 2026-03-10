"""
Service model for City Printers CRM.
Defines printable services and their unit prices.
"""
from datetime import datetime
from app import db


class Service(db.Model):
    """
    A service offered by the business (e.g. B&W Printing, Laminating).
    Admin sets unit_price. Inactive services are excluded from new orders.
    """
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    active_status = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Order items that use this service
    order_items = db.relationship('OrderItem', backref='service', lazy='dynamic')

    @staticmethod
    def get_active_services():
        """Return only services that can be added to new orders."""
        return Service.query.filter_by(active_status=True).order_by(Service.service_name).all()

    def __repr__(self):
        return f'<Service {self.service_name}>'
