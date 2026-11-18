from navigator import Navigator
from speech import speak, listen

def ask_continue():
    speak("Do you want to go somewhere else?")

    while True:
        response = listen()

        if response is None:
            continue

        response = response.lower()

        if any(word in response for word in ["yes", "yeah", "yep", "sure", "okay"]):
            return True

        if any(word in response for word in ["no", "nope", "thank", "thanks"]):
            return False

        speak("Please say yes or no.")

if __name__ == "__main__":
    speak("Starting G I U Smart Glasses Navigation.")

    nav = Navigator()
    first_run = True

    while True:                                          # ← indented inside if block
        nav.start(reuse_last_location=not first_run)
        first_run = False

        if not ask_continue():
            speak("Okay. Have a nice day. Shutting down navigation.")
            break