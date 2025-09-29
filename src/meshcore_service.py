import threading
import time
import json
import logging
from datetime import datetime
from queue import Queue
from typing import Optional
from meshcore import MeshCore

class MeshCoreService:
    """Service to handle MeshCore companion communications."""
    
    def __init__(self, port: str = '/dev/ttyUSB1', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.mesh = None
        self.running = False
        self.connected = False
        self._listener_thread = None
        self._message_queue = Queue()
        self._logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the MeshCore service."""
        if self.running:
            return
            
        try:
            self.mesh = MeshCore(port=self.port, baudrate=self.baudrate)
            self.mesh.connect()
            self.connected = True
            self._logger.info(f"Connected to MeshCore companion on {self.port}")
            
            # Start the listener thread
            self.running = True
            self._listener_thread = threading.Thread(target=self._listen_for_messages)
            self._listener_thread.daemon = True
            self._listener_thread.start()
            
        except Exception as e:
            self._logger.error(f"Failed to start MeshCore service: {str(e)}")
            self.connected = False
            raise
    
    def stop(self):
        """Stop the MeshCore service."""
        self.running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2.0)
        if self.mesh and self.connected:
            self.mesh.disconnect()
            self.connected = False
        self._logger.info("MeshCore service stopped")
    
    def _listen_for_messages(self):
        """Background thread to listen for incoming messages."""
        self._logger.info("Message listener started")
        while self.running:
            try:
                if not self.connected:
                    self._try_reconnect()
                    continue
                    
                # Check for new messages
                message = self.mesh.receive_message(timeout=1.0)
                if message:
                    self._logger.debug(f"Received message: {message}")
                    self._message_queue.put({
                        'content': message.get('content', ''),
                        'sender': message.get('sender', 'unknown'),
                        'receiver': message.get('receiver'),
                        'path': message.get('path', []),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
            except Exception as e:
                self._logger.error(f"Error in message listener: {str(e)}")
                self.connected = False
                time.sleep(5)  # Wait before retry
    
    def _try_reconnect(self):
        """Attempt to reconnect to the MeshCore companion."""
        try:
            if self.mesh:
                self.mesh.disconnect()
            self.mesh = MeshCore(port=self.port, baudrate=self.baudrate)
            self.mesh.connect()
            self.connected = True
            self._logger.info("Reconnected to MeshCore companion")
        except Exception as e:
            self._logger.error(f"Reconnection failed: {str(e)}")
            time.sleep(5)  # Wait before next attempt
    
    def get_message(self) -> Optional[dict]:
        """Get the next message from the queue if available."""
        try:
            return self._message_queue.get_nowait()
        except:
            return None
    
    def send_message(self, content: str, receiver: Optional[str] = None) -> dict:
        """Send a message through MeshCore companion."""
        if not self.connected:
            raise RuntimeError("Not connected to MeshCore companion")
            
        try:
            if receiver:
                # Send private message
                path = self.mesh.send_direct(receiver, content)
            else:
                # Send public message
                path = self.mesh.send_broadcast(content)
                
            return {
                'content': content,
                'sender': self.mesh.get_node_id(),
                'receiver': receiver,
                'path': path,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self._logger.error(f"Failed to send message: {str(e)}")
            raise
    
    def get_node_id(self) -> str:
        """Get the node ID of the MeshCore companion."""
        if not self.connected:
            raise RuntimeError("Not connected to MeshCore companion")
        return self.mesh.get_node_id()
    
    def is_connected(self) -> bool:
        """Check if the service is connected to the MeshCore companion."""
        return self.connected

    def get_status(self) -> dict:
        """Get the current status of the MeshCore service."""
        return {
            'running': self.running,
            'connected': self.connected,
            'port': self.port,
            'messages_queued': self._message_queue.qsize()
        }