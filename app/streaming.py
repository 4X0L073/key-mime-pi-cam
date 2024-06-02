# Klon von https://github.com/shillehbean/youtube-p2/blob/main/stream_usb_camera.py
from flask import Flask, Response
from picamera2 import Picamera2
import cv2

# Globale Variable, um den Status der Kamera zu verfolgen
camera_running = True
# Erstellen einer Flask-Anwendung
app = Flask(__name__)

# Initialisierung der Kamera mit Picamera2
camera = Picamera2()
# Konfiguration der Kamera für das Hauptbild mit Format XRGB8888 und Größe 640x480 Pixel
camera.configure(camera.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
# Starten der Kamera
camera.start()

# Funktion zum Generieren von Bildern im Echtzeit-Stream
def generate_frames():
    global camera_running
    # Solange die Kamera läuft
    while camera_running:
        # Erfasse ein Bild von der Kamera
        frame = camera.capture_array()
        # Kodiere das Bild in das JPEG-Format
        ret, buffer = cv2.imencode('.jpg', frame)
        # Konvertiere das Bild in Bytes
        frame = buffer.tobytes()
        # Wenn die Kodierung erfolgreich ist
        if ret:
            # Erzeuge ein Response-Objekt mit dem Bild
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            # Gib eine Fehlermeldung aus, falls die Kodierung fehlschlägt
            print("Fehler beim Kodieren des Bildes")

# Definiere die Route für die Videoübertragung
@app.route('/')
def video_feed():
    # Rückgabe eines Responses mit dem generierten Frame-Stream und MIME-Typ für einen gemischten Ersetzungsansatz    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    '''
    mimetype steht kurz für Multipurpose Internet Mail Extensions Type
    Das spezielle MimeType multipart/x-mixed-replace wird oft für Live-Streams verwendet, 
    da es dem Client ermöglicht, dynamische Inhalte zu aktualisieren, 
    indem alte Inhalte durch neue ersetzt werden, ohne die gesamte Seite neu laden zu müssen.
    '''

# Definiere die Route zum Starten der Kamera
@app.route('/start_camera')
def start_camera():
    global camera_running
    # Setze den Status der Kamera auf aktiv
    camera_running = True
    # Gebe eine Bestätigungsmeldung zurück
    return "Kamera gestartet"

# Definiere die Route zum Stoppen der Kamera
@app.route('/stop_camera')
def stop_camera():
    global camera_running
    # Setze den Status der Kamera auf inaktiv
    camera_running = False
    # Gebe eine Bestätigungsmeldung zurück
    return "Kamera gestoppt"

# Starten der Flask-Anwendung ohne Debugging, auf allen Netzwerkschnittstellen lauschen und Port 8001 verwenden
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8001)
    
'''
Dieser Code erstellt eine einfache Webanwendung, die Bilder von einer USB-Kamera in Echtzeit über einen HTTP-Stream liefert.
Die Kamera wird konfiguriert, um Bilder im Format XRGB8888 mit einer Auflösung von 640x480 Pixeln aufzunehmen.
Diese Bilder werden dann in einem kontinuierlichen Loop erfasst, kodiert und als Byte-String ausgegeben, 
der als Teil eines multipart/mixed-replace HTTP-Antwortkörpers verwendet wird. Der Client, der diesen Stream empfängt, 
kann die einzelnen Bilder basierend auf dem Boundary-Namen frame korrekt parsen und anzeigen.
'''
