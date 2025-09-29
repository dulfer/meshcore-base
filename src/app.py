import json
import os
import threading
import time
from flask import Flask, render_template, request, jsonify
from database.models import db, Message, Contact
from datetime import datetime
from meshcore_service import MeshCoreService

# Create Flask application
app = Flask(__name__)

# Configure Flask application
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meshcore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MESHCORE_PORT'] = os.environ.get('MESHCORE_PORT', '/dev/ttyUSB1')
app.config['MESHCORE_BAUDRATE'] = int(os.environ.get('MESHCORE_BAUDRATE', '115200'))

# Initialize database
db.init_app(app)

# Initialize MeshCore service
mesh_service = MeshCoreService(
    port=app.config['MESHCORE_PORT'],
    baudrate=app.config['MESHCORE_BAUDRATE']
)

def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()

def process_messages():
    """Background task to process received messages."""
    while True:
        with app.app_context():
            message = mesh_service.get_message()
            if message:
                # Store message in database
                db_message = Message(
                    content=message['content'],
                    sender_node=message['sender'],
                    receiver_node=message.get('receiver'),
                    message_path=json.dumps(message.get('path', [])),
                    is_public=message.get('receiver') is None,
                    timestamp=datetime.fromisoformat(message['timestamp'])
                )
                db.session.add(db_message)
                
                # Update contact's last seen timestamp
                contact = Contact.query.filter_by(node_id=message['sender']).first()
                if contact:
                    contact.last_seen = datetime.utcnow()
                else:
                    contact = Contact(
                        node_id=message['sender'],
                        last_seen=datetime.utcnow()
                    )
                    db.session.add(contact)
                
                db.session.commit()
        time.sleep(0.1)  # Short sleep to prevent CPU overuse

@app.before_first_request
def before_first_request():
    """Setup before first request."""
    init_db()
    mesh_service.start()
    
    # Start message processing thread
    processing_thread = threading.Thread(target=process_messages)
    processing_thread.daemon = True
    processing_thread.start()

@app.teardown_appcontext
def teardown_appcontext(exception=None):
    """Cleanup when application context ends."""
    mesh_service.stop()

# Make MeshCore service available to routes
app.mesh_service = mesh_service

# Import routes after app initialization to avoid circular imports
from routes import register_routes
register_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)