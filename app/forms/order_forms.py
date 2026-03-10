"""
Order forms for City Printers CRM.
Create order: select customer and add one or more service items (service, quantity).
Unit price and subtotal are taken from the active service at save time.
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, FieldList, FormField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError


def _coerce_service_id(x):
    """Coerce service_id to int or None for optional rows."""
    if x is None or x == '':
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


class OrderItemForm(FlaskForm):
    """
    Single line item: service (from active services) and quantity.
    Both optional so multiple rows can be shown and only some filled.
    unit_price and subtotal are set server-side from the selected service.
    """
    service_id = SelectField('Service', coerce=_coerce_service_id, validators=[Optional()])
    quantity = IntegerField(
        'Quantity',
        validators=[Optional(), NumberRange(min=1, message='Quantity must be at least 1.')],
        default=1
    )


class OrderCreateForm(FlaskForm):
    """
    Create a new order: customer (required) and at least one order item.
    Only active services are allowed; total is calculated from items.
    """
    customer_id = SelectField(
        'Customer',
        coerce=int,
        validators=[DataRequired(message='Select a customer.')]
    )
    items = FieldList(FormField(OrderItemForm), min_entries=3)
    submit = SubmitField('Create Order')

    def validate_items(self, field):
        """At least one item must have both service_id and quantity; only active services allowed."""
        from app.models.service import Service
        active_ids = {s.id for s in Service.get_active_services()}
        filled = 0
        for entry in field.entries:
            sid = entry.service_id.data
            qty = entry.quantity.data
            if sid is None or (isinstance(sid, str) and sid.strip() == ''):
                continue
            try:
                sid = int(sid)
            except (TypeError, ValueError):
                continue
            if qty is None or qty < 1:
                continue
            if sid not in active_ids:
                raise ValidationError('Only active services can be added to an order.')
            filled += 1
        if filled == 0:
            raise ValidationError('At least one order item with service and quantity is required.')
