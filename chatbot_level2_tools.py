import os
import json
import ast
import operator
import urllib.parse
import urllib.request
import sqlite3
import uuid
from pathlib import Path

from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types


# =====================================================
# 1. Load API key
# =====================================================

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")


# =====================================================
# 2. Create Gemini client
# =====================================================

client = genai.Client(api_key=api_key)


# =====================================================
# 3. App settings
# =====================================================

MODEL_NAME = "gemini-3.1-flash-lite"

MEMORY_FILE = "chat_history.json"
DRAFTS_DIR = Path("drafts")
CALENDAR_FILE = "calendar_events.json"

SYSTEM_INSTRUCTION = """
You are a helpful beginner-friendly chatbot.

You have access to tools.

Use tools when needed:
- Use calculator for math.
- Use get_weather for current weather.
- Use query_database or get_database_schema for database questions.
- Use create_email_draft for email draft requests.
- Use get_current_datetime, add_calendar_event, or list_calendar_events for date/calendar tasks.

Important:
- Do not pretend you sent a real email. You only create local email drafts.
- Do not pretend you updated Google Calendar. You only save local calendar events.
- Explain answers clearly and simply.
- Keep answers short unless the user asks for detail.
"""


# =====================================================
# 4. Create required folders/files
# =====================================================

def setup_storage():
    DRAFTS_DIR.mkdir(exist_ok=True)

    if not os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "w") as file:
            json.dump([], file, indent=4)


# =====================================================
# 5. Safe calculator tool
# =====================================================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed.")

    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op_type = type(node.op)

        if op_type not in ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed.")

        return ALLOWED_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        op_type = type(node.op)

        if op_type not in ALLOWED_OPERATORS:
            raise ValueError("Operator not allowed.")

        return ALLOWED_OPERATORS[op_type](operand)

    raise ValueError("Invalid expression.")


def calculator(expression: str) -> str:
    
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return f"The result is {result}"
    except Exception as e:
        return f"Calculator error: {e}"


# =====================================================
# 6. Weather tool
# =====================================================

def get_weather(city: str) -> str:
    
    try:
        encoded_city = urllib.parse.quote(city)

        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={encoded_city}&count=1&language=en&format=json"
        )

        with urllib.request.urlopen(geo_url) as response:
            geo_data = json.loads(response.read().decode())

        if "results" not in geo_data or not geo_data["results"]:
            return f"Could not find weather location for {city}."

        location = geo_data["results"][0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        location_name = location["name"]
        country = location.get("country", "")

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
            f"&temperature_unit=fahrenheit"
            f"&wind_speed_unit=mph"
        )

        with urllib.request.urlopen(weather_url) as response:
            weather_data = json.loads(response.read().decode())

        current = weather_data["current"]

        temperature = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind_speed = current["wind_speed_10m"]

        return (
            f"Current weather in {location_name}, {country}: "
            f"{temperature}°F, humidity {humidity}%, wind speed {wind_speed} mph."
        )

    except Exception as e:
        return f"Weather tool error: {e}"


# =====================================================
# Database-from-file tools
# =====================================================

DATABASE_CONNECTION = None
DATABASE_TABLE_NAME = "uploaded_data"


def clean_column_name(column_name):
    """
    Converts messy CSV column names into safe SQL column names.
    Example:
    "First Name" -> "first_name"
    "Total Amount ($)" -> "total_amount"
    """
    cleaned = column_name.strip().lower()
    cleaned = "".join(char if char.isalnum() else "_" for char in cleaned)
    cleaned = "_".join(part for part in cleaned.split("_") if part)

    if not cleaned:
        cleaned = "column"

    if cleaned[0].isdigit():
        cleaned = "col_" + cleaned

    return cleaned


