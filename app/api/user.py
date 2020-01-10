from flask import request, g, jsonify
from . import api
from .. import db, create_app
from ..models import User, Role
from ..decorators import json, paginate
from ..auth import auth_token
from ..utils import allowed_file
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from flask import url_for, current_app

@api.route('/lawyers', methods=['GET'])
@json
@paginate('lawyers')
@auth_token.login_required
def get_lawyers():
    role = Role.query.filter_by(name='Lawyer').first()
    return User.query.filter_by(role=role)

@api.route('/users', methods=['GET'])
@json
@paginate('users')
@auth_token.login_required
def get_users():
    role = Role.query.filter_by(name='User').first()
    return User.query.filter_by(role=role)

@api.route('/user/<int:id>', methods=['GET'])
@json
@auth_token.login_required
def get_user(id):
    return User.query.get_or_404(id)

@api.route('/profile', methods=['GET'])
@json
@auth_token.login_required
def profile():
    return g.user

@api.route('/user', methods=['POST'])
@json
def new_user():
    user = User()
    role = Role.query.filter_by(name='User').first()
    user.import_data(request.json)
    user.role = role
    db.session.add(user)
    db.session.commit()
    return {'token': user.generate_auth_token(), 'user': user.export_data()}

@api.route('/login', methods=['POST'])
@json
def login():
    user = User.query.filter_by(email=request.json.get('email')).first()
    if user is not None and user.verify_password(request.json.get('password')):
        return {'token': user.generate_auth_token(), 'user': user.export_data(), 'failed':False}
    return {'failed': True}

@api.route('/lawyer', methods=['POST'])
@json
def new_lawyer():
    user = User()
    role = Role.query.filter_by(name='Lawyer').first()
    user.import_data(request.json)
    user.role = role
    db.session.add(user)
    db.session.commit()
    return {'token': user.generate_auth_token(), 'user': user.export_data()}


@api.route('/upload_user_photo', methods=['POST'])
@json
@auth_token.login_required
def upload_user_photo():
    app = create_app('production')
    user = g.user
    image = request.files['image']
    if image and allowed_file(image.filename):
        imagename = "{:%I%M%S%f%d%m%Y}".format(datetime.now()) + secure_filename(image.filename)
        image.save(os.path.join(app.config['USER_UPLOAD_FOLDER'], imagename))
        user.image = imagename
    db.session.add(user)
    db.session.commit()
    return {'token': user.generate_auth_token(), 'user': user.export_data()}

@api.route('/edit-user/<int:id>', methods=['POST'])
@json
@auth_token.login_required
def edit_user(id):
    user = User.query.get_or_404(id)
    user.import_data(request.json)
    db.session.add(user)
    db.session.commit()
    return {'token': user.generate_auth_token(), 'user': user.export_data()}


@api.route('/search', methods=['POST'])
@auth_token.login_required
def search():
    query = request.json.get('query')
    users =  User.query.whoosh_search(query).all()
    role = Role.query.filter_by(name='Lawyer').first()
    lawyers = []
    for user in users:
        if user.role != role:
            continue
        lawyers.append(user.export_data())
    return jsonify({'result': lawyers})
    
