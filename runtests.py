#!/usr/bin/env python
import os
import sys

import argparse
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Django Slick Reporting test suite.")
    parser.add_argument(
        'modules', nargs='*', metavar='module',
        help='Optional path(s) to test modules; e.g. "i18n" or '
             '"i18n.tests.TranslationTests.test_lazy_objects".',
    )
    options = parser.parse_args()

    options.modules = [os.path.normpath(labels) for labels in options.modules]


    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(options.modules)
    # failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))

