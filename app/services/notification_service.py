"""
Notification service for City Printers CRM.
Creates customer-facing notifications (navbar bell, notifications page).
"""
from app import db
from app.models.notification import Notification


def create_notification(customer_id, title, message, order_id=None, notification_type='info'):
    """
    Create a notification for a customer.
    Used for order updates and other customer alerts.
    """
    n = Notification(
        customer_id=customer_id,
        order_id=order_id,
        title=title,
        message=message,
        type=notification_type,
        is_read=False,
    )
    db.session.add(n)
    return n
