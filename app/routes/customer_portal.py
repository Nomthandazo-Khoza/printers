"""
Customer portal blueprint: dashboard, place request, my orders, receipts, profile.
"""
import os
import uuid
from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, session, request, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app import db
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.order_file import OrderFile
from app.models.receipt import Receipt
from app.models.service import Service
from app.models.notification import Notification
from app.forms.customer_order_forms import CustomerRequestForm, ALLOWED_ORDER_FILE_EXTENSIONS
from app.services.order_workflow import add_notification
from app.services.notification_service import create_notification

customer_bp = Blueprint('customer_portal', __name__)


@customer_bp.app_context_processor
def inject_notification_context():
    """Make notification count and latest available in templates when customer is logged in."""
    if not session.get('customer_id'):
        return {}
    customer_id = session.get('customer_id')
    unread_count = Notification.query.filter_by(customer_id=customer_id, is_read=False).count()
    latest = Notification.query.filter_by(customer_id=customer_id).order_by(
        Notification.created_at.desc()
    ).limit(5).all()
    return {
        'notification_unread_count': unread_count,
        'notification_latest': latest,
    }


def _order_upload_folder():
    """Return the absolute path to the order uploads directory; create if needed."""
    folder = os.path.join(current_app.instance_path, current_app.config['UPLOAD_ORDER_FOLDER'])
    os.makedirs(folder, exist_ok=True)
    return folder


def _allowed_file_extension(filename):
    """Return the lowercased extension if allowed, else None."""
    if not filename or '.' not in filename:
        return None
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext if ext in ALLOWED_ORDER_FILE_EXTENSIONS else None


def get_current_customer():
    """Return current customer from session or None."""
    cid = session.get('customer_id')
    if not cid:
        return None
    return Customer.query.get(cid)


def customer_login_required(f):
    """Require customer to be logged in to portal."""
    from functools import wraps
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if not session.get('customer_id'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_view


@customer_bp.route('/')
@customer_bp.route('/dashboard')
@customer_login_required
def dashboard():
    """
    Customer portal dashboard: summary and recent orders for this customer.
    """
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))

    my_orders = Order.query.filter_by(customer_id=customer.id).order_by(
        Order.created_at.desc()
    ).limit(10).all()

    return render_template(
        'customer/dashboard.html',
        customer=customer,
        my_orders=my_orders,
    )


