"""
Payment forms for City Printers CRM.
Full payment only; amount must equal order total (validated in view).
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


# Counter payment only (pay_later_counter orders)
COUNTER_PAYMENT_METHOD = 'counter'

# Allowed payment methods for counter (admin/cashier)
PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('Card', 'Card'),
    ('EFT', 'EFT'),
    ('Mobile', 'Mobile'),
]


class OnlineCardPaymentForm(FlaskForm):
    """Mock online card payment form (demo)."""
    card_number = StringField('Card number', validators=[DataRequired(), Length(min=12, max=19)])
    card_name = StringField('Name on card', validators=[DataRequired(), Length(max=100)])
    expiry = StringField('Expiry (MM/YY)', validators=[DataRequired(), Length(min=4, max=5)])
    cvv = StringField('CVV', validators=[DataRequired(), Length(min=3, max=4)])
    submit = SubmitField('Pay now')


class PaymentForm(FlaskForm):
    """
    Record full payment for an order.
    - payment_method: required, one of Cash/Card/EFT/Mobile.
    - amount_paid: required, must equal order.total_amount (enforced in view).
    """
    payment_method = SelectField(
        'Payment Method',
        choices=PAYMENT_METHODS,
        validators=[DataRequired(message='Select a payment method.')]
    )
    amount_paid = FloatField(
        'Amount Paid (R)',
        validators=[
            DataRequired(message='Amount is required.'),
            NumberRange(min=0.01, message='Amount must be greater than 0.')
        ],
        render_kw={'readonly': True, 'step': '0.01'}
    )
    submit = SubmitField('Record Payment')
