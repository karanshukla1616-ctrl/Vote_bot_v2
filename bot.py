import sqlite3
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# Bot Token aur Admin ID (Environment variables ya direct yahan daalein)
TOKEN = "8705214074:AAFF1RoexM4-Ux7PfiFkHaxPNI9Q4Y8SvQI"
ADMIN_ID = 8680144387  # Apna Telegram Numeric User ID yahan dalein

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE SETUP =================
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

# Votes table (Poll ID, User ID, Votes count)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS votes (
    poll_id TEXT,
    user_id INTEGER,
    username TEXT,
    vote_count INTEGER,
    PRIMARY KEY (poll_id, user_id)
)
"""
)
conn.commit()


# ================= 1. WELCOME MESSAGE FEATURE =================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
  for member in message.new_chat_members:
    if member.id == bot.get_me().id:
      bot.send_message(
          message.chat.id,
          "👋 **Shukriya mujhe is group/channel me add karne ke liye!**\n\nAb main yahan welcome messages aur baki features handle karunga.",
          parse_mode="Markdown",
      )
    else:
      name = member.first_name
      welcome_text = (
          f"🎉 **Welcome {name}!**\n\n"
          f"Hamare group me aapka swagat hai. Kripya rules ka palan karein."
      )
      markup = InlineKeyboardMarkup()
      markup.add(
          InlineKeyboardButton(
              "🔗 Hamara Channel", url="https://t.me/your_channel_link"
          )
      )
      bot.send_message(
          message.chat.id,
          welcome_text,
          reply_markup=markup,
          parse_mode="Markdown",
      )


# ================= 2. ADMIN INBOX & CHAT SYSTEM =================
@bot.message_handler(
    func=lambda message: message.chat.type == "private"
    and message.from_user.id != ADMIN_ID
)
def handle_user_messages(message):
  """Aam user jab bot ko personal message karega toh admin ke paas jayega"""
  user = message.from_user
  try:
    bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    bot.send_message(
        ADMIN_ID,
        f"👤 **New Message User Se:**\nNaam: {user.first_name}\nID: `{user.id}`\n\n*(Is message par reply karke aap user ko jawab de sakte hain)*",
        parse_mode="Markdown",
    )
    bot.reply_to(
        message, "📩 Aapka message admin ke paas bhej diya gaya hai!"
    )
  except Exception as e:
    print(f"Error: {e}")


@bot.message_handler(
    func=lambda message: message.chat.type == "private"
    and message.from_user.id == ADMIN_ID
)
def handle_admin_messages(message):
  """Admin jab kisi forwarded message ka reply karega toh user ko jayega"""
  if message.reply_to_message and message.reply_to_message.forward_from:
    user_id = message.reply_to_message.forward_from.id
    try:
      bot.send_message(user_id, f"💬 **Admin ka Jawab:**\n\n{message.text}")
      bot.reply_to(message, "✅ Message user tak pahunch gaya!")
    except Exception as e:
      bot.reply_to(message, f"❌ Error: {e}")
  else:
    # Commands ya normal admin texts ke liye help
    if message.text.startswith("/"):
      return
    bot.reply_to(
        message,
        "ℹ️ Kisi user ke forwarded message par reply karke hi jawab bhejein.\n\n"
        "🛠 **Admin Vote Control Commands:**\n"
        "• `/addvote <poll_id> <user_id> <count>` - Kisi ke votes badhane ke liye\n"
        "• `/leaderboard <poll_id>` - Vote list dekhne ke liye",
    )


# ================= 3. ADVANCED VOTE SYSTEM & ADMIN CONTROL =================


@bot.message_handler(commands=["vote"])
def start_voting(message):
  """User voting start karne ke liye ya vote dene ke liye"""
  args = message.text.split()
  if len(args) < 2:
    bot.reply_to(
        message,
        "⚠️ Sahi tareeqa use karein:\n`/vote <poll_id>`\nExample: `/vote contest1`",
        parse_mode="Markdown",
    )
    return

  poll_id = args[1]
  user = message.from_user

  # Check karein agar user pehle se hai toh vote count badhao, warna add karo
  cursor.execute(
      "SELECT vote_count FROM votes WHERE poll_id = ? AND user_id = ?",
      (poll_id, user.id),
  )
  result = cursor.fetchone()

  if result:
    new_count = result[0] + 1
    cursor.execute(
        "UPDATE votes SET vote_count = ? WHERE poll_id = ? AND user_id = ?",
        (new_count, poll_id, user.id),
    )
  else:
    cursor.execute(
        "INSERT INTO votes (poll_id, user_id, username, vote_count) VALUES"
        " (?, ?, ?, 1)",
        (poll_id, user.id, user.first_name),
    )

  conn.commit()
  bot.reply_to(
      message,
      f"✅ Aapka vote successfully darj ho gaya hai! (Poll ID: {poll_id})",
  )


@bot.message_handler(commands=["addvote"])
def admin_add_vote(message):
  """ADMIN COMMAND: Kisi bhi user ke votes manually badhane ke liye"""
  if message.from_user.id != ADMIN_ID:
    bot.reply_to(message, "❌ Yeh command sirf Admin ke liye hai!")
    return

  args = message.text.split()
  if len(args) < 4:
    bot.reply_to(
        message,
        "⚠️ **Galat Format!**\nUse karein: `/addvote <poll_id> <user_id>`"
        " `<kitne_votes_badhane_hain>`\nExample: `/addvote contest1 987654321"
        " 50`",
        parse_mode="Markdown",
    )
    return

  poll_id = args[1]
  try:
    target_user_id = int(args[2])
    extra_votes = int(args[3])
  except ValueError:
    bot.reply_to(message, "❌ User ID aur votes numbers me hone chahiye!")
    return

  # Database me check karein user hai ya nahi
  cursor.execute(
      "SELECT vote_count FROM votes WHERE poll_id = ? AND user_id = ?",
      (poll_id, target_user_id),
  )
  result = cursor.fetchone()

  if result:
    new_count = result[0] + extra_votes
    cursor.execute(
        "UPDATE votes SET vote_count = ? WHERE poll_id = ? AND user_id = ?",
        (new_count, poll_id, target_user_id),
    )
  else:
    cursor.execute(
        "INSERT INTO votes (poll_id, user_id, username, vote_count) VALUES"
        " (?, ?, 'Manual User', ?)",
        (poll_id, target_user_id, extra_votes),
    )

  conn.commit()
  bot.reply_to(
      message,
      f"✅ Successfully User `{target_user_id}` ke votes me `{extra_votes}`"
      f" add kar diye gaye hain!",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["leaderboard"])
def show_leaderboard(message):
  """Kisi bhi poll ka leaderboard dekhne ke liye"""
  args = message.text.split()
  if len(args) < 2:
    bot.reply_to(
        message,
        "⚠️ Use karein: `/leaderboard <poll_id>`",
        parse_mode="Markdown",
    )
    return

  poll_id = args[1]
  cursor.execute(
      "SELECT username, user_id, vote_count FROM votes WHERE poll_id = ? ORDER"
      " BY vote_count DESC LIMIT 10",
      (poll_id,),
  )
  rows = cursor.fetchall()

  if not rows:
    bot.reply_to(message, f"📭 Is Poll ID ({poll_id}) par abhi koi votes nahi hain.")
    return

  text = f"🏆 **Leaderboard (Poll: {poll_id})** 🏆\n\n"
  for i, row in enumerate(rows, 1):
    text += f"{i}. **{row[0]}** (ID: `{row[1]}`) — ⭐ **{row[2]} Votes**\n"

  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# ================= BOT START =================
if __name__ == "__main__":
  print("🤖 Bot GitHub deployment ke liye ready hai aur run ho raha hai...")
  bot.infinity_polling()
