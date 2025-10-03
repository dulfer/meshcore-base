"""MeshCore Web Application."""

import json
import os
import threading
import time
from flask import Flask
from datetime import datetime

from .database import db
from .database.models import Message, Contact
from .meshcore_service import MeshCoreService
from .routes import register_routes

def init_db(app):
    """Initialize the database."""
    with app.app_context():
        db.create_all()

def process_messages(app):
    """Background task to process received messages."""
    while True:
        with app.app_context():
            message = app.mesh_service.get_message()
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

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure Flask application
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meshcore.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['MESHCORE_PORT'] = os.environ.get('MESHCORE_PORT', 'COM3')
    app.config['MESHCORE_BAUDRATE'] = int(os.environ.get('MESHCORE_BAUDRATE', '115200'))

    # Initialize database
    db.init_app(app)

    # Initialize MeshCore service
    mesh_service = MeshCoreService(
        port=app.config['MESHCORE_PORT'],
        baudrate=app.config['MESHCORE_BAUDRATE']
    )
    app.mesh_service = mesh_service

    with app.app_context():
        # Initialize the database
        init_db(app)
        
        # Start MeshCore service
        mesh_service.start()
        
        # Start message processing thread
        processing_thread = threading.Thread(target=process_messages, args=(app,))
        processing_thread.daemon = True
        processing_thread.start()

    @app.teardown_appcontext
    def teardown_appcontext(exception=None):
        """Cleanup when application context ends."""
        mesh_service.stop()

    # Register routes
    register_routes(app)

    return app

# Create the application instance
app = create_app()

# Ensure database and services are initialized
with app.app_context():
    init_db(app)
    if not app.mesh_service.is_connected():
        app.mesh_service.start()

    # Start message processing if not already running
    if not any(t.name == "MeshCore-MessageProcessor" for t in threading.enumerate()):
        processing_thread = threading.Thread(
            target=process_messages,
            name="MeshCore-MessageProcessor",
            args=(app,)
        )
        processing_thread.daemon = True
        processing_thread.start()