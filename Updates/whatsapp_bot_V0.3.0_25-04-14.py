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
    user_id = request.form["From"]
    msg = request.form["Body"].strip().lower()
    if msg.startswith("/"):
        msg = msg[1:]

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

        elif msg.startswith("clear"):
            users[user_id] = {
                "monthly_allocation": 0,
                "current_balance": 0,
                "topup_amount": 0,
                "last_topup": None,
                "expenses": []
            }
            response.message("🧹 All your budget data has been cleared.")

        elif msg.startswith("history"):
            parts = msg.split()
            days = int(parts[1]) if len(parts) > 1 else 7
            cutoff = (now - timedelta(days=days)).isoformat()
            history = [e for e in user["expenses"] if e["date"] >= cutoff]
            if history:
                lines = [f"{e['date']}: ${e['amount']:.2f} - {e['desc']}" for e in history]
                response.message("📜 Expense History:\n" + "\n".join(lines))
            else:
                response.message("📭 No expenses recorded in the selected period.")

        elif msg in ["hi budgetbuddy", "hello budgetbuddy", "hi"]:
            response.message(
                "BudgetBuddy: A Personal Finance Tool for Everyone\n"
                "👋 Welcome! I’d love to introduce you to BudgetBuddy — a simple, free, and private WhatsApp-based assistant designed to help people manage their money better.\n\n"
                "💡 What is BudgetBuddy?\n"
                "- Set a monthly budget 💰\n"
                "- Log daily expenses 💸\n"
                "- Track your remaining funds in real-time 📊\n"
                "- Stay financially aware and in control — without apps or spreadsheets\n\n"
                "🙌 100% free. No data collection. No ads. Just helpful."
            )

        elif msg.startswith("status"):
            response.message(
                f"💼 Budget: ${user['monthly_allocation']:.2f}\n"
                f"💰 Current Balance: ${user['current_balance']:.2f}\n"
                f"🔁 Top-up: ${user['topup_amount']:.2f}"
            )

        else:
            response.message(
                "📘 *BudgetBuddy Help Guide*\n"
                "Commands:\n"
                "- setbudget 1000\n"
                "- topup 800\n"
                "- addexpense 50 groceries\n"
                "- -120 rent\n"
                "- history 5\n"
                "- status\n"
                "- clear\n"
                "- help"
            )

    except:
        response.message("❌ There was an error processing your request.")
    finally:
        save_data()
        return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
