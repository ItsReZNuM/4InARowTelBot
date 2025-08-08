# handlers/callbacks.py
from telebot import types
from config import ADMIN_USER_IDS
from database import update_leaderboard, save_user
from game_logic import (
    game_states, create_board, create_board_markup, render_board, render_multi_board,
    drop_piece, check_winner, check_draw, bot_move, end_game_markup
)
from utils import is_message_valid, check_rate_limit
from config import logger
import sqlite3
from database import USER_DB
from time import sleep, time
import uuid

def register_callbacks(bot):

    # --- broadcast flow (admin) ---
    def send_broadcast(message):
        try:
            if not is_message_valid(message):
                return
            user_id = message.chat.id
            if user_id not in ADMIN_USER_IDS:
                bot.send_message(user_id, "فقط ادمین‌ها می‌تونن پیام همگانی ارسال کنن.")
                return
            try:
                with sqlite3.connect(USER_DB) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM users')
                    users = cursor.fetchall()
            except sqlite3.Error as e:
                logger.error(f"Error accessing users database for broadcast: {e}")
                bot.send_message(user_id, "خطا در دسترسی به دیتابیس.")
                return

            success_count = 0
            for u in users:
                try:
                    bot.send_message(u[0], message.text)
                    success_count += 1
                    sleep(0.5)
                except Exception:
                    continue
            bot.send_message(user_id, f"پیام به {success_count} کاربر ارسال شد 📢")
        except Exception as e:
            logger.error(f"Error in send_broadcast: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "broadcast")
    def handle_broadcast(call):
        try:
            user_id = call.from_user.id
            chat_id = call.message.chat.id if call.message else call.from_user.id
            if user_id not in ADMIN_USER_IDS:
                bot.answer_callback_query(call.id, "این قابلیت فقط برای ادمین‌ها در دسترسه! 😕")
                return
            bot.edit_message_text("هر پیامی که می‌خوای بنویس تا برای همه کاربران ارسال بشه 📢", chat_id, call.message.message_id)
            bot.register_next_step_handler_by_chat_id(chat_id, send_broadcast)
        except Exception as e:
            logger.error(f"Error in handle_broadcast: {e}")

    # --- invalid click (for non-top-row buttons) ---
    @bot.callback_query_handler(func=lambda call: call.data == "invalid_click")
    def handle_invalid_click(call):
        try:
            bot.answer_callback_query(call.id, "برای انداختن مهره، روی دکمه‌های ردیف اول ضربه بزنید! 😉")
        except Exception as e:
            logger.error(f"Error in handle_invalid_click: {e}")

    # --- start game (difficulty selection) ---
    @bot.callback_query_handler(func=lambda call: call.data == "start_game")
    def start_game(call):
        try:
            user_id = call.from_user.id
            allowed, err = check_rate_limit(user_id)
            if not allowed:
                bot.answer_callback_query(call.id, err)
                return
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("آسان 😊", callback_data="difficulty_easy"))
            markup.add(types.InlineKeyboardButton("متوسط 😎", callback_data="difficulty_medium"))
            markup.add(types.InlineKeyboardButton("سخت 😈", callback_data="difficulty_hard"))
            bot.edit_message_text("سطح سختی رو انتخاب کن: 🎯", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            logger.error(f"Error in start_game: {e}")

    @bot.callback_query_handler(func=lambda call: call.data in ["difficulty_easy", "difficulty_medium", "difficulty_hard"])
    def handle_difficulty_selection(call):
        try:
            user_id = call.from_user.id
            allowed, err = check_rate_limit(user_id)
            if not allowed:
                bot.answer_callback_query(call.id, err)
                return
            difficulty_map = {
                "difficulty_easy": "easy",
                "difficulty_medium": "medium",
                "difficulty_hard": "hard"
            }
            difficulty = difficulty_map[call.data]
            user_name = call.from_user.first_name
            game_states[user_id] = {
                "mode": "single",
                "board": create_board(),
                "turn": "player",
                "difficulty": difficulty,
                "user_name": user_name,
                "message_id": None,
                "chat_id": call.message.chat.id
            }
            update_single_board(bot, user_id)
        except Exception as e:
            logger.error(f"Error in handle_difficulty_selection: {e}")

    # --- handle single-player move callbacks and surrender ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("move_") or call.data == "surrender" or call.data.startswith("surrender_"))
    def handle_single_move(call):
        try:
            user_id = call.from_user.id
            if user_id not in game_states or game_states[user_id]["mode"] != "single":
                bot.answer_callback_query(call.id, "بازی فعالی وجود نداره! /start رو بزن.")
                return
            state = game_states[user_id]

            # surrender flow
            if call.data == "surrender":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("آره 😔", callback_data=f"surrender_yes_{user_id}"))
                markup.add(types.InlineKeyboardButton("نه، پشیمون شدم! 😅", callback_data=f"surrender_no_{user_id}"))
                bot.edit_message_text("مطمئنی می‌خوای تسلیم بشی؟ 🏳️", state["chat_id"], state["message_id"], reply_markup=markup)
                return

            if call.data.startswith("surrender_yes_"):
                bot.edit_message_text(f"تو تسلیم شدی! 🏳️", state["chat_id"], state["message_id"], reply_markup=end_game_markup())
                del game_states[user_id]
                return

            if call.data.startswith("surrender_no_"):
                update_single_board(bot, user_id)
                return

            # check turn
            if state["turn"] != "player":
                bot.answer_callback_query(call.id, "نوبتت نیست، صبر کن! ⏳")
                return

            allowed, err = check_rate_limit(user_id)
            if not allowed:
                bot.answer_callback_query(call.id, err)
                return

            col = int(call.data.split("_")[1])
            if state["board"][0][col] is not None:
                bot.answer_callback_query(call.id, "این ستون پره! یه ستون دیگه انتخاب کن. 😕")
                return

            row = drop_piece(state["board"], col, "player")
            if row is not None:
                if check_winner(state["board"], "player"):
                    points = {"easy": 1, "medium": 3, "hard": 10}[state["difficulty"]]
                    update_leaderboard(user_id, state["user_name"], points)
                    bot.edit_message_text(
                        f"تو برنده شدی! 🎉 {points} امتیاز گرفتی!",
                        state["chat_id"],
                        state["message_id"],
                        reply_markup=end_game_markup()
                    )
                    del game_states[user_id]
                    return

                if check_draw(state["board"]):
                    bot.edit_message_text(
                        f"بازی بدون برنده به پایان رسید! 🤝",
                        state["chat_id"],
                        state["message_id"],
                        reply_markup=end_game_markup()
                    )
                    del game_states[user_id]
                    return

                state["turn"] = "bot"
                update_single_board(bot, user_id)

                # bot move
                col = bot_move(state["board"], state["difficulty"])
                if col is not None:
                    drop_piece(state["board"], col, "bot")
                    state["turn"] = "player"
                    if check_winner(state["board"], "bot"):
                        bot.edit_message_text(
                            "ربات برنده شد! 😢",
                            state["chat_id"],
                            state["message_id"],
                            reply_markup=end_game_markup()
                        )
                        del game_states[user_id]
                        return

                    if check_draw(state["board"]):
                        bot.edit_message_text(
                            f"بازی بدون برنده به پایان رسید! 🤝",
                            state["chat_id"],
                            state["message_id"],
                            reply_markup=end_game_markup()
                        )
                        del game_states[user_id]
                        return

                    update_single_board(bot, user_id)
        except Exception as e:
            logger.error(f"Error in handle_single_move: {e}")

    # --- end game buttons (new_game / main_menu) ---
    @bot.callback_query_handler(func=lambda call: call.data in ["new_game", "main_menu"])
    def handle_end_game(call):
        try:
            user_id = call.from_user.id
            if call.data == "new_game":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("آسون 😊 (همینجوری الکی فقط مهره میندازه)", callback_data="difficulty_easy"))
                markup.add(types.InlineKeyboardButton("متوسط 😎 (با استدلال های ساده بازی رو جلو میبره)", callback_data="difficulty_medium"))
                markup.add(types.InlineKeyboardButton("سخت 😈 (بردن این سختی ، کار هر کسی نیست)", callback_data="difficulty_hard"))
                bot.edit_message_text("سطح سختی رو انتخاب کن: 🎯", call.message.chat.id, call.message.message_id, reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("شروع بازی 🎲", callback_data="start_game"))
                if user_id in ADMIN_USER_IDS:
                    markup.add(types.InlineKeyboardButton("پیام همگانی 📢", callback_data="broadcast"))
                bot.edit_message_text("به منوی اصلی خوش اومدی! 🌟", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            logger.error(f"Error in handle_end_game: {e}")

    # --- inline handler start (for multiplayer prompt) ---
    @bot.inline_handler(lambda query: query.query == "")
    def inline_query(query):
        try:
            user_id = query.from_user.id
            # check user in DB
            with sqlite3.connect(USER_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()

            if not user:
                results = [
                    types.InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="ربات رو استارت نکردی ! برای جزئیات کلیک کن",
                        input_message_content=types.InputTextMessageContent("اول وارد ربات @Rez4InARowBot شو و دستور /start رو بزن تا به عنوان کاربر بازی شناخته بشی بعدش میتونی دو نفره هم بازی کنی 😊")
                    )
                ]
                bot.answer_inline_query(query.id, results, cache_time=1)
                return

            user_name = user[0]
            results = [
                types.InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="شروع بازی دو نفره 🎮",
                    input_message_content=types.InputTextMessageContent(
                        f"{user_name} می‌خواد یه بازی دو نفره ۴ در یک ردیف انجام بده، کی پایه‌ست؟ 😎"
                    ),
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("پایه‌م! 💪", callback_data=f"join_{user_id}")
                    )
                )
            ]
            bot.answer_inline_query(query.id, results, cache_time=0)
        except Exception as e:
            logger.error(f"Error in inline_query: {e}")
            results = [
                types.InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="خطا",
                    input_message_content=types.InputTextMessageContent(
                        "خطایی رخ داد. لطفاً دوباره امتحان کنید."
                    )
                )
            ]
            bot.answer_inline_query(query.id, results, cache_time=1)

    # --- join game (from inline) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("join_"))
    def join_game(call):
        try:
            challenger_id = int(call.data.split("_")[1])
            opponent_id = call.from_user.id

            if opponent_id == challenger_id:
                bot.answer_callback_query(call.id, "نمی‌تونی با خودت بازی کنی! 😅")
                return

            with sqlite3.connect(USER_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (challenger_id,))
                challenger = cursor.fetchone()
            if not challenger:
                bot.answer_callback_query(call.id, "کاربر شروع‌کننده پیدا نشد! لطفاً دوباره امتحان کن.")
                return

            with sqlite3.connect(USER_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (opponent_id,))
                opponent = cursor.fetchone()
            if not opponent:
                bot.answer_callback_query(call.id, "اول وارد ربات @Rez4InARowBot شو و دستور /start رو بزن تا به عنوان کاربر بازی شناخته بشی بعدش میتونی دو نفره هم بازی کنی 😊")
                return

            challenger_name = challenger[0]
            opponent_name = call.from_user.first_name

            if challenger_id not in game_states:
                game_states[challenger_id] = {
                    "mode": "multi",
                    "board": create_board(),
                    "turn": "player1",
                    "player1_id": challenger_id,
                    "player2_id": opponent_id,
                    "player1_name": challenger_name,
                    "player2_name": opponent_name,
                    "time_left": 10,
                    "last_move_time": time(),
                    "message_id": None if call.message is None else call.message.message_id,
                    "chat_id": None if call.message is None else call.message.chat.id,
                    "inline_message_id": call.inline_message_id if call.message is None else None,
                    "rematch": []
                }
                bot.answer_callback_query(call.id, "بازی شروع شد! 🎮")
                update_multi_board(bot, challenger_id)
        except Exception as e:
            logger.error(f"Error in join_game: {e}")
            bot.answer_callback_query(call.id, "خطایی رخ داد. لطفاً دوباره امتحان کنید.")

    # --- multiplayer move handlers (and surrender) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("multi_move_") or call.data == "multi_surrender" or call.data.startswith("multi_surrender_"))
    def handle_multi_move(call):
        try:
            user_id = call.from_user.id
            # find challenger game
            challenger_id = None
            for c_id, st in game_states.items():
                if st.get("mode") == "multi" and (st.get("player1_id") == user_id or st.get("player2_id") == user_id):
                    challenger_id = c_id
                    break

            if not challenger_id:
                bot.answer_callback_query(call.id, "تو داخل بازی نیستی دوست عزیز ")
                return

            state = game_states[challenger_id]

            # surrender
            if call.data == "multi_surrender":
                winner_name = state["player2_name"] if state["player1_id"] == user_id else state["player1_name"]
                board_message = f"🏳️ {call.from_user.first_name} تسلیم شد!\n\nبرنده: {winner_name} 🎉"
                try:
                    if state.get("chat_id") and state.get("message_id"):
                        bot.edit_message_text(board_message, state["chat_id"], state["message_id"], parse_mode="Markdown")
                    elif state.get("inline_message_id"):
                        bot.edit_message_text(board_message, inline_message_id=state["inline_message_id"], parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error ending game after surrender: {e}")
                del game_states[challenger_id]
                return

            # column index
            col = int(call.data.split("_")[2])

            if state["board"][0][col] is not None:
                bot.answer_callback_query(call.id, "این ستون پره! 😕")
                return

            # check turn
            if (state["turn"] == "player1" and state["player1_id"] != user_id) or \
               (state["turn"] == "player2" and state["player2_id"] != user_id):
                bot.answer_callback_query(call.id, "الان نوبتت نیست! ⏳")
                return

            player_symbol = "player1" if state["turn"] == "player1" else "player2"
            drop_piece(state["board"], col, player_symbol)

            # check winner
            if check_winner(state["board"], player_symbol):
                winner_name = state["player1_name"] if state["turn"] == "player1'".replace("'", "") else None
                # above line in original had simpler logic; we'll compute winner properly:
                winner_name = state["player1_name"] if state["turn"] == "player1" else state["player2_name"]
                winner_id = state["player1_id"] if state["turn"] == "player1" else state["player2_id"]
                update_leaderboard(winner_id, winner_name, 2)

                board_message = f"🎉 {winner_name} برنده شد!\n\n{render_multi_board(state['board'])}"
                rematch_markup = types.InlineKeyboardMarkup()
                rematch_markup.add(types.InlineKeyboardButton("بازی مجدد 🎮", callback_data=f"rematch_{challenger_id}"))

                try:
                    if state.get("chat_id") and state.get("message_id"):
                        bot.edit_message_text(board_message, state["chat_id"], state["message_id"], reply_markup=rematch_markup, parse_mode="Markdown")
                    elif state.get("inline_message_id"):
                        bot.edit_message_text(board_message, inline_message_id=state["inline_message_id"], reply_markup=rematch_markup, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error ending game after win: {e}")

                del game_states[challenger_id]
                return

            # check draw
            if check_draw(state["board"]):
                board_message = f"بازی بدون برنده به پایان رسید! 🤝\n\n{render_multi_board(state['board'])}"
                rematch_markup = types.InlineKeyboardMarkup()
                rematch_markup.add(types.InlineKeyboardButton("بازی مجدد 🎮", callback_data=f"rematch_{challenger_id}"))
                try:
                    if state.get("chat_id") and state.get("message_id"):
                        bot.edit_message_text(board_message, state["chat_id"], state["message_id"], reply_markup=rematch_markup, parse_mode="Markdown")
                    elif state.get("inline_message_id"):
                        bot.edit_message_text(board_message, inline_message_id=state["inline_message_id"], reply_markup=rematch_markup, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error ending game after draw: {e}")
                del game_states[challenger_id]
                return

            # switch turn
            state["turn"] = "player2" if state["turn"] == "player1" else "player1"
            state["last_move_time"] = time()

            update_multi_board(bot, challenger_id)
        except Exception as e:
            logger.error(f"Error in handle_multi_move: {e}")

    # --- rematch handler ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("rematch_"))
    def handle_rematch(call):
        try:
            user_id = call.from_user.id
            chat_id = call.message.chat.id if call.message else None
            for state in list(game_states.values()):
                if state["mode"] == "multi" and (state["player1_id"] == user_id or state["player2_id"] == user_id):
                    if user_id not in state["rematch"]:
                        state["rematch"].append(user_id)
                        bot.answer_callback_query(call.id, "منتظر موافقت حریفت هستیم! ⏳")
                        if len(state["rematch"]) == 2:
                            # both agreed -> create new game
                            game_states[state["player1_id"]] = {
                                "mode": "multi",
                                "board": create_board(),
                                "turn": "player1",
                                "player1_id": state["player1_id"],
                                "player2_id": state["player2_id"],
                                "player1_name": state["player1_name"],
                                "player2_name": state["player2_name"],
                                "time_left": 10,
                                "last_move_time": time(),
                                "message_id": None,
                                "chat_id": chat_id,
                                "rematch": []
                            }
                            update_multi_board(bot, state["player1_id"])
                    break
            else:
                bot.answer_callback_query(call.id, "بازی جدیدی شروع کن! 🎮")
        except Exception as e:
            logger.error(f"Error in handle_rematch: {e}")

    # --- update functions (these interact with the bot directly) ---
    def update_single_board(bot, user_id):
        try:
            if user_id not in game_states or game_states[user_id]["mode"] != "single":
                return
            state = game_states[user_id]
            board = state["board"]
            user_name = state["user_name"]
            turn = "کاربر" if state["turn"] == "player" else "ربات"

            board_message = f"🔵 {user_name}\n🔴 ربات\nنوبت: {turn}\n\nحواست باشه که خود ردیف اول رو هم میتونی مهره بزاری  !!!\n\nو این نکته رو هم در نظر بگیر که سختی بازی رو هر چقدر که بیشتر بکنی بیشتر طول میکشه که ربات بازی رو تحلیل کنه ، پس یکم صبور باش  ، ممکنه توی سختی آخر تا 20 ثانیه هم هر نوبت طول بکشه "
            markup = create_board_markup(board)
            markup.add(types.InlineKeyboardButton("تسلیم 🏳️", callback_data="surrender"))
            try:
                if state.get("message_id"):
                    bot.edit_message_text(board_message, state["chat_id"], state["message_id"], reply_markup=markup, parse_mode="Markdown")
                else:
                    state["message_id"] = bot.send_message(state["chat_id"], board_message, reply_markup=markup, parse_mode="Markdown").message_id
            except Exception as e:
                # on failure try sending fresh message (like original)
                try:
                    state["message_id"] = bot.send_message(state["chat_id"], board_message, reply_markup=markup, parse_mode="Markdown").message_id
                except Exception as ex:
                    logger.error(f"Error sending single board message: {ex}")
        except Exception as e:
            logger.error(f"Error in update_single_board: {e}")

    def update_multi_board(bot, challenger_id):
        try:
            if challenger_id not in game_states or game_states[challenger_id]["mode"] != "multi":
                return
            state = game_states[challenger_id]
            board = state["board"]
            time_left = max(0, 10 - int(time() - state["last_move_time"]))

            if time_left == 0:
                state["turn"] = "player2" if state["turn"] == "player1" else "player1"
                state["last_move_time"] = time()
                time_left = 10

            board_message = (
                f"🔵 {state['player1_name']}\n"
                f"🔴 {state['player2_name']}\n"
                f"نوبت: {state['player1_name'] if state['turn'] == 'player1' else state['player2_name']} ⏳ {time_left} ثانیه\n\n"
                f"{render_multi_board(board)}"
            )
            markup = create_board_markup(board, prefix="multi_move")
            markup.add(types.InlineKeyboardButton("تسلیم 🏳️", callback_data="multi_surrender"))

            try:
                if state.get("chat_id") and state.get("message_id"):
                    bot.edit_message_text(board_message, state["chat_id"], state["message_id"], reply_markup=markup, parse_mode="Markdown")
                elif state.get("inline_message_id"):
                    bot.edit_message_text(board_message, inline_message_id=state["inline_message_id"], reply_markup=markup, parse_mode="Markdown")
                else:
                    if state.get("chat_id"):
                        state["message_id"] = bot.send_message(state["chat_id"], board_message, reply_markup=markup, parse_mode="Markdown").message_id
                    elif state.get("inline_message_id"):
                        bot.edit_message_text(board_message, inline_message_id=state["inline_message_id"], reply_markup=markup, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error updating multiplayer board for challenger {challenger_id}: {e}")
        except Exception as e:
            logger.error(f"Error in update_multi_board: {e}")
