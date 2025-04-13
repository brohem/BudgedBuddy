
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

@app.route("/bot", methods=["POST"])
def bot():
    user_id = request.form["From"]
    msg = request.form["Body"].strip().lower()
    # Normalize command by removing leading slash if present
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

    # Monthly top-up logic

    # Handle quick expense with -amount
    if msg.startswith("-"):
        try:
            parts = msg.split()
            amount = float(parts[0])
            description = " ".join(parts[1:]) if len(parts) > 1 else "Quick entry"
            user["current_balance"] += amount  # amount is negative
            user["expenses"].append({
                "amount": abs(amount),
                "desc": description,
                "date": now.isoformat()
            })
            response.message(f"💸 {description} - ${abs(amount):.2f} added. Remaining: ${user['current_balance']:.2f}")
            save_data()
    if user["current_balance"] < 0:

        if user["current_balance"] < 0:
            response.message(f"⚠️ Warning: Your balance is negative (${user['current_balance']:.2f}). Please review your spending.")
            return str(response)
        except:
            response.message("❌ Couldn't process the amount. Use -100 groceries to log an expense.")
            save_data()
    if user["current_balance"] < 0:

            return str(response)

        except:
            response.message("❌ Couldn't process the amount. Use -100 to log an expense.")
            save_data()
    if user["current_balance"] < 0:

            return str(response)

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
        if user["current_balance"] < 0:
            response.message(f"⚠️ Warning: Your balance is negative (${user['current_balance']:.2f}). Please review your spending.")
    if user["current_balance"] < 0:

        except:
            response.message("❌ Usage: /addexpense 50 groceries")
    elif msg.startswith("topup"):
        try:
            amount = float(msg.split()[1])
            user["topup_amount"] = amount
            response.message(f"🔄 Top-up amount set to ${amount:.2f}")
        except:
            response.message("❌ Usage: /topup 1000")
    
    elif msg.startswith("clear"):
        if user_id in users:
            users[user_id] = {
                "monthly_allocation": 0,
                "current_balance": 0,
                "topup_amount": 0,
                "last_topup": None,
                "expenses": []
            }
            response.message("🧹 All your budget data has been cleared.")
        else:
            response.message("ℹ️ No data found to clear.")

    elif msg.startswith("history"):
        try:
            parts = msg.split()
            days = int(parts[1]) if len(parts) > 1 else 7
            cutoff = (now - timedelta(days=days)).isoformat()
            history = [e for e in user["expenses"] if e["date"] >= cutoff]
            if history:
                lines = [f"{e['date']}: ${e['amount']:.2f} - {e['desc']}" for e in history]
                response.message("📜 Expense History:\n" + "\n".join(lines))
            else:
                response.message("📭 No expenses recorded in the selected period.")
        except:
            response.message("❌ Usage: history 5")

    
    elif msg in ["hi budgetbuddy", "hello budgetbuddy"]:
        response.message(
            "BudgetBuddy: A Personal Finance Tool for Everyone\n"
            "👋 Welcome! I’d love to introduce you to BudgetBuddy — a simple, free, and private WhatsApp-based assistant designed to help people manage their money better.\n\n"
            "💡 What is BudgetBuddy?\n"
            "BudgetBuddy is a lightweight chatbot you can message on WhatsApp to:\n"
            "- Set a monthly budget 💰\n"
            "- Log daily expenses 💸\n"
            "- Track your remaining funds in real-time 📊\n"
            "- Stay financially aware and in control — without needing apps or spreadsheets\n"
            "It works entirely through WhatsApp, making it easy and accessible for anyone.\n\n"
            "🧠 Why I Built It:\n"
            "As someone who values simple tools and financial wellness, I created BudgetBuddy to:\n"
            "- Encourage healthy money habits\n"
            "- Help friends and family track their spending\n"
            "- Provide an alternative to complex finance apps\n\n"
            "This is a personal project, built and maintained by me, with no commercial interest or monetization involved.\n\n"
            "🙌 Non-Profit Educational Intent\n"
            "BudgetBuddy is:\n"
            "✅ 100% free to use\n"
            "✅ Not affiliated with any business or product\n"
            "✅ Built for personal, family, and educational purposes only\n"
            "❌ Not collecting or selling any data\n"
            "❌ Not sending promotional or unsolicited messages\n\n"
            "This project was born out of passion for tech and financial literacy — and it’s here to help anyone who finds it useful.\n\n"
            "👉 Send 'help' into the chat to see available commands."
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
            "Manage your budget easily via WhatsApp commands.\n\n"
            "🔧 *Commands:*\n"
            "• setbudget [amount] – Set your monthly budget.\n"
            "• topup [amount] – Adjust your monthly top-up amount.\n"
            "• addexpense [amount] [description] – Log a new expense.\n"
            "• -[amount] [description] – Quick expense entry (description optional).\n"
            "• status – Show current budget, balance, and top-up.\n"
            "• history [days] – View expense history for past [days] (default: 7).\n"
            "• clear – Reset all saved data.\n"
            "• help – Show this help message.\n\n"
            "💡 *Examples:*\n"
            "• setbudget 1000\n"
            "• topup 800\n"
            "• addexpense 50 groceries\n"
            "• -120 rent\n"
            "• history 5\n\n"
            "Need more help? Just type: help"
        )
    return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)



