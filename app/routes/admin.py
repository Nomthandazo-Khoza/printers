"""
Admin blueprint: dashboard, customer view, service management, (later) user/order/reports.
"""
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user
from app.routes.decorators import admin_required, staff_required
from app import db
from app.models.user import User
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.order_file import OrderFile
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.service import Service
from sqlalchemy.orm import joinedload
from app.forms.customer_forms import CustomerSearchForm
from app.forms.service_forms import ServiceForm
from datetime import datetime, date
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)


def _search_customers(query):
    """Search customers by name, phone, or email. Returns base query. Case-insensitive."""
    if not (query and query.strip()):
        return Customer.query.order_by(Customer.last_name, Customer.first_name)
    q = query.strip()
    term = f'%{q}%'
    return Customer.query.filter(
        db.or_(
            db.func.lower(Customer.first_name).like(db.func.lower(term)),
            db.func.lower(Customer.last_name).like(db.func.lower(term)),
            db.func.lower(Customer.email).like(db.func.lower(term)),
            Customer.phone_number.like(term),
        )
    ).order_by(Customer.last_name, Customer.first_name)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@staff_required
def dashboard():
    """
    Admin dashboard: totals, today's stats, recent orders, recent customers.
    """
    # Counts
    total_customers = Customer.query.count()
    orders_today = Order.query.filter(db.func.date(Order.order_date) == date.today()).count()
    orders_in_progress = Order.query.filter_by(order_status=Order.STATUS_IN_PROGRESS).count()
    completed = Order.query.filter_by(order_status=Order.STATUS_COMPLETED).count()

    # Revenue today (from payments for orders with order_date today)
    from app.models.payment import Payment
    revenue_today = db.session.query(db.func.coalesce(db.func.sum(Payment.amount_paid), 0)).join(
        Order
    ).filter(db.func.date(Order.order_date) == date.today()).scalar() or 0

    # Recent orders (last 10)
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(10).all()

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        orders_today=orders_today,
        revenue_today=revenue_today,
        orders_in_progress=orders_in_progress,
        completed_jobs=completed,
        recent_orders=recent_orders,
        recent_customers=recent_customers,
    )


# --- Customer Management (admin: view only - list and detail) ---


@admin_bp.route('/customers')
@staff_required
def customer_list():
    """List all customers with optional search."""
    form = CustomerSearchForm()
    q = request.args.get('q', '').strip()
    if q:
        form.q.data = q
    customers = _search_customers(q).all()
    return render_template('admin/customers/list.html', customers=customers, form=form)


@admin_bp.route('/customers/<int:customer_id>')
@staff_required
def customer_detail(customer_id):
    """View customer details (read-only)."""
    customer = Customer.query.get_or_404(customer_id)
    orders = customer.orders.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('admin/customers/detail.html', customer=customer, orders=orders)


# --- Service Management (admin only: list, create, edit, activate/deactivate) ---


@admin_bp.route('/services')
@admin_required
def service_list():
    """List all services (active and inactive)."""
    services = Service.query.order_by(Service.service_name).all()
    return render_template('admin/services/list.html', services=services)


@admin_bp.route('/services/create', methods=['GET', 'POST'])
@admin_required
def service_create():
    """Add a new service."""
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            service_name=form.service_name.data.strip(),
            description=form.description.data.strip() or None,
            unit_price=Decimal(str(form.unit_price.data)),
            active_status=form.active_status.data,
        )
        db.session.add(service)
        db.session.commit()
        flash(f'Service "{service.service_name}" added successfully.', 'success')
        return redirect(url_for('admin.service_list'))
    return render_template('admin/services/create.html', form=form)


@admin_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@admin_required
def service_edit(service_id):
    """Edit service details and activate/deactivate."""
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    form._obj = service  # for unique name validator
    # Coerce Decimal to float for form
    if request.method == 'GET':
        form.unit_price.data = float(service.unit_price)
    if form.validate_on_submit():
        service.service_name = form.service_name.data.strip()
        service.description = form.description.data.strip() or None
        service.unit_price = Decimal(str(form.unit_price.data))
        service.active_status = form.active_status.data
        db.session.commit()
        flash(f'Service "{service.service_name}" updated successfully.', 'success')
        return redirect(url_for('admin.service_list'))
    return render_template('admin/services/edit.html', form=form, service=service)


@admin_bp.route('/services/<int:service_id>/toggle-status', methods=['POST'])
@admin_required
def service_toggle_status(service_id):
    """Activate or deactivate a service (quick toggle from list)."""
    service = Service.query.get_or_404(service_id)
    service.active_status = not service.active_status
    db.session.commit()
    status = 'activated' if service.active_status else 'deactivated'
    flash(f'Service "{service.service_name}" {status}.', 'success')
    return redirect(url_for('admin.service_list'))


# --- Order Management (admin: view only - list and detail) ---


