from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from .utils import need_access, need_access
from .models import db, User

reports = Blueprint('reports', __name__)


@reports.route('/')
@need_access(1)
def index():
    return render_template('architect/main_architect.html')