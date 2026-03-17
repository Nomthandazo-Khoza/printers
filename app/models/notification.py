"""
Notification model for City Printers CRM.
Customer-facing notifications for order updates (navbar bell, notifications page).
"""
from datetime import datetime
from app import db


class Notification(db.Model):
    """
    A notification for a customer (e.g. order update).
    Shown in navbar bell and on the notifications page.
    """
    __tablename__ = 'notifications'

    TYPE_INFO = 'info'
    TYPE_SUCCESS = 'success'
    TYPE_WARNING = 'warning'
    TYPE_PAYMENT = 'payment'
    TYPE_COLLECTION = 'collection'
    TYPE_CHOICES = [TYPE_INFO, TYPE_SUCCESS, TYPE_WARNING, TYPE_PAYMENT, TYPE_COLLECTION]

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(512), nullable=False)
    type = db.Column(db.String(20), default=TYPE_INFO, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = db.relationship('Customer', backref=db.backref('notifications', lazy='dynamic'))
    order = db.relationship('Order', backref=db.backref('customer_notifications', lazy='dynamic'))

    def __repr__(self):
        return f'<Notification {self.id} customer={self.customer_id} {self.title!r}>'
