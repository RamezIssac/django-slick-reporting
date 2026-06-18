from threading import Lock

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver


class DashboardReportRegistry:
    """
    Lazily walks the root URL resolver to discover all ReportView-backed URL patterns.
    Results are cached after first access.
    """

    def __init__(self):
        self._cache = None
        self._lock = Lock()

    def _walk_patterns(self, patterns, namespace=None):
        from slick_reporting.views import ReportViewBase

        results = []
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                ns = pattern.namespace
                if namespace and ns:
                    full_ns = f"{namespace}:{ns}"
                elif ns:
                    full_ns = ns
                else:
                    full_ns = namespace
                results.extend(self._walk_patterns(pattern.url_patterns, full_ns))
            elif isinstance(pattern, URLPattern):
                if not pattern.name:
                    continue
                view_class = getattr(pattern.callback, "view_class", None)
                if view_class is None:
                    continue
                try:
                    is_report = issubclass(view_class, ReportViewBase)
                except TypeError:
                    continue
                if not is_report:
                    continue
                url_name = f"{namespace}:{pattern.name}" if namespace else pattern.name
                results.append(
                    {
                        "url_name": url_name,
                        "title": view_class.get_report_title(),
                        "report_slug": view_class.get_report_slug(),
                        "description": getattr(view_class, "report_description", ""),
                    }
                )
        return results

    def get_available_reports(self):
        if self._cache is not None:
            return self._cache
        with self._lock:
            if self._cache is None:
                resolver = get_resolver()
                self._cache = self._walk_patterns(resolver.url_patterns)
        return self._cache

    def clear_cache(self):
        with self._lock:
            self._cache = None


report_registry = DashboardReportRegistry()
