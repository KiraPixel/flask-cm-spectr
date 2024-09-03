from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from .utils import login_required
from .models import db, User

architect = Blueprint('architect', __name__)


@architect.route('/')
@login_required
def index():
    return render_template('architect/main_architect.html')