import streamlit as st
from globals import globals
import os
import random
from chatbot_avatar import get_avatar_html, create_avatar_file

def get_bot_response(query):
    """
    Generate responses from the chatbot based on user query.
    This is a simple implementation that can be expanded later with more advanced NLP.
    """
    # Dictionary of common questions and answers related to Greek lemmatization
    responses = {
        "hello": "Hello! I'm your AI in Classics assistant. How can I help you with Greek lemmatization?",
        "help": "I can help you with using this tool for Greek lemmatization, searching texts, and analyzing results. What specifically are you trying to do?",
        "what is lemmatization": "Lemmatization is the process of determining the base form (lemma) of a word. For Greek texts, this means finding the dictionary form of inflected words.",
        "how to search": "To search texts, go to the Query tab, enter your search terms, and click the Search button.",
        "how to load": "To load texts, go to the Load tab and either provide a directory path to your texts or upload a CSV file.",
        "what can you do": "I can help you navigate the Greek lemmatizer, explain features, assist with searches, and answer questions about Greek language processing.",
        "about": "This tool is part of the AI in Classics project focused on digital humanities and computational approaches to ancient texts.",
    }
    
    # Convert query to lowercase for case-insensitive matching
    query_lower = query.lower()
    
    # Check for exact matches first
    if query_lower in responses:
        return responses[query_lower]
    
    # Check for partial matches
    for key in responses:
        if key in query_lower:
            return responses[key]
    
    # Default response if no match is found
    default_responses = [
        "I'm not sure about that. Could you rephrase your question about Greek lemmatization?",
        "That's an interesting question about Greek texts. Could you provide more details?",
        "I'm still learning about Greek linguistics. Could you ask something more specific about the lemmatizer?",
        "I don't have information about that yet. Would you like to know how to use the search or analyze features instead?"
    ]
    
    return random.choice(default_responses)

