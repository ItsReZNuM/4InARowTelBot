# game_logic.py
import random
from telebot import types

# game_states will be used by handlers (mirrors original bot.py)
# structure per game_state matches original: single and multi
game_states = {}  # {user_id: {...}}

# ---------- board utilities ----------
def create_board():
    return [[None for _ in range(7)] for _ in range(7)]

def drop_piece(board, col, piece):
    for row in range(6, -1, -1):
        if board[row][col] is None:
            board[row][col] = piece
            return row
    return None

def check_winner(board, piece):
    # horizontal
    for row in range(7):
        for col in range(4):
            if all(board[row][col + i] == piece for i in range(4)):
                return True
    # vertical
    for row in range(4):
        for col in range(7):
            if all(board[row + i][col] == piece for i in range(4)):
                return True
    # diag positive
    for row in range(4):
        for col in range(4):
            if all(board[row + i][col + i] == piece for i in range(4)):
                return True
    # diag negative
    for row in range(3, 7):
        for col in range(4):
            if all(board[row - i][col + i] == piece for i in range(4)):
                return True
    return False

def check_draw(board):
    for row in board:
        if None in row:
            return False
    return True

def render_board(board):
    board_str = ""
    for row in board:
        board_str += "".join(["🔵" if cell == "player" else "🔴" if cell == "bot" else "⬜" for cell in row]) + "\n"
    return board_str

def render_multi_board(board):
    board_str = ""
    for row in board:
        board_str += "".join(["🔵" if cell == "player1" else "🔴" if cell == "player2" else "⬜" for cell in row]) + "\n"
    return board_str

def create_board_markup(board, prefix="move"):
    markup = types.InlineKeyboardMarkup(row_width=7)
    for row in range(7):
        row_buttons = []
        for col in range(7):
            emoji = "🔵" if board[row][col] in ["player", "player1"] else "🔴" if board[row][col] in ["bot", "player2"] else "⬜"
            if row == 0 and board[row][col] is None:
                row_buttons.append(types.InlineKeyboardButton("⬇️", callback_data=f"{prefix}_{col}"))
            else:
                row_buttons.append(types.InlineKeyboardButton(emoji, callback_data="invalid_click"))
        markup.add(*row_buttons)
    return markup

# ---------- bot AI ----------
def bot_move(board, difficulty):
    valid_moves = [col for col in range(7) if board[0][col] is None]
    if not valid_moves:
        return None
    if difficulty == "easy":
        return random.choice(valid_moves)
    elif difficulty == "medium":
        # try win
        for col in valid_moves:
            temp_board = [r[:] for r in board]
            row = drop_piece(temp_board, col, "bot")
            if row is not None and check_winner(temp_board, "bot"):
                return col
        # try block
        for col in valid_moves:
            temp_board = [r[:] for r in board]
            row = drop_piece(temp_board, col, "player")
            if row is not None and check_winner(temp_board, "player"):
                return col
        return random.choice(valid_moves)
    else:  # hard
        best_score = float('-inf')
        best_col = random.choice(valid_moves)
        for col in valid_moves:
            temp_board = [r[:] for r in board]
            row = drop_piece(temp_board, col, "bot")
            if row is not None:
                score = minimax(temp_board, 5, False)
                if score > best_score:
                    best_score = score
                    best_col = col
        return best_col

def minimax(board, depth, is_maximizing):
    if check_winner(board, "bot"):
        return 100
    if check_winner(board, "player"):
        return -100
    if depth == 0 or all(board[0][col] is not None for col in range(7)):
        return 0
    if is_maximizing:
        best_score = float('-inf')
        for col in range(7):
            if board[0][col] is None:
                temp = [r[:] for r in board]
                drop_piece(temp, col, "bot")
                score = minimax(temp, depth - 1, False)
                if score > best_score:
                    best_score = score
        return best_score
    else:
        best_score = float('inf')
        for col in range(7):
            if board[0][col] is None:
                temp = [r[:] for r in board]
                drop_piece(temp, col, "player")
                score = minimax(temp, depth - 1, True)
                if score < best_score:
                    best_score = score
        return best_score

def end_game_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("بازی جدید 🎲", callback_data="new_game"))
    markup.add(types.InlineKeyboardButton("برگشت به منوی اصلی 🏠", callback_data="main_menu"))
    return markup
