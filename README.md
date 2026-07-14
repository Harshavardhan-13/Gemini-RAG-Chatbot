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

## Level 2: Chatbot with Tools

This version adds tool calling to the chatbot.

The chatbot can decide when to use Python functions instead of only answering from the LLM.

Tools included:

- Calculator for accurate math
- Weather lookup using an external API
- Date and time lookup
- CSV file loading into an in-memory SQLite database
- Safe SQL `SELECT` queries
- Local email draft creation
- Local calendar event creation
- Persistent chat memory

Run it using:

```bash
python chatbot_level2_tools.py
```

When the program starts, it asks for a CSV file path.

Enter a CSV path to load it as a database, or press Enter to skip it.

Example:

```text
hospital_appointment_no_show_5000.csv
```

Example questions:

```text
Calculate 245 * 17

What is the weather in Seattle?

What columns are in the database?

Create an email draft to test@example.com

Add a calendar event for tomorrow
```

The email tool only creates local drafts, and the calendar tool only stores local events. It does not send real emails or update Google Calendar.



## Level 3: Basic RAG Chatbot

This version adds Retrieval-Augmented Generation (RAG).

The chatbot can:

- Read TXT, Markdown, and PDF files
- Split large documents into overlapping chunks
- Create embeddings for each chunk
- Store embeddings in a Chroma vector database
- Convert the user question into an embedding
- Retrieve the most relevant chunks using similarity search
- Send only the retrieved context to Gemini
- Generate answers based on the uploaded document

Run it using:

```bash
python chatbot_level3_rag.py
```

Inside the chatbot, type:

```text
upload
```

Then enter the file path:

```text
sample_data/policy.txt
```

Example questions:

```text
How many sick leaves do employees get?

How long does refund processing take?

What is the cancellation policy?

What is the laptop replacement policy?
```

The first questions should be answered from the document. If the answer is not present, the chatbot should say that it could not find the information.

### RAG Flow

```text
Upload document
        ↓
Extract text
        ↓
Split text into chunks
        ↓
Create embeddings
        ↓
Store chunks in Chroma
        ↓
User asks a question
        ↓
Create question embedding
        ↓
Retrieve relevant chunks
        ↓
Send retrieved context to Gemini
        ↓
Generate the final answer
```







## Project Structure

```text
Gemini_chatbot/
│
├── chatbot_level1.py
├── chatbot_level1_memory.py
├── chatbot_level2_tools.py
├── chatbot_level3_rag.py
├── sample_data/
│   └── policy.txt
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Important Notes

- The real `.env` file is kept private and is not uploaded to GitHub.
- The `.env.example` file only shows the required API key format.
- `chat_history.json` stores chatbot memory locally.
- `calendar_events.json` stores local calendar events.
- The `drafts` folder stores local email drafts.
- The `chroma_db` folder stores the local vector database.
- Generated files and private datasets are excluded through `.gitignore`.
- The email tool does not send real emails.
- The calendar tool does not update Google Calendar.
- The database tool allows only safe `SELECT` queries.
- Text-based PDFs work best with the current RAG chatbot.
- Image-based or scanned PDFs may require OCR.




## Testing

### Test Level 1

Run:

```bash
python chatbot_level1.py
```

Try:

```text
Hello

Explain what an LLM is in simple words

exit
```

### Test Level 1.5 Memory

Run:

```bash
python chatbot_level1_memory.py
```

Try:

```text
My name is Vru

What is my name?

history

exit
```

Run the chatbot again and ask:

```text
What is my name?
```

The chatbot should reload the saved memory.

### Test Level 2 Tools

Run:

```bash
python chatbot_level2_tools.py
```

Try:

```text
Calculate 245 * 17

What is the weather in Seattle?

Create an email draft to test@example.com

Add a calendar event for tomorrow
```

To test the database tool, provide a CSV file path when the program starts.

### Test Level 3 RAG

Run:

```bash
python chatbot_level3_rag.py
```

Type:

```text
upload
```

Then provide:

```text
sample_data/policy.txt
```

Try:

```text
How many sick leaves do employees get?

How long does refund processing take?

What is the cancellation policy?

What is the laptop replacement policy?
```

The chatbot should answer the first questions from the document and say when information is not present.