def render_chat_message(is_user, message):
    """Render a chat message with appropriate styling"""
    if is_user:
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
            <div style="background-color: #2e7bf3; color: white; border-radius: 18px 18px 0 18px; 
                        padding: 8px 12px; max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        avatar_html = get_avatar_html()
        st.markdown(f"""
        <div style="display: flex; align-items: flex-start; margin-bottom: 10px;">
            <div style="margin-right: 8px;">{avatar_html}</div>
            <div style="background-color: #f0f2f5; color: black; border-radius: 18px 18px 18px 0; 
                        padding: 8px 12px; max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)

def chatbot():
    """Main function to render the chatbot UI"""
    # Use session state to maintain chat history
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    
    # CSS for floating button and chat container
    st.markdown("""
    <style>
    /* Floating button styles */
    .floating-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #3f8cff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 24px;
        cursor: pointer;
        z-index: 1000;
        transition: all 0.3s ease;
    }
    .floating-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }
    
    /* Chat container styles */
    .chat-container {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 350px;
        height: 450px;
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        z-index: 999;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    .chat-header {
        background-color: #3f8cff;
        color: white;
        padding: 15px;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .chat-body {
        flex-grow: 1;
        padding: 15px;
        overflow-y: auto;
    }
    .chat-footer {
        padding: 10px;
        border-top: 1px solid #f0f2f5;
        display: flex;
    }
    .chat-input {
        flex-grow: 1;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 8px 15px;
        margin-right: 10px;
    }
    .chat-send {
        background-color: #3f8cff;
        color: white;
        border: none;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add JavaScript to toggle chat visibility
    st.markdown("""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Add floating button
        const floatingBtn = document.createElement('div');
        floatingBtn.className = 'floating-btn';
        floatingBtn.innerHTML = '🏺';
        floatingBtn.onclick = function() {
            const chatContainer = document.querySelector('.chat-container');
            if (chatContainer.style.display === 'none' || !chatContainer.style.display) {
                chatContainer.style.display = 'flex';
            } else {
                chatContainer.style.display = 'none';
            }
        };
        document.body.appendChild(floatingBtn);
        
        // Create chat container (initially hidden)
        const chatContainer = document.createElement('div');
        chatContainer.className = 'chat-container';
        chatContainer.style.display = 'none';
        
        // Chat header
        const chatHeader = document.createElement('div');
        chatHeader.className = 'chat-header';
        chatHeader.innerHTML = '<span>AI in Classics Assistant</span><span style="cursor:pointer;" onclick="document.querySelector(\'.chat-container\').style.display=\'none\'">✖</span>';
        
        // Chat body
        const chatBody = document.createElement('div');
        chatBody.className = 'chat-body';
        
        // Chat footer
        const chatFooter = document.createElement('div');
        chatFooter.className = 'chat-footer';
        
        const chatInput = document.createElement('input');
        chatInput.className = 'chat-input';
        chatInput.placeholder = 'Type your question...';
        chatInput.onkeypress = function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        };
        
        const chatSend = document.createElement('div');
        chatSend.className = 'chat-send';
        chatSend.innerHTML = '➤';
        chatSend.onclick = sendMessage;
        
        function sendMessage() {
            const userInput = chatInput.value.trim();
            if (userInput) {
                // Add user message to chat
                const userMsg = document.createElement('div');
                userMsg.style.display = 'flex';
                userMsg.style.justifyContent = 'flex-end';
                userMsg.style.marginBottom = '10px';
                userMsg.innerHTML = `<div style="background-color: #2e7bf3; color: white; border-radius: 18px 18px 0 18px; 
                                    padding: 8px 12px; max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                    ${userInput}</div>`;
                chatBody.appendChild(userMsg);
                
                // Clear input
                chatInput.value = '';
                
                // Simulate bot response (in real implementation, this would be replaced with an API call)
                setTimeout(function() {
                    const botMsg = document.createElement('div');
                    botMsg.style.display = 'flex';
                    botMsg.style.justifyContent = 'flex-start';
                    botMsg.style.marginBottom = '10px';
                    botMsg.innerHTML = `<div style="background-color: #f0f2f5; color: black; border-radius: 18px 18px 18px 0; 
                                      padding: 8px 12px; max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                      I'm your AI classics assistant. This is a placeholder response. In a real implementation, I would provide helpful information about Greek lemmatization.</div>`;
                    chatBody.appendChild(botMsg);
                    chatBody.scrollTop = chatBody.scrollHeight;
                    
                    // Update Streamlit session state via component callback
                    window.parent.postMessage({
                        type: 'streamlit:chatMessage',
                        userMessage: userInput
                    }, '*');
                }, 500);
                
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        }
        
        chatFooter.appendChild(chatInput);
        chatFooter.appendChild(chatSend);
        
        chatContainer.appendChild(chatHeader);
        chatContainer.appendChild(chatBody);
        chatContainer.appendChild(chatFooter);
        
        document.body.appendChild(chatContainer);
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Streamlit-specific chat implementation (backup for when JavaScript isn't working)
    # This creates a visible chat interface within the Streamlit app
    with st.expander("AI in Classics Chat Assistant", expanded=False):
        # Display chat history
        for message in st.session_state.chat_history:
            render_chat_message(message["is_user"], message["text"])
        
        # Input for new messages
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input("Type your question here:", key="chat_input")
            submit_button = st.form_submit_button("Send")
            
            if submit_button and user_input:
                # Add user message to chat history
                st.session_state.chat_history.append({"is_user": True, "text": user_input})
                
                # Get bot response
                bot_response = get_bot_response(user_input)
                
                # Add bot response to chat history
                st.session_state.chat_history.append({"is_user": False, "text": bot_response})
                
                # Rerun to show the updated chat
                st.experimental_rerun()

# Function to initialize the chatbot
def init_chatbot():
    # This function adds the chatbot to any Streamlit page
    # Create avatar file if it doesn't exist
    create_avatar_file()
    
    # Add a div that will be filled with our floating button and chat using JavaScript
    st.markdown('<div id="chatbot-container"></div>', unsafe_allow_html=True)
    
    # If JavaScript is disabled, show a basic toggle for the chat
    if globals.get('show_chat', False):
        chatbot()
