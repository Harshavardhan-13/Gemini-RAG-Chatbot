# Gemini Chatbot Learning Project

This project shows my step-by-step progress in building LLM chatbots using Python and the Gemini API.

The project starts with a basic chatbot and gradually adds memory, tools, databases, and Retrieval-Augmented Generation (RAG).

## Level 1: Basic Gemini Chatbot

The Level 1 chatbot can:

- Accept user messages from the terminal
- Send the message to the Gemini model
- Display the model response
- Use a system instruction to control chatbot behavior
- Stop when the user enters `exit`, `quit`, or `bye`
- Handle common API and server errors

## Project Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

## Install the dependencies:
```bash
python -m pip install -r requirements.txt
```

## Create a local .env file and add:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

## Level 1.5: Chatbot with Memory

This version adds memory to the chatbot.

It can:

- Store the conversation in `chat_history`
- Remember earlier messages during the same session
- Save the conversation in `chat_history.json`
- Reload previous conversations when the chatbot starts again
- Show saved conversations using the `history` command
- Clear saved memory using the `clear` command

Run it using:

```bash
python chatbot_level1_memory.py
```