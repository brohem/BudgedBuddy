
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import json
import os

app = Flask(__name__)
data_file = "data.json"

# Load or initialize data
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        users = json.load(f)
else:
    users = {}

def save_data():
    with open(data_file, "w") as f:
        json.dump(users, f)

@app.route("/bot", methods=["POST"])
def bot():
    user_id = request.form["From"]
    msg = request.form["Body"].strip().lower()
    now = datetime.now().date()
    response = MessagingResponse()

    if user_id not in users:
        users[user_id] = {
            "monthly_allocation": 0,
            "current_balance": 0,
            "topup_amount": 0,
            "last_topup": None,
            "expenses": []
        }

    user = users[user_id]

    # Monthly top-up logic
    if user["last_topup"] is None or now.month != datetime.fromisoformat(user["last_topup"]).month:
        user["current_balance"] += user["topup_amount"]
        user["last_topup"] = now.isoformat()

    if msg.startswith("setbudget"):
        try:
            amount = float(msg.split()[1])
            user["monthly_allocation"] = amount
            user["topup_amount"] = amount
            user["current_balance"] = amount
            user["last_topup"] = now.isoformat()
            response.message(f"✅ Budget set to ${amount:.2f}.")
        except:
            response.message("❌ Please send: /setbudget 1000")
    elif msg.startswith("addexpense"):
        try:
            parts = msg.split()
            amount = float(parts[1])
            description = " ".join(parts[2:])
            user["current_balance"] -= amount
            user["expenses"].append({"amount": amount, "desc": description, "date": now.isoformat()})
            response.message(f"💸 {description} - ${amount:.2f} added. Remaining: ${user['current_balance']:.2f}")
        except:
            response.message("❌ Usage: /addexpense 50 groceries")
    elif msg.startswith("topup"):
        try:
            amount = float(msg.split()[1])
            user["topup_amount"] = amount
            response.message(f"🔄 Top-up amount set to ${amount:.2f}")
        except:
            response.message("❌ Usage: /topup 1000")
    elif msg.startswith("status"):
        response.message(
            f"💼 Budget: ${user['monthly_allocation']:.2f}\n"
            f"💰 Current Balance: ${user['current_balance']:.2f}\n"
            f"🔁 Top-up: ${user['topup_amount']:.2f}"
        )
    else:
        response.message("Available commands:\n/setbudget 1000\n/addexpense 50 food\n/topup 800\n/status")

    save_data()
    return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)



