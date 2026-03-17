"""
Order and OrderItem models for City Printers CRM.
An order is a service job containing one or more services (order items).
Workflow: submitted -> in_progress -> (job complete) pending_payment -> paid -> ready_for_collection -> completed.
"""
from datetime import datetime
from decimal import Decimal
from app import db


class Order(db.Model):
    """
    Service job / service request.
    One order can contain multiple services (via OrderItem).
    order_status: submitted | in_progress | ready_for_collection | completed | rejected
    payment_status: unpaid | pending_payment | paid
    """
    __tablename__ = 'orders'

    # Order status (workflow)
    STATUS_SUBMITTED = 'submitted'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_READY_FOR_COLLECTION = 'ready_for_collection'
    STATUS_COMPLETED = 'completed'
    STATUS_REJECTED = 'rejected'
    ORDER_STATUS_CHOICES = [
        STATUS_SUBMITTED, STATUS_IN_PROGRESS, STATUS_READY_FOR_COLLECTION,
        STATUS_COMPLETED, STATUS_REJECTED,
    ]

    # Payment status
    PAYMENT_UNPAID = 'unpaid'
    PAYMENT_PENDING = 'pending_payment'
    PAYMENT_PAID = 'paid'
    PAYMENT_STATUS_CHOICES = [PAYMENT_UNPAID, PAYMENT_PENDING, PAYMENT_PAID]

    # Payment option (when customer chooses to pay)
    PAYMENT_OPTION_PAY_NOW = 'pay_now_online'
    PAYMENT_OPTION_PAY_LATER = 'pay_later_counter'
    PAYMENT_OPTION_CHOICES = [PAYMENT_OPTION_PAY_NOW, PAYMENT_OPTION_PAY_LATER]

    # Payment method (how order was paid: set when payment is recorded)
    PAYMENT_METHOD_CARD = 'card'
    PAYMENT_METHOD_COUNTER = 'counter'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # staff who created
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    order_status = db.Column(db.String(32), default=STATUS_SUBMITTED, nullable=False)
    payment_status = db.Column(db.String(32), default=PAYMENT_UNPAID, nullable=False)
    payment_option = db.Column(db.String(32), default=PAYMENT_OPTION_PAY_LATER, nullable=False)
    payment_method = db.Column(db.String(32), nullable=True)  # 'card' or 'counter' when paid
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    collected_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    files = db.relationship('OrderFile', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False, cascade='all, delete-orphan')
    receipt = db.relationship('Receipt', backref='order', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship(
        'OrderNotification', backref='order', lazy='dynamic',
        cascade='all, delete-orphan', order_by='OrderNotification.created_at'
    )

    def recalculate_total(self):
        """Recalculate total_amount from order items."""
        self.total_amount = sum(
            (item.subtotal for item in self.items),
            Decimal('0.00')
        )

    def can_start_job(self):
        """Pay-now-online orders can only be started after payment; pay-later-counter can start immediately."""
        if self.order_status != self.STATUS_SUBMITTED:
            return False
        if self.payment_option == self.PAYMENT_OPTION_PAY_NOW:
            return self.payment_status == self.PAYMENT_PAID
        return True  # pay_later_counter

    def can_mark_job_complete(self):
        return self.order_status == self.STATUS_IN_PROGRESS

    def can_confirm_payment(self):
        """True only for pay_later_counter orders with no payment yet (counter payment at admin/cashier)."""
        if self.payment_option != self.PAYMENT_OPTION_PAY_LATER:
            return False
        return not self.payment and self.payment_status in (self.PAYMENT_UNPAID, self.PAYMENT_PENDING)

    def can_mark_ready_for_collection(self):
        return self.payment_status == self.PAYMENT_PAID and self.order_status == self.STATUS_IN_PROGRESS

    def can_mark_collected(self):
        return self.order_status == self.STATUS_READY_FOR_COLLECTION

    def get_allowed_order_actions(self):
        """Return list of allowed action names for current state."""
        actions = []
        if self.can_start_job():
            actions.append('start_job')
        if self.can_mark_job_complete():
            actions.append('mark_job_complete')
        if self.can_confirm_payment():
            actions.append('confirm_payment')
        if self.can_mark_ready_for_collection():
            actions.append('ready_for_collection')
        if self.can_mark_collected():
            actions.append('mark_collected')
        return actions

    def get_customer_stage_message(self):
        """Return a short, customer-friendly message for the current stage."""
        if self.order_status == self.STATUS_SUBMITTED:
            if self.payment_option == self.PAYMENT_OPTION_PAY_NOW and self.payment_status != self.PAYMENT_PAID:
                return 'Payment required online before processing can continue.'
            return 'We have received your request and will start soon.'
        if self.order_status == self.STATUS_IN_PROGRESS:
            return 'Your order is being processed.'
        if self.payment_status == self.PAYMENT_PENDING:
            return 'Your order is complete. Please pay at the counter.'
        if self.payment_status == self.PAYMENT_PAID and self.order_status == self.STATUS_IN_PROGRESS:
            return 'Payment received. We will notify you when ready for collection.'
        if self.order_status == self.STATUS_READY_FOR_COLLECTION:
            return 'Your order is ready for collection.'
        if self.order_status == self.STATUS_COMPLETED:
            return 'Order completed. Thank you!'
        if self.order_status == self.STATUS_REJECTED:
            return 'This order was rejected. Please contact us if you have questions.'
        return '—'

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
