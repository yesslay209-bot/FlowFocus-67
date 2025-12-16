from flask import Flask, render_template, jsonify, request
import random, json, os
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

DATA_FILE = "user_data.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

QUOTES_FOCUS = [
    "Small steps make big dreams bloom.",
    "Focus like the gentle flow of a stream.",
    "You’re doing amazing — one moment at a time.",
    "Every minute of focus is a gift to your future self."
]

QUOTES_BREAK = [
    "Time to rest your mind — you’ve earned it.",
    "Breathe in peace, breathe out worry.",
    "Stretch a little. Your bunny’s proud of you!",
    "Rest isn’t wasting time — it’s recharging your light."
]

# Bunny "card" definitions (simple visual via emoji + color)
# 7 bunnies with unlock streak thresholds (days of streak required)
BUNNIES = [
    {"id": "bunny_apple", "name": "Rosabelle", "emoji": "🌸🐰", "color": "#FFD6D6", "image": "pink.png", "desc": "Sweet and energetic.", "unlock_streak": 1},
    {"id": "bunny_moon", "name": "Stella", "emoji": "🌙🐰", "color": "#E6E6FF", "image": "purple.png", "desc": "Calm nighttime companion.", "unlock_streak": 2},
    {"id": "bunny_flow", "name": "Skylie", "emoji": "🦋🐰", "color": "#D6F0FF", "image": "blue.png", "desc": "Focus like the flow.", "unlock_streak": 3},
    {"id": "bunny_sun", "name": "Berrybun", "emoji": "🍓🐰", "color": "#F9DBCE", "image": "orange.png", "desc": "Sunny and motivating.", "unlock_streak": 5},
    {"id": "bunny_garden", "name": "Sprout", "emoji": "🌱🐰", "color": "#E5F9E5", "image": "green.png", "desc": "Bloom with small steps.", "unlock_streak": 7},
    {"id": "bunny_star", "name": "Sunnie", "emoji": "🌻🐰", "color": "#FAF1C9", "image": "yellow.png", "desc": "Bright and curious.", "unlock_streak": 10},
    {"id": "bunny_zen", "name": "Luma", "emoji": "🪷🐰", "color": "#FBF7F9", "image": "white.png", "desc": "Peaceful and wise.", "unlock_streak": 14}
]

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({
                "completed_sessions": 0,
                "last_date": "",
                "streak": 0,
                "collection": [],
                "available_options": [],
                "available_date": "",
                "available_claimed": False,
                "selected_bunny": None,
                "theme": "default",
                "pastel_color": "#6ECF9A"
            }, f, indent=4)
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    # Ensure keys exist for older files
    data.setdefault("collection", [])
    data.setdefault("available_options", [])
    data.setdefault("available_date", "")
    data.setdefault("available_claimed", False)
    data.setdefault("selected_bunny", None)
    data.setdefault("theme", "default")
    data.setdefault("pastel_color", "#6ECF9A")
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# home route
@app.route("/")
def home():
    quote_focus = random.choice(QUOTES_FOCUS)
    quote_break = random.choice(QUOTES_BREAK)
    user_data = load_data()
    return render_template("index.html", 
                           quote_focus=quote_focus,
                           quote_break=quote_break,
                           sessions=user_data["completed_sessions"],
                           streak=user_data["streak"],
                           user_data=user_data)

@app.route("/complete", methods=["POST"])
def complete_session():
    data = load_data()
    today = str(date.today())

    # Update completed sessions
    data["completed_sessions"] += 1

    # Update streak logic and generate daily card options when a new day is reached
    new_card_generated = False
    if data["last_date"] == "":
        data["streak"] = 1
        # generate options for the first day
        data["available_options"] = random.sample([b["id"] for b in BUNNIES], k=min(3, len(BUNNIES)))
        data["available_date"] = today
        data["available_claimed"] = False
        new_card_generated = True
    elif data["last_date"] == today:
        pass  # same day, do not add
    else:
        data["streak"] += 1
        # generate a new set of options for today (excluding already collected)
        # choose eligible bunnies: unlocked by streak and not already collected
        eligible = [b["id"] for b in BUNNIES if b["unlock_streak"] <= data.get("streak", 0) and b["id"] not in data.get("collection", [])]
        if not eligible:
            # fallback to any remaining uncollected
            eligible = [b["id"] for b in BUNNIES if b["id"] not in data.get("collection", [])]
        if not eligible:
            # if none left, allow repeats from all
            eligible = [b["id"] for b in BUNNIES]
        data["available_options"] = random.sample(eligible, k=min(3, len(eligible)))
        data["available_date"] = today
        data["available_claimed"] = False
        new_card_generated = True

    data["last_date"] = today

    save_data(data)
    response = {"data": data, "new_card_generated": new_card_generated}
    return jsonify(response)


