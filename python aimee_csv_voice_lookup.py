import speech_recognition as sr
import pandas as pd
from datetime import datetime

# Load inventory CSV
df = pd.read_csv("inventory.csv")

def log_interaction(query, response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("aimee_query_log.txt", "a") as log_file:
        log_file.write(f"{timestamp} | QUERY: {query} | RESPONSE: {response}\n")
    print(f"💾 LOGGED: {timestamp} | QUERY: {query} | RESPONSE: {response}")


def find_info(query):
    query = query.lower()

    for _, row in df.iterrows():
        customer = row["customer_last_ordered"].lower()
        if customer in query:
            response = f"{row['customer_last_ordered']} last ordered {row['wine_name']}."
            log_interaction(query, response)
            return response

    for _, row in df.iterrows():
        wine_keywords = row["wine_name"].lower().split()
        if all(word in query for word in wine_keywords) or any(word in query for word in wine_keywords):
            if "inventory" in query or "in stock" in query or "how much" in query:
                response = f"We have {row['inventory']} bottles of {row['wine_name']} in stock."
            elif "price" in query or "cost" in query or "how much" in query:
                response = f"The price of {row['wine_name']} is {row['price']}."
            elif "ordered" in query or "last customer" in query or "who" in query:
                response = f"The last customer to order {row['wine_name']} was {row['customer_last_ordered']}."
            else:
                response = f"{row['wine_name']}: {row['inventory']} bottles at {row['price']} (last ordered by {row['customer_last_ordered']})"
            log_interaction(query, response)
            return response

    response = "Sorry, I couldn't find information about that wine or customer."
    log_interaction(query, response)
    return response

def transcribe_and_respond():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    print("🎤 Speak your wine question...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=5)

    try:
        text = recognizer.recognize_google(audio)
        print(f"📝 You said: {text}")
        response = find_info(text)
        print(f"🤖 Response: {response}")
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")

if __name__ == "__main__":
    transcribe_and_respond()
