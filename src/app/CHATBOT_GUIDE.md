# AI in Classics Chatbot Guide

## Overview

The AI in Classics project now includes a chatbot feature that allows users to get instant help while using the Greek Lemmatizer. The chatbot appears as a small floating button in the bottom right corner of the interface, represented by a Greek amphora icon (🏺).

## Features

1. **Floating Button**: A non-intrusive button that stays visible as users scroll through the website
2. **Popup Chat Interface**: Opens a chat window when clicked without navigating to another page
3. **Personalized Avatar**: Custom Greek amphora avatar representing the chatbot
4. **Contextual Help**: Provides assistance with using the lemmatizer and understanding Greek linguistic concepts

## How to Use the Chatbot

1. **Enable the Chatbot**: In the sidebar, make sure the "Enable AI Assistant" checkbox is checked.
2. **Open the Chat**: Click the amphora icon (🏺) in the bottom right corner to open the chat interface.
3. **Ask Questions**: Type your question in the text input at the bottom of the chat window and press Enter or click the send button.
4. **Close the Chat**: Click the X in the top right corner of the chat window to close it.

## Sample Questions

The chatbot can answer questions like:

- "What is lemmatization?"
- "How do I search for texts?"
- "How do I load texts into the system?"
- "What can you help me with?"
- "Tell me about this tool"

## Technical Details

The chatbot is implemented using:

- Streamlit components for UI rendering
- Custom CSS for styling
- JavaScript for interactive behavior
- SVG for the customizable avatar

## How to Run the Application

To run the application with the chatbot:

```bash
# Navigate to the app directory
cd src/app

# Run the Streamlit application
streamlit run app.py
```

## Future Enhancements

1. **Advanced NLP**: Improve response generation using more sophisticated NLP techniques
2. **Context Awareness**: Make the chatbot aware of the current state of the application
3. **Custom Avatar**: Replace the SVG avatar with a designed/drawn character by a team member
4. **Chat History**: Add persistence to chat history across sessions
5. **Multi-language Support**: Add support for answering questions in multiple languages
