from flask import request, jsonify, g, abort
from . import api
from .. import db
from ..models import Message, Reply
from ..decorators import json, paginate
from ..auth import auth_token

@api.route('/inbox', methods=['GET'])
@json
@paginate('messages')
@auth_token.login_required
def get_inbox():
    return Message.query.filter_by(receiver_id=g.user.id)


@api.route('/outbox', methods=['GET'])
@json
@paginate('messages')
@auth_token.login_required
def get_outbox():
    return Message.query.filter_by(sender_id=g.user.id)


@api.route('/total', methods=['GET'])
@auth_token.login_required
def get_total():
    outboxes = Message.query.filter_by(sender_id=g.user.id).count()
    inboxes = Message.query.filter_by(receiver_id=g.user.id).count()
    total = outboxes + inboxes
    return jsonify({'total': total})

@api.route('/get_replies/<int:id>', methods=['GET'])
@auth_token.login_required
def get_replies(id):
    message = Message.query.get_or_404(id)
    if not message.is_mine():
        abort(401)
    return jsonify([reply.export_data() for reply in message.replies])


@api.route('/message/<int:id>', methods=['GET'])
@auth_token.login_required
def get_message(id):
    message = Message.query.get_or_404(id)
    if not message.is_mine():
        abort(403)
    message.read = 1
    db.session.add(message)
    db.session.commit()
    return jsonify({'message': message.export_data(), 'replies': [reply.export_data() for reply in message.replies]})


@api.route('/reply/<int:id>', methods=['POST'])
@auth_token.login_required
def new_reply(id):
    message = Message.query.get_or_404(id)
    message.read = 0
    reply = Reply()
    reply.import_data(request.json)
    reply.message = message
    reply.author = g.user
    db.session.add(message)
    db.session.add(reply)
    db.session.commit()
    return jsonify({'reply': reply.export_data()})

@api.route('/message', methods=['POST'])
@json
@auth_token.login_required
def new_message():
    message = Message()
    message.import_data(request.json)
    message.sender_id = g.user.id
    db.session.add(message)
    db.session.commit()
    return {}, 201, {'Location': message.get_url()}



@api.route('/message/<int:id>', methods=['DELETE'])
@json
@auth_token.login_required
def delete_message(id):
    message = Message.query.get_or_404(id)
    if not message.is_mine():
        abort(403)
    db.session.delete(message)
    db.session.commit()
    return {}
