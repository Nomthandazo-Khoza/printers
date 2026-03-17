"""
OrderNotification model for City Printers CRM.
Stores customer-visible messages for order workflow stages.
"""
from datetime import datetime
from app import db


class OrderNotification(db.Model):
    """
    A message shown to the customer about their order (e.g. "Your order is ready for collection.").
    """
    __tablename__ = 'order_notifications'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    message = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<OrderNotification order={self.order_id} {self.message[:30]!r}>'
