import logging
import os

from flask import Flask, session, request
from flask_socketio import SocketIO, emit, join_room

import config
from microflack_common import requests

logging.basicConfig(level=os.environ.get('LOG_LEVEL', logging.WARNING))

app = Flask(__name__)
config_name = os.environ.get('FLASK_CONFIG', 'dev')
app.config.from_object(getattr(config, config_name.title() + 'Config'))

message_queue = 'redis://' + os.environ['REDIS'] if 'REDIS' in os.environ \
    else None

# adding message_queue=message_queue, logger=True, engineio_logger=True
# this is very important: to have no https socketio problems!!!!
# see here: https://github.com/miguelgrinberg/microflack_admin/issues/6
# see here: https://stackoverflow.com/questions/63113478/flask-socketio-issues-with-https-http-wss-unable-to-connect-in-heroku

test_socketio = os.environ['HTTPS_SERVERNAME'] if 'HTTPS_SERVERNAME' in os.environ \
    else None
if test_socketio is not None and "NOT" in str(test_socketio):
    socketio = SocketIO(app, message_queue=message_queue)
else:
    cors_allowed = ['http://'+str(os.environ["HTTPS_SERVERNAME"]), 'https://'+str(os.environ["HTTPS_SERVERNAME"])]
    print("HTTPS IS USED: ")
    print(cors_allowed)
    socketio = SocketIO(app, message_queue=message_queue, cors_allowed_origins=cors_allowed)

@socketio.on('on_join_room')# , namespace='/chat'
def on_join_room(roomid, id, token):
    if not isinstance(roomid, int):
        roomid=0
    session['roomid'] = int(roomid)
    join_room(int(roomid))
    data = {'sid': str(request.sid)}
    if int(id)>0:
        rv = requests.put('/api/users/'+str(id), json=data,
                          headers={'Authorization': 'Bearer ' + token},
                          raise_for_status=True)

@socketio.on('ping_user')
def on_ping_user(token):
    """Clients must send this event periodically to keep the user online."""
    rv = requests.put('/api/users/me',
                      headers={'Authorization': 'Bearer ' + token},
                      raise_for_status=False)
    if rv.status_code != 401:
        session['token'] = token  # save token, disconnect() might need it
    else:
        emit('expired_token')


@socketio.on('post_message')
def on_post_message(data, token):
    """Clients send this event to when the user posts a message.
       All messages here are broadcasted to all room members
    """
    try:
        data['roomid'] = session['roomid']
    except:
        data['roomid'] = 0
    rv = requests.post('/api/messages', json=data,
                       headers={'Authorization': 'Bearer ' + token},
                       raise_for_status=False)
    if rv.status_code != 401:
        session['token'] = token  # save token, disconnect() might need it
    else:
        emit('expired_token')


@socketio.on('disconnect')
def on_disconnect():
    """A Socket.IO client has disconnected. If we know who the user is, then
    update our state accordingly.
    """
    if 'token' in session:
        requests.delete(
            '/api/users/me',
            headers={'Authorization': 'Bearer ' + session['token']},
            raise_for_status=False)


if __name__ == '__main__':
    socketio.run(app)
