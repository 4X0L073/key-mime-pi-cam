import logging
import os
import flask
import flask_socketio
import hid
import js_to_hid
import threading
import picamera2
import io
import base64
import uvicorn

# Initialize Flask app and Socket.IO
app = flask.Flask(__name__, static_url_path='')
socketio = flask_socketio.SocketIO(app)

# Logging setup
root_logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-15s %(levelname)-4s %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
root_logger.addHandler(handler)
root_logger.setLevel(os.environ.get('LOG_LEVEL', 'WARN'))

logger = logging.getLogger(__name__)
logger.info('Starting app')

# Configuration
host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', 8000))
debug = 'DEBUG' in os.environ
hid_path = os.environ.get('HID_PATH', '/dev/hidg0')

# Import streaming functionality from streaming.py
from streaming import picam2, StreamingOutput

def _parse_key_event(payload):
    return js_to_hid.JavaScriptKeyEvent(meta_modifier=payload['metaKey'],
                                        alt_modifier=payload['altKey'],
                                        shift_modifier=payload['shiftKey'],
                                        ctrl_modifier=payload['ctrlKey'],
                                        key=payload['key'],
                                        key_code=payload['keyCode'])

@socketio.on('keystroke')
def socket_keystroke(message):
    key_event = _parse_key_event(message)
    hid_keycode = None
    success = False
    try:
        control_keys, hid_keycode = js_to_hid.convert(key_event)
    except js_to_hid.UnrecognizedKeyCodeError:
        logger.warning('Unrecognized key: %s (keycode=%d)', key_event.key,
                       key_event.key_code)
    if hid_keycode is None:
        logger.info('Ignoring %s key (keycode=%d)', key_event.key,
                    key_event.key_code)
    else:
        hid.send(hid_path, control_keys, hid_keycode)
        success = True

    socketio.emit('keystroke-received', {'success': success})

# Event handler for connecting clients
@socketio.on('connect')
def test_connect():
    logger.info('Client connected')
    # Start capturing video
    picam2.start_recording(StreamingOutput())

# Event handler for disconnecting clients
@socketio.on('disconnect')
def test_disconnect():
    logger.info('Client disconnected')
    # Stop capturing video
    picam2.stop_recording()

# Emitting video frames to clients
@socketio.on('stream')
def stream(data):
    if data['command'] == 'start':
        # Start sending frames
        while True:
            with StreamingOutput.lock:
                frame = StreamingOutput.frame
            # Encode the frame to base64 and emit it
            encoded_frame = base64.b64encode(frame).decode('utf-8')
            socketio.emit('frame', {'data': encoded_frame})
            # Check if the command is 'stop'
            if data['command'] == 'stop':
                # Stop sending frames
                break

# Route for index
@app.route('/', methods=['GET'])
def index_get():
    return flask.render_template('index.html')

def main():
    # Run the ASGI server
    uvicorn.run(app, host='localhost', port=5001)

if __name__ == '__main__':
    main()

# #!/usr/bin/env python

# import logging
# import os

# import flask
# import flask_socketio

# import hid
# import js_to_hid

# import threading
# import picamera2
# import io
# import logging
# from threading import Thread
# import uvicorn


# root_logger = logging.getLogger()
# handler = logging.StreamHandler()
# formatter = logging.Formatter(
#     '%(asctime)s %(name)-15s %(levelname)-4s %(message)s', '%Y-%m-%d %H:%M:%S')
# handler.setFormatter(formatter)
# root_logger.addHandler(flask.logging.default_handler)
# root_logger.setLevel(os.environ.get('LOG_LEVEL', 'WARN'))

# app = flask.Flask(__name__, static_url_path='')
# socketio = flask_socketio.SocketIO(app)

# logger = logging.getLogger(__name__)
# logger.info('Starting app')

# host = os.environ.get('HOST', '0.0.0.0')
# port = int(os.environ.get('PORT', 8000))
# debug = 'DEBUG' in os.environ
# # Location of HID file handle in which to write keyboard HID input.
# hid_path = os.environ.get('HID_PATH', '/dev/hidg0')

# # Run the ASGI server
# uvicorn.run(app, host='localhost', port=5001)

# def _parse_key_event(payload):
#     return js_to_hid.JavaScriptKeyEvent(meta_modifier=payload['metaKey'],
#                                         alt_modifier=payload['altKey'],
#                                         shift_modifier=payload['shiftKey'],
#                                         ctrl_modifier=payload['ctrlKey'],
#                                         key=payload['key'],
#                                         key_code=payload['keyCode'])


# @socketio.on('keystroke')
# def socket_keystroke(message):
#     key_event = _parse_key_event(message)
#     hid_keycode = None
#     success = False
#     try:
#         control_keys, hid_keycode = js_to_hid.convert(key_event)
#     except js_to_hid.UnrecognizedKeyCodeError:
#         logger.warning('Unrecognized key: %s (keycode=%d)', key_event.key,
#                        key_event.key_code)
#     if hid_keycode is None:
#         logger.info('Ignoring %s key (keycode=%d)', key_event.key,
#                     key_event.key_code)
#     else:
#         hid.send(hid_path, control_keys, hid_keycode)
#         success = True

#     socketio.emit('keystroke-received', {'success': success})


# @socketio.on('connect')
# def test_connect():
#     logger.info('Client connected')


# @socketio.on('disconnect')
# def test_disconnect():
#     logger.info('Client disconnected')


# @app.route('/', methods=['GET'])
# def index_get():
#     return flask.render_template('index.html')

# def start_video_streaming_server():
#     # Initialize Socket.IO server
#     sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
#     app = socketio.ASGIApp(sio)

#     # Configure the camera
#     picam2 = picamera2.Picamera2()
#     picam2.configure(picam2.create_video_configuration(main={"size": (640, 480), "format": "jpeg"}))

#     # Output class to hold the latest frame
#     class StreamingOutput(io.BufferedIOBase):
#         def __init__(self):
#             super().__init__()
#             self.frame = None

#         def write(self, buf):
#             with self.lock:
#                 self.frame = buf

# def run(app, socketio, host, port, debug):
#     socketio.run(app,
#                  host=host,
#                  port=port,
#                  debug=debug,
#                  use_reloader=True,
#                  extra_files=[
#                      './app/templates/index.html', './app/static/js/app.js',
#                      './app/static/css/style.css'
#                  ])

# def main():
#     video_streaming_thread = threading.Thread(target=start_video_streaming_server)
#     video_streaming_thread.daemon = True
#     video_streaming_thread.start()
#     run(app, socketio, host, port, debug)
    

# if __name__ == '__main__':
#     main()
