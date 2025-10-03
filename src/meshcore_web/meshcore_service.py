"""MeshCore service for handling companion communications."""

import threading
import time
import json
import logging
import asyncio
from datetime import datetime
from queue import Queue
from typing import Optional
from meshcore import MeshCore
from meshcore.events import EventType

class MeshCoreService:
    """Service to handle MeshCore companion communications."""
    
    def __init__(self, port: str = 'COM3', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.mesh = None
        self.running = False
        self.connected = False
        self._listener_thread = None
        self._message_queue = Queue()
        self._logger = logging.getLogger(__name__)
        self._event_loop = None
        self._subscriptions = []  # Store subscriptions for cleanup
        
    def start(self):
        """Start the MeshCore service."""
        if self.running:
            return
            
        # Create a new event loop for the background thread
        self._event_loop = asyncio.new_event_loop()
        
        # Start the event loop in a background thread first
        self._listener_thread = threading.Thread(target=self._run_event_loop)
        self._listener_thread.daemon = True
        self._listener_thread.start()
        
        try:
            # Use run_coroutine_threadsafe for initialization
            future = asyncio.run_coroutine_threadsafe(
                self._initialize(),
                self._event_loop
            )
            future.result(timeout=30.0)  # Wait for initialization with increased timeout
            self.running = True
            
        except Exception as e:
            self._logger.error(f"Failed to start MeshCore service: {str(e)}")
            self.connected = False
            self.stop()  # Clean up on error
            raise
            
    async def _error_handler(self, event):
        """Handle error events."""
        error_code = event.attributes.get('error_code')
        error_map = {
            1: "Invalid command",
            2: "Invalid parameter",
            3: "Not ready",
            4: "Timeout",
            5: "No route to destination",
            6: "Buffer full",
            7: "Invalid state",
            8: "Internal error"
        }
        error_msg = error_map.get(error_code, f"Unknown error {error_code}")
        self._logger.error(f"MeshCore error: {error_msg}")
    
    async def _initialize(self):
        """Initialize the MeshCore service."""
        try:
            # Step 1: Try to create and connect MeshCore instance with retries
            self._logger.info("Creating MeshCore instance...")
            
            retry_count = 0
            max_retries = 3
            last_error = None
            
            while retry_count < max_retries:
                try:
                    self.mesh = await MeshCore.create_serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        auto_reconnect=True,
                        debug=True,  # Enable debug mode to see what's happening
                        cx_dly=1.0,  # Increase delay between operations
                        default_timeout=10.0  # Keep individual operation timeouts shorter
                    )
                    self._logger.info("MeshCore instance created successfully")
                    break
                except Exception as e:
                    last_error = e
                    self._logger.warning(f"Creation attempt {retry_count + 1} failed: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(2.0)
            
            if retry_count >= max_retries:
                raise RuntimeError(f"Failed to create device connection after retries: {last_error}")
            
            # Step 2: Set up error handling
            self._error_subscription = self.mesh.subscribe(EventType.ERROR, self._error_handler)
            self._logger.info("MeshCore instance created")
            
            # Step 3: Wait for device to stabilize
            self._logger.info("Waiting for device to stabilize...")
            await asyncio.sleep(2.0)
            
            # Step 4: Initialize device with retries
            self._logger.info("Attempting to initialize device...")
            
            retry_count = 0
            max_retries = 3
            device_ready = False
            
            while retry_count < max_retries and not device_ready:
                try:
                    self._logger.info(f"Initialization attempt {retry_count + 1}...")
                    
                    # First check if the device reports itself as ready
                    error_event = await self.mesh.wait_for_event(
                        EventType.ERROR,
                        timeout=1.0
                    )
                    if error_event:
                        error_code = error_event.attributes.get('error_code')
                        if error_code == 3:  # Not ready
                            self._logger.info("Device not ready, waiting 5 seconds...")
                            await asyncio.sleep(5.0)  # Wait longer when not ready
                            continue
                        else:
                            self._logger.warning(f"Device error {error_code}")
                            continue

                    # Try to get device info after checking readiness
                    try:
                        info_event = await self.mesh.wait_for_event(
                            EventType.SELF_INFO,
                            timeout=5.0
                        )
                        if info_event:
                            info = info_event.attributes
                            self._logger.info(f"Got device info: {info}")
                            device_ready = True
                            break
                        else:
                            self._logger.info("No device info received, waiting...")
                            
                    except asyncio.TimeoutError:
                        self._logger.warning("Timeout waiting for device info event")
                    except Exception as e:
                        self._logger.warning(f"Error getting device info: {e}")
                    
                    # Short pause between attempts
                    await asyncio.sleep(2.0)
                        
                except Exception as e:
                    self._logger.warning(f"Initialization attempt {retry_count + 1} failed: {str(e)}")
                
                # Wait before retrying
                retry_count += 1
                if retry_count < max_retries:
                    self._logger.info("Retrying after delay...")
                    await asyncio.sleep(2.0)
                    
            if not device_ready:
                raise RuntimeError("Failed to initialize device after retries")
            
            # Step 5: Configure message handling
            self.connected = True
            self._logger.info(f"Connected to MeshCore companion on {self.port}")
            
            self._logger.info("Setting up message handling...")
            await self._setup_message_handling()
            self._logger.info("Message handling configured")
            
        except Exception as e:
            self._logger.error(f"Initialization error: {str(e)}")
            raise
            
    async def _setup_message_handling(self):
        """Set up async message handling."""
        await self.mesh.start_auto_message_fetching()
        # Subscribe to both direct and channel messages - subscribe() is not async
        self._subscriptions.extend([
            self.mesh.subscribe(EventType.CONTACT_MSG_RECV, self._handle_message),
            self.mesh.subscribe(EventType.CHANNEL_MSG_RECV, self._handle_message)
        ])
    
    def stop(self):
        """Stop the MeshCore service."""
        if not self.running:
            return
        
        self.running = False
        if self._event_loop and self.mesh:
            try:
                # Run cleanup in the event loop
                asyncio.run_coroutine_threadsafe(
                    self._cleanup(), 
                    self._event_loop
                ).result(timeout=5.0)
            except Exception as e:
                self._logger.error(f"Error during cleanup: {str(e)}")
        
        if self._listener_thread:
            self._listener_thread.join(timeout=2.0)
            
        if self._event_loop:
            self._event_loop.stop()
            
        self._logger.info("MeshCore service stopped")
        
    async def _cleanup(self):
        """Clean up MeshCore resources."""
        if self.mesh:
            try:
                # Clean up subscriptions
                for subscription in self._subscriptions:
                    self.mesh.unsubscribe(subscription)
                self._subscriptions.clear()
                
                await self.mesh.stop_auto_message_fetching()
                await self.mesh.disconnect()
            except Exception as e:
                self._logger.error(f"Error during cleanup: {str(e)}")
            finally:
                self.connected = False
    
    def _run_event_loop(self):
        """Run the event loop in a background thread."""
        self._logger.info("Event loop started")
        try:
            self._event_loop.run_forever()
        except Exception as e:
            self._logger.error(f"Event loop error: {str(e)}")
        finally:
            self._event_loop.close()
    
    async def _handle_message(self, event):
        """Handle received messages."""
        try:
            attrs = event.attributes
            self._logger.debug(f"Received message event: {event.type} with attributes: {attrs}")
            
            if event.type == EventType.CONTACT_MSG_RECV:
                # Direct message
                message = {
                    'content': attrs.get('content', ''),
                    'sender': attrs.get('from_id', 'unknown'),
                    'receiver': attrs.get('to_id'),
                    'path': attrs.get('path', []),
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:  # CHANNEL_MSG_RECV
                # Broadcast/channel message
                message = {
                    'content': attrs.get('content', ''),
                    'sender': attrs.get('from_id', 'unknown'),
                    'receiver': None,  # Broadcast has no specific receiver
                    'path': attrs.get('path', []),
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            self._message_queue.put(message)
            
        except Exception as e:
            self._logger.error(f"Error handling message: {str(e)}")
    
    def _try_reconnect(self):
        """Attempt to reconnect to the MeshCore companion."""
        try:
            if self.mesh:
                self.mesh.disconnect()
            self.mesh = MeshCore(self.port, self.baudrate)
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
            # Create a future to get the result from the async operation
            future = asyncio.run_coroutine_threadsafe(
                self._send_message_async(content, receiver),
                self._event_loop
            )
            return future.result(timeout=10.0)
            
        except Exception as e:
            self._logger.error(f"Failed to send message: {str(e)}")
            raise
            
    async def _send_message_async(self, content: str, receiver: Optional[str] = None) -> dict:
        """Send a message asynchronously."""
        # Get node info through event
        info_event = await self.mesh.wait_for_event(EventType.SELF_INFO, timeout=5.0)
        if not info_event:
            raise RuntimeError("Failed to get device info")
        self_info = info_event.attributes
        
        if receiver:
            # Try to find the contact by name first
            contact = await self.mesh.get_contact_by_name(receiver)
            if not contact:
                # Try by key prefix if name not found
                contact = await self.mesh.get_contact_by_key_prefix(receiver)
            if not contact:
                raise ValueError(f"Contact not found: {receiver}")
                
            # Send direct message
            await self.mesh.send_direct(contact['public_key'], content)
        else:
            # Send broadcast
            await self.mesh.send_broadcast(content)
        
        return {
            'content': content,
            'sender': self_info.get('node_id', 'unknown'),
            'receiver': receiver,
            'path': [],  # Path will be updated by message events
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_node_id(self) -> str:
        """Get the node ID of the MeshCore companion."""
        if not self.connected:
            raise RuntimeError("Not connected to MeshCore companion")
            
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._get_node_id_async(),
                self._event_loop
            )
            return future.result(timeout=5.0)
        except Exception as e:
            self._logger.error(f"Failed to get node ID: {str(e)}")
            raise
    
    async def _get_node_id_async(self) -> str:
        """Get node ID asynchronously."""
        info_event = await self.mesh.wait_for_event(EventType.SELF_INFO, timeout=5.0)
        if not info_event:
            raise RuntimeError("Failed to get device info")
        self_info = info_event.attributes
        return self_info.get('node_id', 'unknown')
    
    def is_connected(self) -> bool:
        """Check if the service is connected to the MeshCore companion."""
        if not self.mesh:
            return False
        return self.mesh.is_connected

    def get_status(self) -> dict:
        """Get the current status of the MeshCore service."""
        return {
            'running': self.running,
            'connected': self.connected,
            'port': self.port,
            'messages_queued': self._message_queue.qsize()
        }