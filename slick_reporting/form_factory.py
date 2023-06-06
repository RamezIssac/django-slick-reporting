import warnings

# warn deprecated
warnings.warn(
    "slick_reporting.form_factory is deprecated. Use slick_reporting.forms instead",
    Warning,
    stacklevel=2,
)

from .forms import *  # noqa
