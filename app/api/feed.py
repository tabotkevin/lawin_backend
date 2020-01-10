from flask import request, g, jsonify, url_for
from . import api
from .. import db, create_app
from ..models import Feed, Comment, User, Like
from ..decorators import json, paginate
from werkzeug.utils import secure_filename
from ..utils import allowed_file
from ..auth import auth_token
from datetime import datetime

import os
from flask import url_for, current_app



def get_author_image(id):
    user = User.query.get_or_404(id)
    if user.image is None:
        return 'false'
    return url_for('static', filename='images/users/'+user.image, _external=True)

@api.route('/feeds', methods=['GET'])
@json
@paginate('feeds')
@auth_token.login_required
def get_feeds():
    return Feed.query.order_by(Feed.timestamp.desc())

@api.route('/feed/<int:id>', methods=['GET'])
@auth_token.login_required
def get_feed(id):
    feed = Feed.query.get_or_404(id)
    return jsonify({'feed': feed.export_data(), 'comments': [comment.export_data() for comment in feed.comments]})


@api.route('/comments/<int:id>', methods=['GET'])
@auth_token.login_required
def get_feed_comments(id):
    feed = Feed.query.get_or_404(id)
    return jsonify([comment.export_data() for comment in feed.comments])

@api.route('/feed', methods=['POST'])
@json
@auth_token.login_required
def new_feed():
    app = create_app('production')
    feed = Feed()
    if not request.json:
        if request.files['image'] is not None:
            image = request.files['image']
            if image and allowed_file(image.filename):
                imagename = "{:%I%M%S%f%d%m%Y}".format(datetime.now()) + secure_filename(image.filename)
                image.save(os.path.join(app.config['FEED_UPLOAD_FOLDER'], imagename))
                feed.image = imagename
                feed.title = request.form['title']
                feed.body = request.form['body']
    else:
        feed.import_data(request.json)
    feed.author = g.user
    db.session.add(feed)
    db.session.commit()
    return {}, 201, {'Message': 'Feed Created Successfully'}


@api.route('/comment/<int:id>', methods=['POST'])
@auth_token.login_required
def new_feed_comment(id):
    feed = Feed.query.get_or_404(id)
    comment = Comment()
    comment.import_data(request.json)
    comment.feed = feed
    comment.author = g.user
    db.session.add(comment)
    db.session.commit()
    return jsonify({'comment': comment.export_data()})


@api.route('/feed/<int:id>', methods=['PUT'])
@json
@auth_token.login_required
def edit_feed(id):
    feed = Feed.query.get_or_404(id)
    image = request.files['image']
    if image and allowed_file(image.filename):
        imagename = "{:%I%M%S%f%d%m%Y}".format(datetime.now()) + secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], imagename))
        feed.image = imagename
    feed.title = request.form['title']
    feed.body = request.form['body']
    db.session.add(feed)
    db.session.commit()
    return {}

@api.route('/like/<int:id>')
@auth_token.login_required
def like(id):
    feed = Feed.query.get_or_404(id)
    for like in feed.likes:
        if g.user == like.liker:
            return 'You are not allowed to like again'
    vote = Like(feed=feed, liker=g.user)
    db.session.add(vote)
    db.session.commit()
    return 'Liked'
