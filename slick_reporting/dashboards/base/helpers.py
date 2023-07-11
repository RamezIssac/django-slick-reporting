import logging
from collections.abc import Iterable

from django.apps import apps
from django.conf import settings
from django.db.models import Max
from django.utils.translation import get_language

logger = logging.getLogger(__name__)

get_model = apps.get_model


def get_obj_from_list(lst, key, val):
    return get_from_list(False, lst, key, val)


def get_from_list(by_getattr, lst, attr_name, val):
    """
    Gets an object from the supplied list by `getattr` or by `__item__`
    :param by_getattr: Use getattr, if False we use __item__ (dict access)
    :param lst: list of the objects
    :param attr_name: Or Key
    :param val: value we search for
    :return: The Item if found else return False
    """

    def get_by_key(_dict, _key):
        return _dict[_key]

    if by_getattr:
        lookup = getattr
    else:
        lookup = get_by_key
    for l in lst:
        if lookup(l, attr_name) == val:
            return l
    return False


class RaPermissionWidgetExclude(object):
    def __call__(self, model):
        from erp_framework.base.models import TransactionItemModel, BaseReportModel

        if (
            TransactionItemModel in model.__mro__
            or BaseReportModel in model.__mro__
            or model._meta.managed is False
        ):
            return True
        if model._meta.auto_created:
            return True
        return False


# def order_apps(app_list):
#     """Called in admin/base_site.html template override and applies custom ordering of
#     apps/models defined by settings.ADMIN_REORDER
#     """
#     from . import app_settings
#
#     # sort key function - use index of item in order if exists, otherwise item
#     sort = lambda order, item: (
#         (order.index(item), "") if item in order else (len(order), item)
#     )
#
#     # sort the app list
#     order = OrderedDict(app_settings.ADMIN_REORDER)
#     app_list.sort(
#         key=lambda app: sort(order.keys(), app["app_url"].strip("/").split("/")[-1])
#     )
#     for i, app in enumerate(app_list):
#         # sort the model list for each app
#         app_name = app["app_url"].strip("/").split("/")[-1]
#         model_order = [m.lower() for m in order.get(app_name, [])]
#         app_list[i]["models"].sort(
#             key=lambda model: sort(
#                 model_order, model.get("admin_url", "").strip("/").split("/")[-1]
#             )
#         )
#     return app_list
#

# def admin_get_app_list(request, admin_site):
#     """
#     :param request: Copied from AdminSite.index() djagno v1.8
#     :param admin_site:
#     :return:
#     """
#     from erp_framework.base.app_settings import RA_MENU_HIDE_MODELS, ERP_FRAMEWORK_SITE_NAME
#
#     app_dict = {}
#     for model, model_admin in admin_site._registry.items():
#         app_label = model._meta.app_label
#         has_module_perms = model_admin.has_module_permission(request)
#
#         is_model_hidden = (
#             "%s_%s" % (app_label, model.__name__.lower()) in RA_MENU_HIDE_MODELS
#         )
#
#         if has_module_perms and not is_model_hidden:
#             perms = model_admin.get_model_perms(request)
#
#             # Check whether user has any perm for this module.
#             # If so, add the module to the model_list.
#             if True in perms.values():
#                 info = (ERP_FRAMEWORK_SITE_NAME, app_label, model._meta.model_name)
#                 model_dict = {
#                     "name": capfirst(model._meta.verbose_name_plural),
#                     "object_name": model._meta.object_name,
#                     "perms": perms,
#                     "model_class": model,
#                 }
#                 if (
#                     perms.get("view", False)
#                     or perms.get("change", False)
#                     or perms.get("add", False)
#                 ):
#                     try:
#                         model_dict["admin_url"] = reverse(
#                             "%s:%s_%s_changelist" % info, current_app=admin_site.name
#                         )
#                     except NoReverseMatch:
#                         pass
#                 if perms.get("add", False):
#                     try:
#                         model_dict["add_url"] = reverse(
#                             "%s:%s_%s_add" % info, current_app=admin_site.name
#                         )
#                     except NoReverseMatch:
#                         pass
#                 if app_label in app_dict:
#                     app_dict[app_label]["models"].append(model_dict)
#                 else:
#                     app_dict[app_label] = {
#                         "name": apps.get_app_config(app_label).verbose_name,
#                         "app_label": app_label,
#                         "app_url": reverse(
#                             "%s:app_list" % ERP_FRAMEWORK_SITE_NAME,
#                             kwargs={"app_label": app_label},
#                             current_app=admin_site.name,
#                         ),
#                         "has_module_perms": has_module_perms,
#                         "models": [model_dict],
#                     }
#
#     # Sort the apps alphabetically.
#     app_list = list(app_dict.values())
#     app_list.sort(key=lambda x: x["name"].lower())
#
#     # Sort the models alphabetically within each app.
#     for app in app_list:
#         app["models"].sort(key=lambda x: x["name"])
#
#     return order_apps(app_list)


def dictsort(value, arg, desc=False):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    return sorted(value, key=lambda x: x[arg], reverse=desc)


#
# def get_ra_relevant_content_types():
#     """
#     This method scans the content type and show only what relevant based on the the exclude function supplied to
#     tabular_permissions
#     #todo make a separate function that might fall back to tabular_permissions
#     :return:
#     """
#     from django.contrib.contenttypes.models import ContentType
#     from erp_framework.base.models import BaseReportModel
#     from tabular_permissions.app_settings import EXCLUDE_FUNCTION
#
#     relevant_ct = []
#     cs = ContentType.objects.all()
#     exclude_function = EXCLUDE_FUNCTION
#     for c in cs:
#         model = c.model_class()
#         if not model:
#             continue
#         if BaseReportModel in model.__mro__:
#             continue
#         if model:
#             if not exclude_function(model):
#                 relevant_ct.append((c.pk, str(model._meta.verbose_name_plural)))
#
#     return relevant_ct


def get_next_serial(model, slug_field="slug"):
    """
    Get the next serial to put in the slug based on the maximum slug found + 1
    :param model: the model to get the next serial for
    :return: a string
    """
    import time

    qs = model.objects.aggregate(Max(slug_field))
    max_slug = qs.get(f"{slug_field}__max", 0) or 0
    if type(max_slug) is str and not max_slug.isdigit():
        return str(time.time()).split(".")[0]
    return int(max_slug) + 1


def default_formfield_for_dbfield(model_admin, db_field, form_field, request, **kwargs):
    """
    A system wide hook to change how db_field are displayed as formfields
    :param model_admin: the ModelAdmin instance
    :param db_field: db_field
    :param form_field: the default form_field
    :param request: the current request

    :return: form_field to be used
    """
    return form_field


def flatten_list(items):
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            yield from flatten_list(x)
        else:
            yield x


def admin_site_access_permission(request):
    if settings.DEBUG:
        return True
    return request.user.is_active and request.user.is_staff


def report_access_function(request, permission, report):
    from erp_framework.reporting.registry import report_registry

    if settings.DEBUG:
        return True

    return report_registry.has_perm(
        request.user, report.get_report_code(), permission=permission
    )


def get_each_context(request, admin_site):
    context = {}
    current_language = get_language() or ""
    cache_key = "app_list_%s_%s" % (request.user.pk, current_language)
    # cache_val = cache.get(cache_key)
    # if not cache_val or settings.DEBUG:
    #     cache_val = admin_get_app_list(request, admin_site)
    #     cache.set(cache_key, cache_val)
    # context["app_list"] = cache_val
    context["admin_site"] = admin_site
    return context
