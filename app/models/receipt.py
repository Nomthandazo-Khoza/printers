"""
Receipt model for City Printers CRM.
One receipt per order, generated after payment.
"""
from datetime import datetime
from app import db


class Receipt(db.Model):
    """
    Receipt for an order. Generated after full payment.
    """
    __tablename__ = 'receipts'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Receipt {self.receipt_number}>'
