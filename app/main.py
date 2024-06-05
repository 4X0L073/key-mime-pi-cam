#!/usr/bin/env python

import json
import logging
import os

import flask
import flask_socketio

import hid
import js_to_hid

import threading


root_logger = logging.getLogger(__name__)
#handler = logging.StreamHandler()
handler = logging.FileHandler('app.log')
formatter = logging.Formatter(
    '%(asctime)s %(name)-15s %(levelname)-4s %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
#root_logger.addHandler(flask.logging.default_handler)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

my_app = flask.Flask(__name__, static_url_path='')
socketio = flask_socketio.SocketIO(my_app)

logger = logging.getLogger(__name__)
logger.info('Starting app')

host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', 8000))
debug = 'DEBUG' in os.environ
# Ort des HID-Datei, in dem die Tastatur-HID-Eingabe geschrieben wird.
hid_path = os.environ.get('HID_PATH', '/dev/hidg0')

def _parse_key_event(payload):
    return js_to_hid.JavaScriptKeyEvent(
        meta_modifier=payload.get('metaKey', False),
        alt_modifier=payload.get('altKey', False),
        shift_modifier=payload.get('shiftKey', False),
        ctrl_modifier=payload.get('ctrlKey', False),
        key=payload.get('key', ''),
        key_code=payload.get('keyCode', 0)
    )

# Behandlung von Tastatur-Ereignissen vom Client
@socketio.on('keystroke')
def socket_keystroke(message):
    key_event = _parse_key_event(message)
    hid_keycode = None
    success = False
    try:
        control_keys, hid_keycode = js_to_hid.convert(key_event)
    except js_to_hid.UnrecognizedKeyCodeError:
        logger.warning('Nicht erkannte Taste: %s (Tastencodierung=%d)', key_event.key,
                       key_event.key_code)
    if hid_keycode is None:
        logger.info('%s-Taste wird ignoriert (Tastencodierung=%d)', key_event.key,
                    key_event.key_code)
    else:
        hid.send(hid_path, control_keys, hid_keycode)
        success = True

    socketio.emit('keystroke-received', {'success': success})

# Event-Handler für die Verbindung und Trennung des Clients
@socketio.on('connect')
def test_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    logger.info('Client disconnected')

# Route für die Indexseite
@my_app.route('/', methods=['GET'])
def index_get():
    return flask.render_template('index.html')


# Endpunkt zum Starten der Tastatureingabeautomatisierung
@my_app.route('/automate', methods=['POST'])
def automate_post():
    data = flask.request.json
    commandsList = data.get('commandsList', [])
    delay = data.get('delay', 0.5)  # Standardverzögerung auf 0.5 Sekunden, falls nicht angegeben
    addTime = data.get('addTime', False)
    threading.Thread(target=js_to_hid.automate_key_input, args=(commandsList, delay, addTime)).start()
    return flask.jsonify({'status': 'success', 'message': 'Automatisierung gestartet'})
    #return {'status': 'success', 'message': 'Automatisierung gestartet'}


def make_list_from_json(path):
    data_list = []
    with open(path) as f:
        data = json.load(f)
        for element in data['keycodes_with_delay']:
            data_list.append((element['key'], element['delay']))
    return data_list


@my_app.route('/load_json', methods=['POST'])
def automate_post_with_individual_delay():
    mod_path =os.path.join(os.path.dirname(__file__), 'static', 'json', 'tizen_config.json')
    keycodes_list = make_list_from_json(mod_path)
    threading.Thread(target=js_to_hid.automate_key_input_with_individual_delay, args=(keycodes_list,)).start()
    return flask.jsonify({'status': 'success', 'message': 'Automatisierung gestartet'})

# Start der Flask-Anwendung
if __name__ == '__main__':
    socketio.run(my_app,
                 host=host,
                 port=port,
                 debug=debug,
                 use_reloader=True,
                 extra_files=[
                     './app/templates/index.html', './app/static/js/app.js',
                     './app/static/css/style.css'
                 ])
