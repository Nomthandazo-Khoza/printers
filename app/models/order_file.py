"""
OrderFile model for City Printers CRM.
Stores metadata for documents uploaded by customers with a service request.
"""
from datetime import datetime
from app import db


class OrderFile(db.Model):
    """
    A file uploaded by a customer with an order (e.g. PDF to print).
    Belongs to the order as a whole, not to individual order items.
    """
    __tablename__ = 'order_files'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)  # relative to instance folder
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<OrderFile {self.original_filename} order={self.order_id}>'
