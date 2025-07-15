// static/js/chatbot.js

document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const fileUpload = document.getElementById('file-upload');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const clearChatButton = document.getElementById('clear-chat-button');

    // Function to scroll to the bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Initial scroll to the bottom on load (after Jinja renders initial history)
    scrollToBottom();

    // Function to add a message to the chat display
    function addMessage(role, content, isHtml = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);

        if (isHtml) {
            messageDiv.innerHTML = content;
        } else {
            messageDiv.textContent = content;
        }

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }

    // Event listener for file input change
    fileUpload.addEventListener('change', function() {
        if (fileUpload.files.length > 0) {
            fileNameDisplay.textContent = fileUpload.files[0].name;
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    });

    // Function to send message to backend
    async function sendMessage() {
        const message = userInput.value.trim();
        const file = fileUpload.files[0];

        if (!message && !file) {
            alert('Please enter a message or select a file to send.');
            return;
        }

        // Display user's message immediately (without file name for now, added by backend)
        addMessage('user', message + (file ? ` (Uploading: ${file.name})` : ''));
        userInput.value = ''; // Clear input field
        fileNameDisplay.textContent = 'No file chosen'; // Clear file display
        fileUpload.value = ''; // Clear file input

        const botMessageElement = addMessage('bot', '...'); // Placeholder for streaming
        let fullBotResponse = '';

        const formData = new FormData();
        if (message) {
            formData.append('message', message);
        }
        if (file) {
            formData.append('file', file);
        }

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error:', errorText);
                botMessageElement.textContent = `Error: ${errorText}`;
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                fullBotResponse += chunk;
                botMessageElement.innerHTML = marked.parse(fullBotResponse);
                scrollToBottom();
            }

        } catch (error) {
            console.error('Network or other error:', error);
            botMessageElement.textContent = 'An error occurred while connecting to the chatbot.';
        }
    }

    // Send message on button click
    sendButton.addEventListener('click', sendMessage);

    // Send message on Enter key press in the input field
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });

    // Event listener for Clear Chat button (UPDATED)
    clearChatButton.addEventListener('click', async function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to clear the entire chat history? This will delete it permanently.')) {
            try {
                const response = await fetch('/api/clear_chat', {
                    method: 'POST',
                });

                const result = await response.json(); // Expecting JSON response

                if (response.ok && result.success) { // Check both HTTP status and custom success flag
                    chatMessages.innerHTML = ''; // Clear messages from the display
                    addMessage('bot', 'Chat history cleared.');
                } else {
                    alert('Failed to clear chat: ' + result.message);
                    console.error('Failed to clear chat:', result.message);
                }
            } catch (error) {
                console.error('Error clearing chat:', error);
                alert('An unexpected error occurred while trying to clear chat.');
            }
        }
    });
});