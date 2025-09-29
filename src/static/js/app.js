document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('message-form');
    const messageList = document.getElementById('message-list');
    const messageType = document.getElementById('message-type');
    const contactSelect = document.getElementById('contact-select');

    // Handle message type selection
    messageType.addEventListener('change', function() {
        contactSelect.style.display = this.value === 'private' ? 'block' : 'none';
    });

    // Handle message form submission
    messageForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const content = document.getElementById('message').value;
        const isPublic = messageType.value === 'public';
        const receiverNode = isPublic ? null : document.getElementById('contact').value;

        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    receiver_node: receiverNode
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            // Clear the message input
            document.getElementById('message').value = '';

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to send message');
        }
    });

    // Setup Server-Sent Events for real-time updates
    const eventSource = new EventSource('/api/messages/stream');
    
    eventSource.onmessage = function(event) {
        const message = JSON.parse(event.data);
        
        // Create new message element
        const messageElement = document.createElement('div');
        messageElement.className = 'message-item mb-3';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message.content;
        
        const meta = document.createElement('div');
        meta.className = 'message-meta text-muted small';
        meta.innerHTML = `From: ${message.sender_node}`;
        if (!message.is_public) {
            meta.innerHTML += ` to: ${message.receiver_node}`;
        }
        meta.innerHTML += `<br>${new Date(message.timestamp).toLocaleString()}`;
        
        messageElement.appendChild(content);
        messageElement.appendChild(meta);
        
        // Add to message list
        messageList.insertBefore(messageElement, messageList.firstChild);
        
        // Remove oldest message if more than 25 are shown
        if (messageList.children.length > 25) {
            messageList.removeChild(messageList.lastChild);
        }
    };

    eventSource.onerror = function(error) {
        console.error('EventSource failed:', error);
        eventSource.close();
    };
});