@customer_bp.route('/request', methods=['GET', 'POST'])
@customer_login_required
def place_request():
    """
    Place a service request: per-document rows (file + service + quantity + notes).
    POST uses request.files.getlist("document_file[]") and request.form.getlist("service_id[]") etc.
    """
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))

    active_services = Service.get_active_services()
    service_choices = [('', '-- Select service --')] + [
        (s.id, f'{s.service_name} — R{s.unit_price:.2f}') for s in active_services
    ]
    if len(service_choices) == 1:
        flash('No active services are available at the moment. Please try again later.', 'warning')
        return redirect(url_for('customer_portal.dashboard'))

    form = CustomerRequestForm()

    if form.validate_on_submit():
        # Per-document rows from getlist
        files_list = request.files.getlist('document_file[]')
        service_ids = request.form.getlist('service_id[]')
        quantities = request.form.getlist('quantity[]')
        item_notes_list = request.form.getlist('item_notes[]')

        # Normalize length
        n = max(len(files_list), len(service_ids), len(quantities), len(item_notes_list))
        while len(files_list) < n:
            files_list.append(None)
        while len(service_ids) < n:
            service_ids.append('')
        while len(quantities) < n:
            quantities.append('')
        while len(item_notes_list) < n:
            item_notes_list.append('')

        rows = []
        for i in range(n):
            f = files_list[i] if i < len(files_list) else None
            sid_raw = service_ids[i] if i < len(service_ids) else ''
            qty_raw = quantities[i] if i < len(quantities) else ''
            inotes = (item_notes_list[i] or '').strip() if i < len(item_notes_list) else ''
            try:
                sid = int(sid_raw) if sid_raw else None
            except (TypeError, ValueError):
                sid = None
            try:
                qty = int(qty_raw) if qty_raw else 0
            except (TypeError, ValueError):
                qty = 0
            has_file = f and getattr(f, 'filename', None)
            if has_file and sid and qty >= 1:
                rows.append((f, sid, qty, inotes))

        if not rows:
            flash('Add at least one document with a file, service, and quantity.', 'danger')
            return render_template('customer/place_request.html', customer=customer, form=form, service_choices=service_choices)

        active_ids = {s.id for s in active_services}
        for _f, sid, _qty, _inotes in rows:
            if sid not in active_ids:
                flash('Only active services can be selected.', 'danger')
                return render_template('customer/place_request.html', customer=customer, form=form, service_choices=service_choices)

        payment_option = (form.payment_option.data or '').strip() or Order.PAYMENT_OPTION_PAY_LATER
        if payment_option not in (Order.PAYMENT_OPTION_PAY_NOW, Order.PAYMENT_OPTION_PAY_LATER):
            payment_option = Order.PAYMENT_OPTION_PAY_LATER
        if payment_option == 'pay_now':
            payment_option = Order.PAYMENT_OPTION_PAY_NOW
        if payment_option == 'pay_later':
            payment_option = Order.PAYMENT_OPTION_PAY_LATER

        order = Order(
            customer_id=customer.id,
            created_by=None,
            order_date=date.today(),
            total_amount=Decimal('0.00'),
            order_status=Order.STATUS_SUBMITTED,
            payment_status=Order.PAYMENT_UNPAID,
            payment_option=payment_option,
            notes=form.notes.data.strip() or None,
        )
        db.session.add(order)
        db.session.flush()
        total = Decimal('0.00')
        upload_folder = _order_upload_folder()

        for f, sid, qty, inotes in rows:
            ext = _allowed_file_extension(f.filename) if f and f.filename else None
            if not ext:
                flash(f'Invalid or missing file for one document. Allowed: PDF, DOC, DOCX, JPG, JPEG, PNG.', 'danger')
                return render_template('customer/place_request.html', customer=customer, form=form, service_choices=service_choices)
            service = Service.query.get(sid)
            if not service or not service.active_status:
                flash('Only active services can be selected.', 'danger')
                return render_template('customer/place_request.html', customer=customer, form=form, service_choices=service_choices)
            unit_price = service.unit_price
            subtotal = Decimal(qty) * unit_price
            total += subtotal
            item = OrderItem(
                order_id=order.id,
                service_id=sid,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            db.session.add(item)
            original_filename = secure_filename(f.filename) or 'document'
            stored_filename = f'{uuid.uuid4().hex}.{ext}'
            file_path = os.path.join(current_app.config['UPLOAD_ORDER_FOLDER'], stored_filename)
            full_path = os.path.join(upload_folder, stored_filename)
            f.save(full_path)
            order_file = OrderFile(
                order_id=order.id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_path=file_path.replace(os.sep, '/'),
            )
            db.session.add(order_file)

        order.total_amount = total
        add_notification(order, 'Your service request has been submitted. We will start your job soon.')
        create_notification(
            customer_id=order.customer_id,
            title='Order submitted',
            message='Your service request has been submitted. We will start your job soon.',
            order_id=order.id,
            notification_type='info',
        )
        db.session.commit()
        flash(f'Request submitted successfully. Order #{order.id} — Total: R{order.total_amount:.2f}', 'success')
        if order.payment_option == Order.PAYMENT_OPTION_PAY_NOW:
            return redirect(url_for('customer_portal.order_pay', order_id=order.id))
        return redirect(url_for('customer_portal.order_detail', order_id=order.id))

    return render_template('customer/place_request.html', customer=customer, form=form, service_choices=service_choices)


@customer_bp.route('/orders')
@customer_login_required
def my_orders():
    """List all orders for the logged-in customer."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    orders = Order.query.filter_by(customer_id=customer.id).order_by(
        Order.created_at.desc()
    ).all()
    return render_template('customer/my_orders.html', customer=customer, orders=orders)


@customer_bp.route('/orders/<int:order_id>/pay', methods=['GET', 'POST'])
@customer_login_required
def order_pay(order_id):
    """Online card payment page for pay_now_online orders. Mock form; on submit sets paid + card."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    order = Order.query.filter_by(id=order_id, customer_id=customer.id).first_or_404()
    if order.payment_option != Order.PAYMENT_OPTION_PAY_NOW:
        return redirect(url_for('customer_portal.order_detail', order_id=order.id))
    if order.payment_status == Order.PAYMENT_PAID:
        flash('This order has already been paid.', 'info')
        return redirect(url_for('customer_portal.order_detail', order_id=order.id))
    from app.forms.payment_forms import OnlineCardPaymentForm
    from app.services.order_workflow import confirm_online_payment
    form = OnlineCardPaymentForm()
    if form.validate_on_submit():
        ok, err = confirm_online_payment(order)
        if not ok:
            flash(err or 'Payment could not be processed.', 'danger')
            return render_template('customer/order_pay.html', customer=customer, order=order, form=form)
        db.session.commit()
        flash('Payment successful. Your order will be processed shortly.', 'success')
        return redirect(url_for('customer_portal.order_detail', order_id=order.id))
    return render_template('customer/order_pay.html', customer=customer, order=order, form=form)


@customer_bp.route('/orders/<int:order_id>')
@customer_login_required
def order_detail(order_id):
    """View one order (only if it belongs to this customer)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    order = Order.query.filter_by(id=order_id, customer_id=customer.id).first_or_404()
    return render_template('customer/order_detail.html', customer=customer, order=order)


@customer_bp.route('/orders/<int:order_id>/files/<int:file_id>/download')
@customer_login_required
def order_file_download(order_id, file_id):
    """Download an order file (only if order belongs to this customer)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    order = Order.query.filter_by(id=order_id, customer_id=customer.id).first_or_404()
    order_file = OrderFile.query.filter_by(id=file_id, order_id=order.id).first_or_404()
    folder = os.path.join(current_app.instance_path, current_app.config['UPLOAD_ORDER_FOLDER'])
    return send_from_directory(
        folder,
        order_file.stored_filename,
        as_attachment=True,
        download_name=order_file.original_filename,
    )


@customer_bp.route('/receipts')
@customer_login_required
def receipts():
    """List receipts for this customer's paid orders."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    # Receipts for orders belonging to this customer
    receipts_list = Receipt.query.join(Order).filter(
        Order.customer_id == customer.id
    ).order_by(Receipt.generated_date.desc()).all()
    return render_template('customer/receipts.html', customer=customer, receipts_list=receipts_list)


@customer_bp.route('/profile')
@customer_login_required
def profile():
    """View and manage profile (view for now)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    return render_template('customer/profile.html', customer=customer)


# --- Notifications (navbar bell + list page) ---


@customer_bp.route('/notifications')
@customer_login_required
def notifications_list():
    """List all notifications for the logged-in customer."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    notifications = Notification.query.filter_by(customer_id=customer.id).order_by(
        Notification.created_at.desc()
    ).all()
    return render_template('customer/notifications.html', customer=customer, notifications=notifications)


@customer_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@customer_login_required
def notification_mark_read(notification_id):
    """Mark a single notification as read and redirect back or to order."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    n = Notification.query.filter_by(id=notification_id, customer_id=customer.id).first_or_404()
    n.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'success')
    redirect_to = request.args.get('next') or url_for('customer_portal.notifications_list')
    if n.order_id and request.args.get('next') is None:
        redirect_to = url_for('customer_portal.order_detail', order_id=n.order_id)
    return redirect(redirect_to)


@customer_bp.route('/notifications/read-all', methods=['POST'])
@customer_login_required
def notification_mark_all_read():
    """Mark all notifications as read for the current customer."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.login'))
    Notification.query.filter_by(customer_id=customer.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('customer_portal.notifications_list'))
