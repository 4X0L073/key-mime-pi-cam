import base64
from main import picam2, StreamingOutput, app, socketio

# Event handler for connecting clients
@socketio.on('connect')
def connect():
    print('Client connected')
    # Start capturing video
    picam2.start_recording(StreamingOutput())

# Event handler for disconnecting clients
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')
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

if __name__ == '__main__':
    socketio.run(app, host='localhost', port=5000)


# import socketio
# import picamera2
# import io
# import base64
# import logging
# from threading import Thread

# # Initialize Socket.IO server
# sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
# app = socketio.ASGIApp(sio)

# # Configure the camera
# picam2 = picamera2.Picamera2()
# picam2.configure(picam2.create_video_configuration(main={"size": (640, 480), "format": "jpeg"}))

# # Output class to hold the latest frame
# class StreamingOutput(io.BufferedIOBase):
#     def __init__(self):
#         super().__init__()
#         self.frame = None

#     def write(self, buf):
#         with self.lock:
#             self.frame = buf

# # Event handler for connecting clients
# @sio.event
# async def connect(sid, environ):
#     print(f"Client connected: {sid}")
#     # Start capturing video
#     picam2.start_recording(StreamingOutput())

# # Event handler for disconnecting clients
# @sio.event
# async def disconnect(sid):
#     print(f"Client disconnected: {sid}")
#     # Stop capturing video
#     picam2.stop_recording()

# # Emitting video frames to clients
# @sio.event
# async def stream(sid, data):
#     if data['command'] == 'start':
#         # Start sending frames
#         while True:
#             with output.lock:
#                 frame = output.frame
#             # Encode the frame to base64 and emit it
#             encoded_frame = base64.b64encode(frame).decode('utf-8')
#             await sio.emit('frame', {'data': encoded_frame}, room=sid)
#             # Check if the command is 'stop'
#             if data['command'] == 'stop':
#                 # Stop sending frames
#                 break


# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run(app, host='localhost', port=5000)


# # # Mostly copied from https://picamera.readthedocs.io/en/release-1.13/recipes2.html
# # # Run this script, then point a web browser at http:<this-ip-address>:7123
# # # Note: needs simplejpeg to be installed (pip3 install simplejpeg).

# # import io
# # import socketserver
# # import logging
# # from http import server
# # from threading import Condition

# # from picamera2 import Picamera2
# # from picamera2.encoders import JpegEncoder
# # from picamera2.outputs import FileOutput

# # PAGE = """\
# # <html>
# # <head>
# # <title>picamera2 MJPEG streaming demo</title>
# # </head>
# # <body>
# # <h1>Picamera2 MJPEG Streaming Demo</h1>
# # <img src="stream.mjpg" width="640" height="480" />
# # </body>
# # </html>
# # """

# # class StreamingOutput(io.BufferedIOBase):
# #     def __init__(self):
# #         self.frame = None
# #         self.condition = Condition()

# #     def write(self, buf):
# #         with self.condition:
# #             self.frame = buf
# #             self.condition.notify_all()


# # class StreamingHandler(server.BaseHTTPRequestHandler):
# #     def do_GET(self):
# #         if self.path == '/':
# #             self.send_response(301)
# #             self.send_header('Location', '/index.html')
# #             self.end_headers()
# #         elif self.path == '/index.html':
# #             content = PAGE.encode('utf-8')
# #             self.send_response(200)
# #             self.send_header('Content-Type', 'text/html')
# #             self.send_header('Content-Length', len(content))
# #             self.end_headers()
# #             self.wfile.write(content)
# #         elif self.path == '/stream.mjpg':
# #             self.send_response(200)
# #             self.send_header('Age', 0)
# #             self.send_header('Cache-Control', 'no-cache, private')
# #             self.send_header('Pragma', 'no-cache')
# #             self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
# #             self.end_headers()
# #             try:
# #                 while True:
# #                     with output.condition:
# #                         output.condition.wait()
# #                         frame = output.frame
# #                     self.wfile.write(b'--FRAME\r\n')
# #                     self.send_header('Content-Type', 'image/jpeg')
# #                     self.send_header('Content-Length', len(frame))
# #                     self.end_headers()
# #                     self.wfile.write(frame)
# #                     self.wfile.write(b'\r\n')
# #             except Exception as e:
# #                 logging.warning(
# #                     'Removed streaming client %s: %s',
# #                     self.client_address, str(e))
# #         else:
# #             self.send_error(404)
# #             self.end_headers()


# # class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
# #     allow_reuse_address = True
# #     daemon_threads = True


# # picam2 = Picamera2()
# # picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
# # output = StreamingOutput()
# # picam2.start_recording(JpegEncoder(), FileOutput(output))

# # try:
# #     address = ('', 7123)
# #     server = StreamingServer(address, StreamingHandler)
# #     server.serve_forever()
# # finally:
# #     picam2.stop_recording()