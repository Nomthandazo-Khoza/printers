"""
Order and OrderItem models for City Printers CRM.
An order is a service job containing one or more services (order items).
"""
from datetime import datetime
from decimal import Decimal
from app import db


class Order(db.Model):
    """
    Service job / service request.
    One order can contain multiple services (via OrderItem).
    """
    __tablename__ = 'orders'

    # Status choices (business rule)
    STATUS_PENDING = 'Pending'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETED = 'Completed'
    STATUS_COLLECTED = 'Collected'
    STATUS_CHOICES = [STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_COLLECTED]

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # staff who created
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    order_status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False, cascade='all, delete-orphan')
    receipt = db.relationship('Receipt', backref='order', uselist=False, cascade='all, delete-orphan')

    def recalculate_total(self):
        """Recalculate total_amount from order items."""
        self.total_amount = sum(
            (item.subtotal for item in self.items),
            Decimal('0.00')
        )

    def __repr__(self):
        return f'<Order {self.id} customer={self.customer_id} total={self.total_amount}>'


class OrderItem(db.Model):
    """
    One line item in an order: a service + quantity + unit_price + subtotal.
    """
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<OrderItem order={self.order_id} service={self.service_id} qty={self.quantity}>'
