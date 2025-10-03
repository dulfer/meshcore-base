"""Database models for the MeshCore web client."""

from datetime import datetime
from ..database import db

class Message(db.Model):
    """Model for storing MeshCore messages."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_node = db.Column(db.String(64), nullable=False)
    receiver_node = db.Column(db.String(64))  # Null for public messages
    message_path = db.Column(db.Text)  # Stored as JSON string
    is_public = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert message to dictionary for API responses."""
        return {
            'id': self.id,
            'content': self.content,
            'sender_node': self.sender_node,
            'receiver_node': self.receiver_node,
            'message_path': self.message_path,
            'is_public': self.is_public,
            'timestamp': self.timestamp.isoformat()
        }

class Contact(db.Model):
    """Model for storing known MeshCore nodes/contacts."""
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        """Convert contact to dictionary for API responses."""
        return {
            'id': self.id,
            'node_id': self.node_id,
            'name': self.name,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_active': self.is_active
        }