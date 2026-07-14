import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types


# -----------------------------
# 1. Load environment variables
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
# 3. Choose model
# -----------------------------
MODEL_NAME = "gemini-3.1-flash-lite"


# -----------------------------
# 4. System instruction
# -----------------------------
SYSTEM_INSTRUCTION = """
You are a helpful beginner-friendly chatbot.
Explain answers clearly and simply.
Avoid very long answers unless the user asks for details.
"""


# -----------------------------
# 5. Start chatbot
# -----------------------------
print("Gemini Level 1 Chatbot")
print("Type 'exit' to stop.\n")


while True:
    user_message = input("You: ").strip()

    if not user_message:
        print("Bot: Please type something.\n")
        continue

    if user_message.lower() in ["exit", "quit", "bye"]:
        print("Bot: Goodbye!")
        break

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=500,
            )
        )

        print("Bot:", response.text)
        print()

    except errors.ServerError:
        print("Bot: The Gemini model is busy right now. Please try again in a few seconds.\n")

    except errors.ClientError as e:
        print("Bot: There is a client/API issue.")
        print("Details:", e)
        print()

    except Exception as e:
        print("Bot: Something unexpected went wrong.")
        print("Details:", e)
        print()