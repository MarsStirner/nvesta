# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

__author__ = 'viruzzz-kun'


module = Blueprint('admin', __name__, template_folder='templates', static_folder='static')


@module.route('/')
def index():
    return render_template(
        'admin/base.html',
    )
