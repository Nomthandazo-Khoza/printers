"""
Order workflow: status transitions and customer notifications.
"""
from datetime import datetime
from app import db
from app.models.order import Order
from app.models.order_notification import OrderNotification
from app.models.payment import Payment
from app.services.notification_service import create_notification


def add_notification(order, message):
    """Add a customer-visible notification for the order (order detail page)."""
    n = OrderNotification(order_id=order.id, message=message)
    db.session.add(n)


def _customer_notification(order, title, message, notification_type='info'):
    """Add OrderNotification and navbar Notification for the customer."""
    add_notification(order, message)
    create_notification(
        customer_id=order.customer_id,
        title=title,
        message=message,
        order_id=order.id,
        notification_type=notification_type,
    )


def start_job(order):
    """Admin: Start the job. order_status -> in_progress."""
    if not order.can_start_job():
        return False, 'Invalid transition'
    order.order_status = Order.STATUS_IN_PROGRESS
    order.updated_at = datetime.utcnow()
    _customer_notification(
        order,
        'Order in progress',
        'We have started working on your order.',
        notification_type='info',
    )
    return True, None


def mark_job_complete(order):
    """Admin: Job done. For pay_later_counter: payment_status -> pending_payment and notify. For pay_now_online: already paid."""
    if not order.can_mark_job_complete():
        return False, 'Invalid transition'
    order.updated_at = datetime.utcnow()
    if order.payment_option == Order.PAYMENT_OPTION_PAY_LATER:
        order.payment_status = Order.PAYMENT_PENDING
        _customer_notification(
            order,
            'Payment required',
            'Your order is complete. Please make payment at the counter.',
            notification_type='payment',
        )
    return True, None


def confirm_online_payment(order):
    """Customer: Record online card payment (pay_now_online only). Sets payment_status=paid, payment_method=card."""
    if order.payment:
        return False, 'Payment already recorded'
    if order.payment_option != Order.PAYMENT_OPTION_PAY_NOW:
        return False, 'This order is not set for online payment.'
    if order.payment_status != Order.PAYMENT_UNPAID:
        return False, 'Invalid payment state'
    from app.models.receipt import Receipt
    amount_paid = order.total_amount
    payment = Payment(
        order_id=order.id,
        amount_paid=amount_paid,
        payment_method=Order.PAYMENT_METHOD_CARD,
        recorded_by=None,
    )
    db.session.add(payment)
    db.session.flush()
    order.payment_status = Order.PAYMENT_PAID
    order.payment_method = Order.PAYMENT_METHOD_CARD
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    receipt_number = f'RCP-{order.id}-{datetime.utcnow().strftime("%Y%m%d")}'
    receipt = Receipt(order_id=order.id, receipt_number=receipt_number)
    db.session.add(receipt)
    _customer_notification(
        order,
        'Payment received',
        'Payment received. Your order will be processed shortly.',
        notification_type='success',
    )
    return True, None


def confirm_payment(order, amount_paid, payment_method, recorded_by_user_id=None):
    """Cashier/Admin: Record counter payment (pay_later_counter only). payment_status -> paid, payment_method -> counter."""
    if order.payment:
        return False, 'Payment already recorded'
    if order.payment_option != Order.PAYMENT_OPTION_PAY_LATER:
        return False, 'Only pay-later orders can be paid at the counter.'
    if order.payment_status not in (Order.PAYMENT_UNPAID, Order.PAYMENT_PENDING):
        return False, 'Invalid payment state'
    from app.models.receipt import Receipt
    payment = Payment(
        order_id=order.id,
        amount_paid=amount_paid,
        payment_method=payment_method or Order.PAYMENT_METHOD_COUNTER,
        recorded_by=recorded_by_user_id,
    )
    db.session.add(payment)
    db.session.flush()
    order.payment_status = Order.PAYMENT_PAID
    order.payment_method = Order.PAYMENT_METHOD_COUNTER
    order.paid_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    receipt_number = f'RCP-{order.id}-{datetime.utcnow().strftime("%Y%m%d")}'
    receipt = Receipt(order_id=order.id, receipt_number=receipt_number)
    db.session.add(receipt)
    _customer_notification(
        order,
        'Payment received',
        'Payment received. Your order is ready for collection when we mark it.',
        notification_type='success',
    )
    return True, None


def mark_ready_for_collection(order):
    """Admin: Notify customer order is ready. order_status -> ready_for_collection."""
    if not order.can_mark_ready_for_collection():
        return False, 'Invalid transition'
    order.order_status = Order.STATUS_READY_FOR_COLLECTION
    order.updated_at = datetime.utcnow()
    _customer_notification(
        order,
        'Ready for collection',
        'Your order is ready for collection.',
        notification_type='collection',
    )
    return True, None


def mark_collected(order):
    """Admin: Customer collected. order_status -> completed."""
    if not order.can_mark_collected():
        return False, 'Invalid transition'
    order.order_status = Order.STATUS_COMPLETED
    order.collected_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    _customer_notification(
        order,
        'Order completed',
        'Order collected. Thank you!',
        notification_type='success',
    )
    return True, None
