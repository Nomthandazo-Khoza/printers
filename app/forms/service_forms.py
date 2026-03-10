"""
Service forms for City Printers CRM.
Admin-only: create and edit services (name, description, unit_price, active_status).
"""
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


def _service_name_unique(form, field):
    """Validate service name is unique (for edit, exclude current service via form._obj)."""
    from app.models.service import Service
    name = (field.data or '').strip()
    if not name:
        return
    q = Service.query.filter(Service.service_name == name)
    if getattr(form, '_obj', None):
        q = q.filter(Service.id != form._obj.id)
    if q.first():
        raise ValidationError('A service with this name already exists.')


class ServiceForm(FlaskForm):
    """
    Single form for both create and edit service.
    - service_name: required, unique.
    - unit_price: required, must be > 0.
    - description: optional.
    - active_status: used on edit; on create defaults to True in view.
    """
    service_name = StringField(
        'Service Name',
        validators=[DataRequired(), Length(max=120), _service_name_unique]
    )
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    unit_price = FloatField(
        'Unit Price (R)',
        validators=[
            DataRequired(message='Unit price is required.'),
            NumberRange(min=0.01, message='Unit price must be greater than 0.')
        ],
        render_kw={'step': '0.01', 'min': '0.01'}
    )
    active_status = BooleanField('Active (available for new orders)', default=True)
    submit = SubmitField('Save Service')
