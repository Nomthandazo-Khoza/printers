"""
Customer order/request forms for City Printers CRM.
Per-document rows (file + service + quantity + notes) are submitted via getlist; this form covers payment and general notes.
"""
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, RadioField
from wtforms.validators import Optional, DataRequired

# Allowed extensions for order document uploads (lowercase)
ALLOWED_ORDER_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}


class CustomerRequestForm(FlaskForm):
    """
    Payment option and general instructions. Document rows use raw request.files.getlist / request.form.getlist.
    """
    payment_option = RadioField(
        'Payment',
        choices=[
            ('pay_now_online', 'Pay Now'),
            ('pay_later_counter', 'Pay After Order Is Done'),
        ],
        validators=[DataRequired(message='Please choose a payment option.')],
        default='pay_later_counter',
    )
    notes = TextAreaField('General instructions', validators=[Optional()])
    submit = SubmitField('Submit Request')
