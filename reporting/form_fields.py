from __future__ import unicode_literals

import json

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AutocompleteSelectMultiple, SELECT2_TRANSLATIONS
from django.utils.translation import get_language


class RaDateDateTimeField(forms.SplitDateTimeField):
    """
    Make sure to translate arabic numbers to western numbers so
    default operation can carry on smoothly.
    """

    def clean(self, value):
        from ra.utils.views import easter_western_map
        new_value = []
        for i in value:
            if type(i) in [str]:
                new_value.append(i.translate(easter_western_map))
            else:
                new_value.append(i)
        return super(RaDateDateTimeField, self).clean(new_value)


class RaAutocompleteSelectMultiple(AutocompleteSelectMultiple):

    def __init__(self, rel, admin_site, attrs=None, choices=(), using=None):
        super().__init__(rel, admin_site, attrs, choices, using)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.allow_multiple_selected:
            context['widget']['attrs']['multiple'] = 'multiple'
            # del context['widget']['attrs']['name']
        return context

    def build_attrs(self, base_attrs, extra_attrs=None):
        """
        Set select2's AJAX attributes.

        Attributes can be set using the html5 data attribute.
        Nested attributes require a double dash as per
        https://select2.org/configuration/data-attributes#nested-subkey-options
        """

        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs.pop('id')
        attrs.setdefault('class', '')
        attrs.update({
            'data-ajax--cache': 'true',
            'data-ajax--type': 'GET',
            'data-ajax--url': self.get_url(),
            'data-theme': 'bootstrap4',
            'data-allow-clear': json.dumps(not self.is_required),
            'data-placeholder': '',  # Allows clearing of the input.
            'class': attrs['class'] + (' ' if attrs['class'] else '') + 'admin-autocomplete',
            # 'multiple': "multiple",
            # 'style': 'width:100%',
        })
        return attrs

    @property
    def media(self):
        extra = '' if settings.DEBUG else '.min'
        i18n_name = SELECT2_TRANSLATIONS.get(get_language())
        i18n_file = ('admin/js/vendor/select2/i18n/%s.js' % i18n_name,) if i18n_name else ()
        return forms.Media(
            js=(
                   # 'admin/js/vendor/jquery/jquery%s.js' % extra,
                   # 'admin/js/vendor/select2/select2.full%s.js' % extra,
               ) + i18n_file + (
                   # 'admin/js/jquery.init.js',
                   # 'admin/js/autocomplete.js',
               ),
            css={
                'screen': (
                    # 'admin/css/vendor/select2/select2%s.css' % extra,
                    # 'admin/css/autocomplete.css',
                ),
            },
        )
