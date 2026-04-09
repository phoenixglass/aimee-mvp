
import speech_recognition as sr
import pandas as pd

# Load inventory CSV
df = pd.read_csv("inventory.csv")

def find_info(query):
    query = query.lower()

    # Check for customer name queries
    for _, row in df.iterrows():
        customer = row["customer_last_ordered"].lower()
        if customer in query:
            return f"{row['customer_last_ordered']} last ordered {row['wine_name']}."

    # Check for wine name queries
    for _, row in df.iterrows():
        wine_keywords = row["wine_name"].lower().split()
        if all(word in query for word in wine_keywords) or any(word in query for word in wine_keywords):
            if "inventory" in query or "in stock" in query or "how much" in query:
                return f"We have {row['inventory']} bottles of {row['wine_name']} in stock."
            elif "price" in query or "cost" in query or "how much" in query:
                return f"The price of {row['wine_name']} is {row['price']}."
            elif "ordered" in query or "last customer" in query or "who" in query:
                return f"The last customer to order {row['wine_name']} was {row['customer_last_ordered']}."
            else:
                return f"{row['wine_name']}: {row['inventory']} bottles at {row['price']} (last ordered by {row['customer_last_ordered']})"

    return "Sorry, I couldn't find information about that wine or customer."

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
