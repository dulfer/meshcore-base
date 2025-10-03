"""Route handlers for the MeshCore web client."""

import json
import time
from flask import jsonify, request, render_template
from .database import db
from .database.models import Message, Contact
from datetime import datetime

def register_routes(app):
    @app.route('/')
    def index():
        """Render the main page."""
        page = request.args.get('page', 1, type=int)
        messages = Message.query.order_by(Message.timestamp.desc()).paginate(
            page=page, per_page=25, error_out=False
        )
        contacts = Contact.query.filter_by(is_active=True).all()
        return render_template('index.html', messages=messages, contacts=contacts)

    @app.route('/api/messages', methods=['GET'])
    def get_messages():
        """Get paginated messages."""
        page = request.args.get('page', 1, type=int)
        messages = Message.query.order_by(Message.timestamp.desc()).paginate(
            page=page, per_page=25, error_out=False
        )
        return jsonify({
            'messages': [msg.to_dict() for msg in messages.items],
            'has_next': messages.has_next,
            'has_prev': messages.has_prev,
            'total': messages.total
        })

    @app.route('/api/messages', methods=['POST'])
    def send_message():
        """Send a new message."""
        data = request.get_json()
        
        try:
            content = data['content']
            receiver_node = data.get('receiver_node')
            is_public = receiver_node is None

            # Send message through MeshCore service
            result = app.mesh_service.send_message(content, receiver_node if not is_public else None)
            
            # Store message in database
            message = Message(
                content=content,
                sender_node=result['sender'],
                receiver_node=result['receiver'],
                message_path=json.dumps(result['path']),
                is_public=is_public,
                timestamp=datetime.fromisoformat(result['timestamp'])
            )
            db.session.add(message)
            db.session.commit()

            return jsonify(message.to_dict()), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/contacts', methods=['GET'])
    def get_contacts():
        """Get all active contacts."""
        contacts = Contact.query.filter_by(is_active=True).all()
        return jsonify([contact.to_dict() for contact in contacts])
        
    @app.route('/api/status', methods=['GET'])
    def get_status():
        """Get the current status of the MeshCore service."""
        status = app.mesh_service.get_status()
        return jsonify({
            'service': status,
            'database': {
                'message_count': Message.query.count(),
                'contact_count': Contact.query.count(),
                'latest_message': Message.query.order_by(Message.timestamp.desc())
                    .first().timestamp.isoformat() if Message.query.first() else None
            }
        })

    # Server-Sent Events route for real-time updates
    @app.route('/api/messages/stream')
    def stream_messages():
        """Stream messages in real-time using Server-Sent Events."""
        def generate():
            def get_latest_message():
                with app.app_context():
                    return Message.query.order_by(Message.timestamp.desc()).first()
            
            last_message_id = None
            if last_msg := get_latest_message():
                last_message_id = last_msg.id
                
            while True:
                # Check for new messages in database
                current_msg = get_latest_message()
                if current_msg and (last_message_id is None or current_msg.id > last_message_id):
                    last_message_id = current_msg.id
                    yield f"data: {json.dumps(current_msg.to_dict())}\n\n"
                time.sleep(0.5)  # Short sleep to prevent excessive database queries

        return app.response_class(
            generate(),
            mimetype='text/event-stream'
        )