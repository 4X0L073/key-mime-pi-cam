#!/usr/bin/env python

import json
import logging
import os
import threading

import flask
import flask_socketio

import hid
import js_to_hid


root_logger = logging.getLogger(__name__)
handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), 'app.log'))
#handler = logging.StreamHandler()
#handler = logging.FileHandler('app.log')
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

automation_thread = None
stop_event = threading.Event()


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
    #js_to_hid.automate_key_input(commandsList, delay, addTime)
    global automation_thread, stop_event
    if automation_thread and automation_thread.is_alive():
        return flask.jsonify({'status': 'error', 'message': 'Automatisierung läuft bereits'})
    elif automation_thread and not automation_thread.is_alive():
        del automation_thread
    stop_event.clear()    
    automation_thread = threading.Thread(target=js_to_hid.automate_key_input, args=(commandsList, delay, addTime, stop_event))
    automation_thread.start()
    return flask.jsonify({'status': 'success', 'message': 'Automatisierung gestartet'})


# Take version number from the select dropdown in index.html
def make_list_from_json_versioned(path, version):
    data_list = []
    local_version = ""
    logger.info(f'version: {version}')
    try:
        if not version == None:
            if version == "universal_template":
                local_version = str(version)
            else:
                local_version = f"tizen_{int(version)}_config"
            with open(path) as f:
                data = json.load(f)
                for element in data[local_version]:
                    data_list.append((element['key'], element['delay']))
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
    return data_list


@my_app.route('/load_json', methods=['GET'])
def load_automation_file():
    selectedVersion = flask.request.args.get('tizen_ver', type=str)  # Ensure that selectedVersion is always a string, even if it's None
    logger.info(f'selected Version %s', selectedVersion)
    mod_path = os.path.join(os.path.dirname(__file__), 'static', 'json', 'tizen_config.json')
    logger.info(mod_path)
    keycodes_list = make_list_from_json_versioned(mod_path, str(selectedVersion))
    logger.info(f'keycodes_list: %s selected version: %s', keycodes_list, str(selectedVersion))
    global automation_thread, stop_event
    if automation_thread and automation_thread.is_alive():
        return flask.jsonify({'status': 'error', 'message': 'Automatisierung läuft bereits'})
    elif automation_thread and not automation_thread.is_alive():
        del automation_thread
    stop_event.clear()
    automation_thread = threading.Thread(target=js_to_hid.automate_key_input_with_individual_delay, args=(keycodes_list, stop_event))
    automation_thread.start()
    return flask.jsonify({'status': 'success', 'message': 'Automatisierung gestartet'})


@my_app.route('/stop_automation', methods=['GET'])
def stop_automation():
    global automation_thread, stop_event
    if automation_thread and automation_thread.is_alive():
        stop_event.set()
        automation_thread.join()
        automation_thread = None
        return flask.jsonify({'status': 'success', 'message': 'Automatisierung gestoppt'})
    else:
        return flask.jsonify({'status': 'error', 'message': 'Automatisierung wurde nicht gestartet'})

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