@admin_bp.route('/orders')
@staff_required
def order_list():
    """List all service orders (newest first)."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders/list.html', orders=orders)


@admin_bp.route('/orders/<int:order_id>')
@staff_required
def order_detail(order_id):
    """View order details (read-only): customer, items, total, status. Shows Paid/Unpaid and View Receipt if paid."""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/orders/detail.html', order=order)


@admin_bp.route('/orders/<int:order_id>/workflow', methods=['POST'])
@staff_required
def order_workflow_action(order_id):
    """
    Perform workflow action: start_job, mark_job_complete, ready_for_collection, mark_collected.
    """
    from app.services.order_workflow import (
        start_job, mark_job_complete, mark_ready_for_collection, mark_collected,
    )
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')
    ok, err = False, 'Unknown action'
    if action == 'start_job':
        ok, err = start_job(order)
        if ok:
            flash('Job started.', 'success')
    elif action == 'mark_job_complete':
        ok, err = mark_job_complete(order)
        if ok:
            flash('Job marked complete. Order is now awaiting payment.', 'success')
    elif action == 'ready_for_collection':
        ok, err = mark_ready_for_collection(order)
        if ok:
            flash('Order marked ready for collection. Customer will see the notification.', 'success')
    elif action == 'mark_collected':
        ok, err = mark_collected(order)
        if ok:
            flash('Order marked as collected.', 'success')
    if not ok:
        flash(err or 'Invalid transition.', 'danger')
    db.session.commit()
    return redirect(url_for('admin.order_detail', order_id=order.id))


@admin_bp.route('/orders/<int:order_id>/confirm-payment', methods=['GET', 'POST'])
@staff_required
def order_confirm_payment(order_id):
    """Admin: Confirm counter payment (pay_later_counter orders only)."""
    from app.services.order_workflow import confirm_payment
    from app.forms.payment_forms import PaymentForm
    order = Order.query.get_or_404(order_id)
    if order.payment_option != Order.PAYMENT_OPTION_PAY_LATER:
        flash('Only "Pay After Order Is Done" orders can be paid at the counter.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    if order.payment:
        flash('This order already has a payment recorded.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    if not order.can_confirm_payment():
        flash('Cannot record payment for this order.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    form = PaymentForm()
    form.amount_paid.data = float(order.total_amount)
    if form.validate_on_submit():
        amount = Decimal(str(form.amount_paid.data))
        if amount != order.total_amount:
            flash(f'Amount must equal order total (R {order.total_amount:.2f}).', 'danger')
            return render_template('admin/orders/confirm_payment.html', order=order, form=form)
        ok, err = confirm_payment(
            order, amount, Order.PAYMENT_METHOD_COUNTER,
            recorded_by_user_id=current_user.id,
        )
        if not ok:
            flash(err or 'Could not record payment.', 'danger')
            return redirect(url_for('admin.order_detail', order_id=order.id))
        db.session.commit()
        flash(f'Payment of R {amount:.2f} recorded. Receipt generated.', 'success')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    return render_template('admin/orders/confirm_payment.html', order=order, form=form)


@admin_bp.route('/orders/<int:order_id>/receipt')
@staff_required
def order_receipt(order_id):
    """View/print receipt for a paid order (read-only)."""
    order = Order.query.get_or_404(order_id)
    if not order.payment:
        flash('No payment recorded for this order.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    if not order.receipt:
        flash('Receipt not found for this order.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    return render_template(
        'admin/orders/receipt.html',
        order=order,
        payment=order.payment,
        receipt=order.receipt,
    )


@admin_bp.route('/orders/<int:order_id>/files/<int:file_id>/download')
@staff_required
def order_file_download(order_id, file_id):
    """Download an order file (admin)."""
    order = Order.query.get_or_404(order_id)
    order_file = OrderFile.query.filter_by(id=file_id, order_id=order.id).first_or_404()
    folder = os.path.join(current_app.instance_path, current_app.config['UPLOAD_ORDER_FOLDER'])
    return send_from_directory(
        folder,
        order_file.stored_filename,
        as_attachment=True,
        download_name=order_file.original_filename,
    )


# --- Payments (staff: list pending_payment orders, confirm counter payment) ---


@admin_bp.route('/payments')
@staff_required
def payments_list():
    """List orders with payment_status = pending_payment for staff to confirm counter payment."""
    orders = Order.query.filter_by(payment_status=Order.PAYMENT_PENDING).order_by(
        Order.created_at.desc()
    ).options(joinedload(Order.customer), joinedload(Order.items).joinedload(OrderItem.service)).all()
    return render_template('admin/payments/list.html', orders=orders)


# --- Reports (admin only) ---


@admin_bp.route('/reports')
@admin_required
def reports():
    """Admin reports: summary cards and tables (recent payments, popular services, recent orders)."""
    today = date.today()
    orders_today = Order.query.filter(db.func.date(Order.order_date) == today).count()
    revenue_today = db.session.query(db.func.coalesce(db.func.sum(Payment.amount_paid), 0)).join(
        Order
    ).filter(db.func.date(Order.order_date) == today).scalar()
    if revenue_today is None:
        revenue_today = 0
    orders_in_progress = Order.query.filter_by(order_status=Order.STATUS_IN_PROGRESS).count()
    completed_orders_today = Order.query.filter(
        db.func.date(Order.order_date) == today,
        Order.order_status == Order.STATUS_COMPLETED
    ).count()
    total_customers = Customer.query.count()

    recent_payments = Payment.query.options(
        joinedload(Payment.order).joinedload(Order.customer),
        joinedload(Payment.order).joinedload(Order.receipt)
    ).order_by(Payment.payment_date.desc()).limit(20).all()

    popular_services = db.session.query(
        Service.service_name,
        db.func.count(OrderItem.id).label('times_used'),
        db.func.coalesce(db.func.sum(OrderItem.quantity), 0).label('total_quantity')
    ).join(OrderItem, Service.id == OrderItem.service_id).group_by(
        Service.id, Service.service_name
    ).order_by(db.func.count(OrderItem.id).desc()).limit(10).all()

    recent_orders = Order.query.options(joinedload(Order.customer)).order_by(
        Order.created_at.desc()
    ).limit(20).all()

    return render_template(
        'admin/reports/index.html',
        orders_today=orders_today,
        revenue_today=revenue_today,
        orders_in_progress=orders_in_progress,
        completed_orders_today=completed_orders_today,
        total_customers=total_customers,
        recent_payments=recent_payments,
        popular_services=popular_services,
        recent_orders=recent_orders,
    )
