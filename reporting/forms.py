from __future__ import unicode_literals

from django import forms


class OrderByForm(forms.Form):
    order_by = forms.CharField(required=False)

    def get_order_by(self, default_field=None):
        """
        Get the order by specified by teh form or the default field if provided
        :param default_field:
        :return: tuple of field and direction
        """
        if self.is_valid():
            order_field = self.cleaned_data['order_by']
            order_field = order_field or default_field
            if order_field:
                return self.parse_order_by_field(order_field)
        return None, None

    def parse_order_by_field(self, order_field):
        """
        Specify the field and direction
        :param order_field: the field to order by
        :return: tuple of field and direction
        """
        if order_field:
            asc = True
            if order_field[0:1] == '-':
                order_field = order_field[1:]
                asc = False
            return order_field, not asc
        return None, None
