from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from telegram.ext import MessageHandler, ConversationHandler, filters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import re, time, traceback
import json
import os

# SETTINGS
TOKEN = "7568694178:AAHMNPuAFCVP0DG2ONM1NsfWw4ZoWzOoBMc"  # Replace with your bot token
LOGIN_URL = "https://sport.shahroodut.ac.ir/SportLogin"
USER_DATA_FILE = "user_credentials.json"

# JSON handler utility
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)


# Global driver
driver = None

# === Login Function ===
def login(user_id):
    global driver
    data = load_user_data()
    creds = data.get(str(user_id))
    if not creds:
        return False

    USERNAME = creds["username"]
    PASSWORD = creds["password"]
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)

        driver.get(LOGIN_URL)
        time.sleep(2)

        driver.find_element(By.ID, "txtusv").send_keys(USERNAME)
        driver.find_element(By.ID, "passv").send_keys(PASSWORD)

        captcha_text = driver.find_element(By.ID, "lbcode").text
        match = re.findall(r'\d+|\+|\-', captcha_text)
        if len(match) == 3:
            num1 = int(match[0])
            operator = match[1]
            num2 = int(match[2])
            result = num1 + num2 if operator == '+' else num1 - num2
            driver.find_element(By.ID, "txtcode").send_keys(str(result))
        else:
            print("❌ CAPTCHA parse failed.")
            return False

        driver.find_element(By.ID, "btlogin").click()
        time.sleep(3)
        return True

    except Exception as e:
        traceback.print_exc()
        return False





# === Telegram Commands ===

SET_USERNAME, SET_PASSWORD = range(2)

async def login_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_user_data()

    if user_id in data:
        username = data[user_id]["username"]
        password_length = len(data[user_id]["password"])
        await update.message.reply_text(
            f"🧾 <b>Saved Login Info:</b>\n"
            f"👤 Username: <code>{username}</code>\n"
            f"🔐 Password: {'•' * password_length}\n"
            f"(Stored securely on bot)",
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("🧑‍💻 Please enter your username:")
        return SET_USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["username"] = update.message.text
    await update.message.reply_text("🔐 Now enter your password:")
    return SET_PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = context.user_data.get("username")
    password = update.message.text

    data = load_user_data()
    data[user_id] = {"username": username, "password": password}
    save_user_data(data)

    await update.message.reply_text("✅ Credentials saved. Use /login to log in.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Canceled.")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("login_info", login_info)],
    states={
        SET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
        SET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[],
)

# -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.full_name
    await update.message.reply_text(f"👋 Welcome to reSUT, {name}.\nUse /login to start.")

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) in load_user_data():
        await update.message.reply_text("🔐 Trying to log in...")
        user_id = update.effective_user.id
    else:
        print("You have to complete your information first.")
        return await login_info(update, context)

    def wrapped_login():
        return login(user_id)  # pass context so it grabs username/password

    success = await context.application.run_in_threadpool(wrapped_login)
    if success:
        await update.message.reply_text("✅ Logged in successfully.")
    else:
        await update.message.reply_text("❌ Login failed. Check credentials or site status.")


# === Bot Setup ===

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("login", login_command))
app.add_handler(conv_handler)


print("🤖 reSUT_minibot is running...")
app.run_polling()