def load_csv_as_database(file_path):
 
    import csv

    global DATABASE_CONNECTION

    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    if not file_path.lower().endswith(".csv"):
        return "Only CSV files are supported for database loading right now."

    DATABASE_CONNECTION = sqlite3.connect(":memory:")
    DATABASE_CONNECTION.row_factory = sqlite3.Row

    cursor = DATABASE_CONNECTION.cursor()

    with open(file_path, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        original_columns = reader.fieldnames

        if not original_columns:
            return "CSV file has no header row."

        cleaned_columns = [clean_column_name(col) for col in original_columns]

        column_definitions = ", ".join(
            [f'"{col}" TEXT' for col in cleaned_columns]
        )

        cursor.execute(
            f'CREATE TABLE {DATABASE_TABLE_NAME} ({column_definitions})'
        )

        rows_inserted = 0

        for row in reader:
            values = [row.get(original_col, "") for original_col in original_columns]

            placeholders = ", ".join(["?"] * len(values))
            column_names = ", ".join([f'"{col}"' for col in cleaned_columns])

            cursor.execute(
                f'INSERT INTO {DATABASE_TABLE_NAME} ({column_names}) VALUES ({placeholders})',
                values
            )

            rows_inserted += 1

    DATABASE_CONNECTION.commit()

    return (
        f"CSV loaded successfully as database table '{DATABASE_TABLE_NAME}'.\n"
        f"Rows loaded: {rows_inserted}\n"
        f"Columns: {', '.join(cleaned_columns)}"
    )


def get_database_schema() -> str:
    """
    Show the currently loaded database table and columns.
    Use this before writing SQL.
    """
    try:
        if DATABASE_CONNECTION is None:
            return "No database file is loaded."

        cursor = DATABASE_CONNECTION.cursor()

        cursor.execute(f"PRAGMA table_info({DATABASE_TABLE_NAME})")
        columns = cursor.fetchall()

        schema = {
            DATABASE_TABLE_NAME: [
                {
                    "name": column[1],
                    "type": column[2]
                }
                for column in columns
            ]
        }

        return json.dumps(schema, indent=2)

    except Exception as e:
        return f"Database schema error: {e}"


def query_database(sql: str) -> str:
    """
    Run a safe SELECT query on the loaded CSV database.

    Only SELECT queries are allowed.
    The table name is uploaded_data.
    """
    try:
        if DATABASE_CONNECTION is None:
            return "No database file is loaded."

        cleaned_sql = sql.strip().lower()

        if not cleaned_sql.startswith("select"):
            return "Only SELECT queries are allowed for safety."

        if ";" in sql.rstrip(";"):
            return "Only one SQL statement is allowed."

        cursor = DATABASE_CONNECTION.cursor()
        cursor.execute(sql)

        rows = cursor.fetchall()
        results = [dict(row) for row in rows]

        if not results:
            return "No matching rows found."

        return json.dumps(results[:30], indent=2)

    except Exception as e:
        return f"Database query error: {e}"


# =====================================================
# 8. Email draft tools
# =====================================================

def create_email_draft(to: str, subject: str, body: str) -> str:
    """
    Create a local email draft.

    This does not send a real email.
    It saves the email draft inside the drafts folder.
    """
    try:
        draft_id = str(uuid.uuid4())[:8]

        draft = {
            "draft_id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": datetime.now().isoformat()
        }

        draft_path = DRAFTS_DIR / f"email_draft_{draft_id}.json"

        with open(draft_path, "w", encoding="utf-8") as file:
            json.dump(draft, file, indent=4)

        return (
            f"Email draft created successfully.\n"
            f"Draft ID: {draft_id}\n"
            f"Saved file: {draft_path}\n"
            f"Note: This email was not sent."
        )

    except Exception as e:
        return f"Email draft error: {e}"


def list_email_drafts() -> str:
    """
    List locally saved email drafts.
    """
    try:
        drafts = []

        for file_path in DRAFTS_DIR.glob("email_draft_*.json"):
            with open(file_path, "r", encoding="utf-8") as file:
                drafts.append(json.load(file))

        if not drafts:
            return "No email drafts found."

        return json.dumps(drafts, indent=2)

    except Exception as e:
        return f"Email draft list error: {e}"


# =====================================================
# 10. Calendar tools
# =====================================================

def get_current_datetime() -> str:
    """
    Get the current date and time.

    Use this when the user asks today's date, current time,
    or date-related questions.
    """
    try:
        timezone = "America/New_York"
        now = datetime.now(ZoneInfo(timezone))

        return (
            f"Current date and time in {timezone}: "
            f"{now.strftime('%Y-%m-%d %I:%M %p %Z')}"
        )

    except Exception as e:
        return f"Date/time error: {e}"


def add_calendar_event(
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = ""
) -> str:
    """
    Add a local calendar event.

    Date format: YYYY-MM-DD
    Time format: HH:MM in 24-hour format

    This does not add to Google Calendar.
    It saves the event locally.
    """
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")

        with open(CALENDAR_FILE, "r", encoding="utf-8") as file:
            events = json.load(file)

        event_id = str(uuid.uuid4())[:8]

        event = {
            "event_id": event_id,
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "created_at": datetime.now().isoformat()
        }

        events.append(event)

        with open(CALENDAR_FILE, "w", encoding="utf-8") as file:
            json.dump(events, file, indent=4)

        return (
            f"Calendar event saved locally.\n"
            f"Event ID: {event_id}\n"
            f"Title: {title}\n"
            f"Date: {date}\n"
            f"Time: {start_time} - {end_time}\n"
            f"Note: This was not added to Google Calendar."
        )

    except ValueError:
        return "Invalid date or time format. Use date YYYY-MM-DD and time HH:MM."

    except Exception as e:
        return f"Calendar event error: {e}"


def list_calendar_events(date: str = "") -> str:
    """
    List locally saved calendar events.

    If date is provided, use format YYYY-MM-DD.
    If date is empty, list all events.
    """
    try:
        with open(CALENDAR_FILE, "r", encoding="utf-8") as file:
            events = json.load(file)

        if date:
            events = [event for event in events if event["date"] == date]

        if not events:
            return "No calendar events found."

        return json.dumps(events, indent=2)

    except Exception as e:
        return f"Calendar list error: {e}"


# =====================================================
# 11. Memory functions
# =====================================================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError:
        print("Warning: Memory file is corrupted. Starting with empty memory.")
        return []


def save_memory(chat_history):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(chat_history, file, indent=4)


# =====================================================
# 12. Setup app
# =====================================================

setup_storage()

database_path = input("Enter CSV database file path, or press Enter to skip: ").strip()

if database_path:
    result = load_csv_as_database(database_path)
    print(result)
    print()

chat_history = load_memory()


# =====================================================
# 13. Start chatbot
# =====================================================

print("Gemini Chatbot with Tools")
print("Type 'exit' to stop.")
print("Type 'history' to see conversation.")
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
        chat_history.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=chat_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[
                        calculator,
                        get_weather,
                        get_database_schema,
                        query_database,
                        create_email_draft,
                        list_email_drafts,
                        get_current_datetime,
                        add_calendar_event,
                        list_calendar_events,
                    ],
                temperature=0.3,
                max_output_tokens=1000,
            )
        )

        bot_reply = response.text

        print("Bot:", bot_reply)
        print()

        chat_history.append({
            "role": "model",
            "parts": [{"text": bot_reply}]
        })

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