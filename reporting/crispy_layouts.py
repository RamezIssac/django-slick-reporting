from crispy_forms.bootstrap import InlineField, Accordion, Field
from ra.base import app_settings

class StackedField(InlineField):
    template = "ra/%s/layout/stacked_field.html"


class StackedField2(InlineField):
    template = f"{app_settings.RA_THEME}/layout/stacked_field2.html"


class EnhancedAccordion(Accordion):
    template = "ra/%s/enhanced-accordion.html"


class UserName(Field):
    template = "ra/%s/username_field.html"
