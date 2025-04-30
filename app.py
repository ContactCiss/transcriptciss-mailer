from flask import Flask, request
from flask_mail import Mail, Message
import os
import hmac
import hashlib

app = Flask(__name__)

# Configuratie voor Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# Webhook endpoint met HMAC-validatie
@app.route('/webhook', methods=['POST'])
def webhook():
    test_mode = os.environ.get("TEST_MODE", "False") == "True"

    # HMAC-validatie (tenzij in testmodus)
    if not test_mode:
        secret = os.environ.get("ELEVENLABS_WEBHOOK_SECRET")
        if not secret:
            return "Webhook secret ontbreekt. Stel ELEVENLABS_WEBHOOK_SECRET in als environment variable.", 500

        secret_bytes = secret.encode()
        signature = request.headers.get("x-elevenlabs-signature", "")
        computed_signature = hmac.new(secret_bytes, request.data, hashlib.sha256).hexdigest()

        # Debug output (alleen voor testen, kan later weg)
        print("Gekregen signature: ", signature)
        print("Berekenende signature:", computed_signature)

        if not hmac.compare_digest(signature, computed_signature):
            return "Signature mismatch", 403

    # Verwerk de payload
    payload = request.get_json()
    print("Ontvangen payload:", payload)

    if not payload:
        return "No JSON received", 400

    # Pak de echte transcript-data
    data = payload.get('data', {})
    transcript = data.get('transcript', [])

    if not transcript:
        return "No transcript found.", 400

    # Opbouw HTML-content
    html_content = "<h2>Nieuwe AI gesprek binnengekomen</h2>"
    html_content += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
    html_content += "<tr><th>Rol</th><th>Tijd</th><th>Bericht</th></tr>"

    for segment in transcript:
        role = segment.get('role', 'onbekend')
        message = segment.get('message', '')
        time_secs = segment.get('time_in_call_secs', 0)

        minutes = int(time_secs) // 60
        seconds = int(time_secs) % 60
        timestamp = f"{minutes:02}:{seconds:02}"

        html_content += f"<tr><td>{role.capitalize()}</td><td>{timestamp}</td><td>{message}</td></tr>"

    html_content += "</table>"

    # Verstuur e-mail
    sender = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    recipient = os.environ.get('MAIL_RECIPIENT')

    msg = Message(subject='Nieuwe AI gesprek binnengekomen',
                  sender=sender,
                  recipients=[recipient])

    msg.html = html_content

    try:
        mail.send(msg)
        return "Transcriptie ontvangen en e-mail verzonden.", 200
    except Exception as e:
        print("Error sending email:", e)
        return f"Fout bij verzenden van e-mail: {str(e)}", 500

# Aliassen
@app.route('/transcript', methods=['POST'])
def transcript():
    return webhook()

@app.route('/elevenlabs/transcriptie', methods=['POST'])
def elevenlabs_transcriptie():
    return webhook()

@app.route('/', methods=['GET'])
def health():
    return "Server is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

