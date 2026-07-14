import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types


# -----------------------------
# 1. Load API key
# -----------------------------
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")


# -----------------------------
# 2. Create Gemini client
# -----------------------------
client = genai.Client(api_key=api_key)


# -----------------------------
# 3. Model and settings
# -----------------------------
MODEL_NAME = "gemini-3.1-flash-lite"

MEMORY_FILE = "chat_history.json"

SYSTEM_INSTRUCTION = """
You are a helpful beginner-friendly chatbot.
Explain answers clearly and simply.
Avoid very long answers unless the user asks for details.
"""


# -----------------------------
# 4. Load memory from file
# -----------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print("Warning: Memory file is corrupted. Starting with empty memory.")
        return []


# -----------------------------
# 5. Save memory to file
# -----------------------------
def save_memory(chat_history):
    with open(MEMORY_FILE, "w") as file:
        json.dump(chat_history, file, indent=4)


# -----------------------------
# 6. Start with saved memory
# -----------------------------
chat_history = load_memory()


# -----------------------------
# 7. Start chatbot
# -----------------------------
print("Gemini Chatbot is Ready!!")
print("Type 'exit' to stop.")
print("Type 'history' to see saved conversation.")
print("Type 'clear' to clear memory.\n")

if chat_history:
    print(f"Loaded {len(chat_history)} saved messages from memory.\n")


while True:
    user_message = input("You: ").strip()

    if not user_message:
        print("Bot: Please type something.\n")
        continue

    if user_message.lower() in ["exit", "quit", "bye"]:
        print("Bot: Goodbye!")
        break

    if user_message.lower() == "history":
        print("\n--- Chat History ---")
        for message in chat_history:
            role = message["role"]
            text = message["parts"][0]["text"]
            print(f"{role}: {text}")
        print("--------------------\n")
        continue

    if user_message.lower() == "clear":
        chat_history.clear()
        save_memory(chat_history)
        print("Bot: Memory cleared.\n")
        continue

    try:
        # Add user's message to memory
        chat_history.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        # Send full conversation history to Gemini
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=chat_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=500,
            )
        )

        bot_reply = response.text

        print("Bot:", bot_reply)
        print()

        # Add bot response to memory
        chat_history.append({
            "role": "model",
            "parts": [{"text": bot_reply}]
        })

        # Save updated memory to file
        save_memory(chat_history)

    except errors.ServerError:
        print("Bot: The Gemini model is busy right now. Please try again in a few seconds.\n")

        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
            save_memory(chat_history)

    except errors.ClientError as e:
        print("Bot: There is a client/API issue.")
        print("Details:", e)
        print()

        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
            save_memory(chat_history)

    except Exception as e:
        print("Bot: Something unexpected went wrong.")
        print("Details:", e)
        print()

        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
            save_memory(chat_history)