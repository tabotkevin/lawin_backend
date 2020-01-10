from datetime import datetime
from dateutil import parser as datetime_parser
from dateutil.tz import tzutc
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import JSONWebSignatureSerializer as Serializer
from flask import url_for, current_app, g
from . import db, create_app
from .exceptions import ValidationError
from .utils import split_url
import flask_whooshalchemy as whooshalchemy
from whoosh.analysis import StemmingAnalyzer




class Permission:
    COMMENT = 0x01
    WRITE_ARTICLES = 0x02
    MODERATE_COMMENTS = 0x04
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.COMMENT, True),
            'Lawyer': (Permission.COMMENT | Permission.WRITE_ARTICLES | Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name



class User(db.Model):
    __tablename__ = 'users'
    __searchable__ = ['name', 'company', 'email', 'position', 'location', 'about'] 
    __analyzer__ = StemmingAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=True)
    name = db.Column(db.String(64))
    image = db.Column(db.String(1024), default='default.jpg', index=True)
    company = db.Column(db.String(1024))
    position = db.Column(db.String(1024))
    location = db.Column(db.String(64))
    about = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    feeds = db.relationship('Feed', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    likes = db.relationship('Like', backref='liker', lazy='dynamic')
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    received_messages = db.relationship('Message', backref='receiver', lazy='dynamic', foreign_keys='Message.receiver_id')
    messages_replied = db.relationship('Reply', backref='author', lazy='dynamic')


    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])
    

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def get_url(self):
        return url_for('api.get_user', id=self.id, _external=True)

    def get_image_url(self):
        if self.image is None:
            return 'false'
        return url_for('static', filename='images/users/'+self.image, _external=True)

    def export_data(self):
        return {
            'id': self.id,
            'self_url': self.get_url(),
            'role_id': self.role_id,
            'email': self.email,
            'name': self.name,
            'image': self.get_image_url(),
            'location': self.location,
            'company': self.company,
            'position': self.position,
            'about': self.about,
            'feeds_url': url_for('api.get_feeds', id=self.id, _external=True),
            'comments_url': url_for('api.get_feed_comments', id=self.id, _external=True),
            'sent_messages_url': url_for('api.get_outbox', id=self.id, _external=True),
            'received_messages_url': url_for('api.get_inbox', id=self.id, _external=True)
        }

    def import_data(self, data):
        try:
            self.email = data.get('email')
            self.company = data.get('company')
            self.position = data.get('position')
            self.name = data.get('name')
            self.location = data.get('location')
            self.about = data.get('about')
            if data.get('password') is not None:
                self.set_password(data.get('password'))
        except KeyError as e:
            raise ValidationError('Invalid customer: missing ' + e.args[0])
        return self

    def __repr__(self):
        return '<User %r>' % self.username


class Feed(db.Model):
    __tablename__ = 'feeds'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1024), index=True)
    body = db.Column(db.Text)
    image = db.Column(db.String(1024), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    likes = db.relationship('Like', backref='feed', lazy='dynamic')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='feed', lazy='dynamic')

    
    def get_url(self):
        return url_for('api.get_feed', id=self.id, _external=True)

    def get_image_url(self):
        if self.image is None:
            return 'false'
        else:
            return url_for('static', filename='images/feeds/'+self.image, _external=True)

    def get_author_image(self):
        if self.author.image is None:
            return 'false'
        else:
            return url_for('static', filename='images/users/'+self.author.image, _external=True)

    def export_data(self):
        return {
            'id': self.id,
            'likes': self.likes.count(),
            'comments': self.comments.count(),
            'self_url': self.get_url(),
            'author_id': self.author.id,
            'author_name': self.author.name,
            'author_image': self.get_author_image(),
            'author_company': self.author.company,
            'author_position': self.author.position,
            'title': self.title,
            'body': self.body,
            'created_on': self.timestamp,
            'image': self.get_image_url(),
            'comments_url': url_for('api.get_feed_comments', id=self.id, _external=True)
        }

    def import_data(self, data):
        try:
            self.title = data['title']
            self.body = data['body']
        except KeyError as e:
            raise ValidationError('Invalid customer: missing ' + e.args[0])
        return self
    


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id'))


    def get_url(self):
        return url_for('api.get_comment', id=self.id, _external=True)


    def get_author_image(self):
        if self.author.image is None:
            return 'false'
        else:
            return url_for('static', filename='images/users/'+self.author.image, _external=True)


    def export_data(self):
        return {
            'body': self.body,
            'author_image': self.get_author_image(),
            'author_name': self.author.name,
            'author_id': self.author.id,
            'created_on': self.timestamp
        }


    def import_data(self, data):
        try:
            self.body = data['body']
        except KeyError as e:
            raise ValidationError('Invalid customer: missing ' + e.args[0])
        return self


class Like(db.Model):
    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id'))
    created_on = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(u'id', db.Integer(), primary_key=True, nullable=False)
    title = db.Column(db.String(256), index=True)
    body = db.Column(db.Text(), index=True)
    read = db.Column(db.Boolean, default=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    replies = db.relationship('Reply', backref='message', lazy='dynamic')

    def get_url(self):
        return url_for('api.get_message', id=self.id, _external=True)

    def get_author_image(self, id):
        user = User.query.get_or_404(id)
        if user.image is None:
            return 'false'
        return url_for('static', filename='images/users/'+user.image, _external=True)

    def isMe(self):
        if self.sender == g.user:
            return True
        return False

    def export_data(self):
        return {
            'id': self.id,
            'isMe': self.isMe(),
            'title': self.title,
            'body': self.body,
            'created_on': self.created_on,
            'read': self.read,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'sender_image': self.get_author_image(self.sender_id),
            'receiver_image': self.get_author_image(self.receiver_id),
        }


    def import_data(self, data):
        try:
            self.title = data['title']
            self.body = data['body']
            self.receiver_id = data['receiver_id']
        except KeyError as e:
            raise ValidationError('Parameters missing ' + e.args[0])
        return self


class Reply(db.Model):
    __tablename__ = 'replies'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))


    def get_url(self):
        return url_for('api.get_reply', id=self.id, _external=True)

    def get_author_image(self, id):
        user = User.query.get_or_404(id)
        if user.image is None:
            return 'false'
        return url_for('static', filename='images/users/'+user.image, _external=True)

    def isMe(self):
        if self.author == g.user:
            return True
        return False

    def export_data(self):
        return {
            'id': self.id,
            'isMe': self.isMe(),
            'body': self.body,
            'timestamp': self.timestamp,
            'author_id': self.author_id,
            'message_id': self.message_id,
            'sender_image': self.get_author_image(self.author_id),
        }


    def import_data(self, data):
        try:
            self.body = data['body']
        except KeyError as e:
            raise ValidationError('Invalid customer: missing ' + e.args[0])
        return self

app = create_app('production')
whooshalchemy.search_index(app, User)
