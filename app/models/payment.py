"""
Payment model for City Printers CRM.
Full payment only; one payment per order (business rule).
"""
from datetime import datetime
from app import db


class Payment(db.Model):
    """
    One payment per order. Full payment required (no partial / pay later).
    """
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)  # e.g. Cash, Card, EFT
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    recorded_by_user = db.relationship('User', backref='payments_recorded', foreign_keys=[recorded_by])

    def __repr__(self):
        return f'<Payment order={self.order_id} amount={self.amount_paid}>'