@app.route("/bunnies")
def bunnies_page():
    user_data = load_data()
    return render_template("bunnies.html", bunnies=BUNNIES, user_data=user_data)


@app.route('/claim_card', methods=['POST'])
def claim_card():
    payload = request.get_json() or {}
    card_id = payload.get('card_id')
    data = load_data()
    today = str(date.today())
    if data.get('available_date') != today:
        return jsonify({'error': 'No available card for today'}), 400
    if data.get('available_claimed'):
        return jsonify({'error': 'Card already claimed'}), 400
    if card_id not in data.get('available_options', []):
        return jsonify({'error': 'Invalid card selected'}), 400

    # ensure streak meets unlock requirement
    card = next((b for b in BUNNIES if b['id'] == card_id), None)
    if not card:
        return jsonify({'error': 'Unknown card'}), 400
    # Allow the user to choose any available option on their very first claim (no collection yet)
    if not data.get('collection'):
        pass
    else:
        if data.get('streak', 0) < card.get('unlock_streak', 0):
            return jsonify({'error': 'Streak too low to claim this card'}), 400

    # add to collection
    if card_id not in data['collection']:
        data['collection'].append(card_id)
    data['available_claimed'] = True
    save_data(data)
    return jsonify({'success': True, 'data': data})


@app.route('/chat', methods=['POST'])
def chat():
    if not client:
        return jsonify({'error': 'OpenAI API key not configured'}), 500
    
    payload = request.get_json() or {}
    user_message = payload.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is empty'}), 400
    
    try:
        # Provide the assistant with the bunny catalog so it can answer questions about them
        system_content = (
            "You are a helpful and encouraging focus buddy for the FocusFlow app. "
            "Help users stay motivated and focused. Be warm, supportive, and brief in your responses.\n\n"
            "Available bunnies (id, name, emoji, color, image, desc, unlock_streak):\n"
            + json.dumps(BUNNIES)
            + "\n\nWhen users ask about bunnies, reference this list: explain unlock requirements, descriptions, and image names. Keep replies short and friendly. do not say the image information"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message}
            ],
            max_tokens=200
        )
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/select_bunny', methods=['POST'])
def select_bunny():
    payload = request.get_json() or {}
    bunny_id = payload.get('bunny_id')
    data = load_data()
    
    # Check if bunny is in collection
    if bunny_id not in data.get('collection', []):
        return jsonify({'error': 'Bunny not in collection'}), 400
    
    # Set as selected bunny
    data['selected_bunny'] = bunny_id
    save_data(data)
    return jsonify({'success': True, 'selected_bunny': bunny_id})


# navigate to the pomo page
@app.route("/pomo")
def pomo():
    quote_focus = random.choice(QUOTES_FOCUS)
    quote_break = random.choice(QUOTES_BREAK)
    user_data = load_data()
    return render_template("pomo.html",
                           quote_focus=quote_focus,
                           quote_break=quote_break,
                           sessions=user_data["completed_sessions"],
                           streak=user_data["streak"],
                           user_data=user_data)


@app.route("/music")
def music():
    user_data = load_data()
    return render_template("music.html", user_data=user_data)


@app.route('/settings')
def settings():
    user_data = load_data()
    return render_template('settings.html', user_data=user_data)


@app.route('/save_settings', methods=['POST'])
def save_settings():
    payload = request.get_json() or {}
    color = payload.get('pastel_color')
    theme = payload.get('theme')
    data = load_data()
    if color:
        data['pastel_color'] = color
    if theme:
        data['theme'] = theme
    save_data(data)
    return jsonify({'success': True, 'data': data})


if __name__ == "__main__":
    app.run(port=5001, debug=True)
