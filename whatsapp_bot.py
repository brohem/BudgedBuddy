# Version: 0.4.4

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
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

# Shared account logic
def get_account_id(user_number):
    for account_id, account_data in users.items():
        if isinstance(account_data, dict) and 'members' in account_data:
            if user_number in account_data['members']:
                return account_id
    return user_number  # fallback to personal

def ensure_user_structure(user_id, phone_number):
    if user_id not in users:
        users[user_id] = {
            "members": [phone_number],
            "monthly_allocation": 0,
            "current_balance": 0,
            "topup_amount": 0,
            "last_topup": None,
            "expenses": []
        }
    elif phone_number not in users[user_id].get("members", []):
        users[user_id]["members"].append(phone_number)

def add_expense(user, amount, description, now):
    user["current_balance"] -= amount
    user["expenses"].append({
        "amount": amount,
        "desc": description,
        "date": now.isoformat()
    })

def add_quick_expense(user, amount, description, now):
    user["current_balance"] += amount  # amount is negative
    user["expenses"].append({
        "amount": abs(amount),
        "desc": description,
        "date": now.isoformat()
    })

def check_negative_balance(user, response):
    if user["current_balance"] < 0:
        response.message(f"⚠️ Warning: Your balance is negative (${user['current_balance']:.2f}). Please review your spending.")

@app.route("/bot", methods=["POST"])
def bot():
    raw_user_id = request.form["From"]
    user_id = get_account_id(raw_user_id)
    msg = request.form["Body"].strip().lower()
    if msg.startswith("/"):
        msg = msg[1:]

    now = datetime.now().date()
    response = MessagingResponse()

    ensure_user_structure(user_id, raw_user_id)

    user = users[user_id]

    if user["last_topup"] is None or now.month != datetime.fromisoformat(user["last_topup"]).month:
        user["current_balance"] += user["topup_amount"]
        user["last_topup"] = now.isoformat()

    try:
        if msg.startswith("-"):
            parts = msg.split()
            amount = float(parts[0])
            description = " ".join(parts[1:]) if len(parts) > 1 else "Quick entry"
            add_quick_expense(user, amount, description, now)
            response.message(f"💸 {description} - ${abs(amount):.2f} added. Remaining: ${user['current_balance']:.2f}")
            check_negative_balance(user, response)
            save_data()
            return str(response)

        elif msg.startswith("setbudget"):
            amount = float(msg.split()[1])
            user["monthly_allocation"] = amount
            user["topup_amount"] = amount
            user["current_balance"] = amount
            user["last_topup"] = now.isoformat()
            response.message(f"✅ Budget set to ${amount:.2f}.")

        elif msg.startswith("addexpense"):
            parts = msg.split()
            amount = float(parts[1])
            description = " ".join(parts[2:])
            add_expense(user, amount, description, now)
            response.message(f"💸 {description} - ${amount:.2f} added. Remaining: ${user['current_balance']:.2f}")
            check_negative_balance(user, response)

        elif msg.startswith("topup"):
            amount = float(msg.split()[1])
            user["topup_amount"] = amount
            response.message(f"🔄 Top-up amount set to ${amount:.2f}")

        elif msg.startswith("share"):
            parts = msg.split()
            if len(parts) == 2 and parts[1].startswith("+"):
                invitee = "whatsapp:" + parts[1].lstrip("whatsapp:")
                if invitee in users[user_id].get("members", []):
                    response.message(f"ℹ️ {invitee} is already part of your budget.")
                else:
                    if "pending_invites" not in users[user_id]:
                        users[user_id]["pending_invites"] = []
                    users[user_id]["pending_invites"].append(invitee)
                    response.message(f"📨 Invitation sent to {invitee}. Ask them to type 'accept' to join.")
            else:
                response.message("❌ Usage: share +1234567890")

        elif msg.startswith("accept"):
            for acc_id, data in users.items():
                if isinstance(data, dict) and raw_user_id in data.get("pending_invites", []):
                    data["members"].append(raw_user_id)
                    data["pending_invites"].remove(raw_user_id)
                    response.message("✅ You've joined a shared budget!")
                    break
            else:
                response.message("❌ No invitation found. Ask someone to share with you first.")

        elif msg.startswith("status"):
            response.message(
                f"💼 Budget: ${user['monthly_allocation']:.2f}\n"
                f"💰 Current Balance: ${user['current_balance']:.2f}\n"
                f"🔁 Top-up: ${user['topup_amount']:.2f}\n"
            )

        else:
            response.message(
                "📘 *BudgetBuddy Help Guide*\n"
                "Commands:\n"
                "- setbudget 1000 → Set your starting monthly budget\n"
                "- topup 800 → Set the monthly top-up amount\n"
                "- addexpense 50 groceries → Add an expense with description\n"
                "- -120 rent → Quick expense entry with minus\n"
                "- history 5 → Show expenses from the last 5 days\n"
                "- status → Show your current budget status\n"
                "- clear → Reset all your budget data\n"
                "- share +1234567890 → Invite someone to share your budget\n"
                "- accept → Accept an invitation to join a shared budget\n"
                "- help → Show this help message\n"
            )

    except Exception as e:
        response.message(f"❌ There was an error processing your request: {str(e)}")

    finally:
        save_data()
        return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
