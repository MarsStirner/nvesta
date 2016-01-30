# -*- coding: utf-8 -*-
from fanstatic import Group
from js.ui_bootstrap import ui_bootstrap
from js.angular import angular, angular_sanitize, angular_route
from js.momentjs import moment_timezone_with_data
from js.underscore import underscore
from js.fontawesome import fontawesome

__author__ = 'viruzzz-kun'


group = Group([
    ui_bootstrap, angular, angular_sanitize, angular_route, moment_timezone_with_data, underscore, fontawesome
])