
from PySide6.QtCore import QObject, Qt, QRunnable, Slot, QThreadPool, Signal
from PySide6.QtGui import QIcon, QAction, QIntValidator
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtWidgets import QWidget, QGridLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox, QFrame
from random import randint, shuffle

try:
    from ctypes import windll
    windll.shell32.SetCurrentProcessExplicitAppUserModelID("Qionglu735.MineSweeperBot.1.0")
except ImportError:
    windll = None

import datetime
import itertools
import os
import sys
import time
import webbrowser

PRESET = [
    (9, 9, 10, ),  # Easy, 12.35%
    (16, 16, 40, ),  # Moderate, 15.62%
    (30, 16, 99, ),  # Hard, 20.62%
]

FIELD_PRESET = [
    (10, 10, "Small", ),
    (20, 20, "Medium", ),
    (40, 20, "Large", ),
    (60, 30, "Huge", ),
    (80, 40, "Expansive", ),
    (100, 50, "Enormous", ),
]

DIFFICULTY_PRESET = [
    (0.10, "Simple", ),
    (0.12, "Easy", ),
    (0.14, "Moderate", ),
    (0.16, "Manageable", ),
    (0.18, "Challenging", ),
    (0.20, "Hard", ),
    (0.22, "Extreme", ),
    (0.24, "Impossible", ),
]

MIN_WIDTH = 9
MAX_WIDTH = 1000

MIN_HEIGHT = 3
MAX_HEIGHT = 1000

SYMBOL_BLANK = " "
SYMBOL_MINE = "X"
SYMBOL_FLAG = "!"
SYMBOL_UNKNOWN = "?"

BUTTON_SIZE = 20


class Land(QPushButton):
    x = 0
    y = 0
    id = 0
    cover = SYMBOL_BLANK
    content = SYMBOL_BLANK
    have_mine = False
    adjacent_mine_count = 0
    checked = False
    style_sheet = """
        QPushButton {
            color: FONT_COLOR;
            font: "Roman Times";
            font-size: 10;
            font-weight: bold;
            background-color: #292929;
        }
        QPushButton:pressed {
            border: 2px solid #a0a020;
        }
        QPushButton:checked {
            background-color: #232323;
        }
    """
    focus_style_sheet = """
        QPushButton {
            color: FONT_COLOR;
            font: "Roman Times";
            font-size: 10;
            font-weight: bold;
            border: 2px solid #a0a020;
            background-color: #434343;
        }
        QPushButton:pressed {
            border: 2px solid #a0a020;
        }
        QPushButton:checked {
            background-color: #232323;
        }
    """
    danger_style_sheet = """
        QPushButton {
            color: FONT_COLOR;
            font: "Roman Times";
            font-size: 10;
            font-weight: bold;
            border: 2px solid #a02020;
            background-color: #434343;
        }
        QPushButton:pressed {
            border: 2px solid #a0a020;
        }
        QPushButton:checked {
            background-color: #232323;
        }
    """
    safe_style_sheet = """
        QPushButton {
            color: FONT_COLOR;
            font: "Roman Times";
            font-size: 10;
            font-weight: bold;
            border: 2px solid #20a020;
            background-color: #434343;
        }
        QPushButton:pressed {
            border: 2px solid #a0a020;
        }
        QPushButton:checked {
            background-color: #232323;
        }
    """

    def __init__(self, parent, x, y):
        super().__init__(parent, text=SYMBOL_BLANK)

        self.x, self.y = x, y
        self.id = x + parent.field_width * y

        # UI
        self.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.setStyleSheet(self.style_sheet.replace("FONT_COLOR", "white"))
        self.setCheckable(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.update_tooltip()

    def left_click(self, chain=False):
        mine_field = self.parent()
        field_width = self.parent().field_width
        field_height = self.parent().field_height

        if MainWindow().game_terminated or not MainWindow().game_terminated and self.cover != SYMBOL_BLANK:
            # prevent changing check status
            self.setChecked(self.checked)
            return

        self.checked = True
        # if not chain:
        #     print(f"Click ({self.x}, {self.y})")
        if len([x for x in mine_field.land_list if x.have_mine is True]) == 0:
            # first click always safe
            mine_field.generate_mine(self.x, self.y)

        self.parent().check_end_game(self.x, self.y)
        if not MainWindow().game_terminated:
            flag_num = 0
            for x, y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                if x == 0 and y == 0:
                    continue
                if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                    land = self.parent().land_list[(self.x + x) + field_width * (self.y + y)]
                    if not land.checked and land.cover == SYMBOL_FLAG:
                        flag_num += 1
            if flag_num == self.adjacent_mine_count:
                for x, y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                    if x == 0 and y == 0:
                        continue
                    if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                        land = self.parent().land_list[(self.x + x) + field_width * (self.y + y)]
                        if not land.checked and land.cover == SYMBOL_BLANK:
                            land.left_click(chain=True)
        if not chain:
            self.parent().check_end_game(self.x, self.y)
            self.update_ui(focus=True)

        if not MainWindow().game_terminated:
            MainWindow().set_message(f"{mine_field.mine_count - mine_field.marked_land_count()} mines remained")

    def auto_click(self):
        # print(f"Auto Click")
        self.left_click()

    def right_click(self):
        if not MainWindow().game_terminated:
            # print(f"Mark  ({self.x}, {self.y})")
            if not self.checked:
                if self.cover == SYMBOL_BLANK:
                    self.cover = SYMBOL_FLAG
                elif self.cover == SYMBOL_FLAG:
                    self.cover = SYMBOL_UNKNOWN
                elif self.cover == SYMBOL_UNKNOWN:
                    self.cover = SYMBOL_BLANK
            mine_field = self.parent()
            MainWindow().set_message(f"{mine_field.mine_count - mine_field.marked_land_count()} mines remained")
        self.update_ui(focus=True)

    def auto_mark(self):
        # print(f"Auto Mark")
        while not MainWindow().game_terminated and self.cover != SYMBOL_FLAG:
            self.right_click()

    def update_tooltip(self, cheat_mode=False):
        mine_field = self.parent()
        if self.have_mine and cheat_mode:
            self.setToolTip(f"! ({self.x + 1}, {self.y + 1}) {self.x + mine_field.field_width * self.y + 1} !")
        else:
            self.setToolTip(f"({self.x + 1}, {self.y + 1}) {self.x + mine_field.field_width * self.y + 1}")

    def update_ui(self, focus=False):
        style_sheet = self.focus_style_sheet if focus else self.style_sheet
        self.setChecked(self.checked)
        if self.checked:
            self.setText(self.content)
            color_dict = {
                " ": "white",
                "X": "red",
                "1": "#8080f0",
                "2": "#80f080",
                "3": "#f08080",
                "4": "#4040f0",
                "5": "#a0a040",
                "6": "#40a040",
                "7": "#000000",
                "8": "#404040",
            }
            style_sheet = style_sheet.replace("FONT_COLOR", color_dict[self.content])
        else:
            self.setText(self.cover)
            color_dict = {
                " ": "white",
                "X": "red",
                "!": "#f02020",
                "?": "#2020f0",
            }
            style_sheet = style_sheet.replace("FONT_COLOR", color_dict[self.cover])

        self.setStyleSheet(style_sheet)

        if focus:
            for land in self.parent().land_list:
                if land == self:
                    continue
                land.update_ui()

    def to_string(self):
        return f"{self.id} ({self.x}, {self.y})"

    def highlight(self, _type):
        if _type == "danger":
            style_sheet = self.danger_style_sheet
        elif _type == "safe":
            style_sheet = self.safe_style_sheet
        else:
            style_sheet = self.style_sheet
        color_dict = {
            " ": "white",
            "X": "red",
            "!": "#f02020",
            "?": "#2020f0",
        }
        style_sheet = style_sheet.replace("FONT_COLOR", color_dict[self.cover])
        self.setStyleSheet(style_sheet)


class MineField(QWidget):
    field_width = 0
    field_height = 0
    mine_count = 0

    land_list = list()

    def __init__(self, parent, field_width=PRESET[0][0], field_height=PRESET[0][1], mine_count=PRESET[0][2]):
        super().__init__(parent)
        self.field_width = min(max(MIN_WIDTH, field_width), MAX_WIDTH)
        self.field_height = min(max(MIN_HEIGHT, field_height), MAX_HEIGHT)
        self.mine_count = min(max(1, mine_count), (self.field_width - 1) * (self.field_height - 1))
        self.init_mine_field()

    def init_mine_field(self):
        grid = QGridLayout()
        grid.setSpacing(0)

        self.land_list = list()
        for y in range(self.field_height):
            for x in range(self.field_width):
                land = Land(self, x, y)
                land.clicked.connect(self.left_click)
                land.customContextMenuRequested.connect(self.right_click)
                grid.addWidget(land, y, x)

                self.land_list.append(land)

        self.setLayout(grid)

        self.parent().setFixedWidth(20 + self.field_width * BUTTON_SIZE)
        self.parent().setFixedHeight(61 + self.field_height * BUTTON_SIZE)

    def reset_mine_field(self):
        for land in self.land_list:
            land.cover = SYMBOL_BLANK
            land.checked = False
            land.update_ui()

    def generate_mine(self, safe_x=-9, safe_y=-9):
        for x in range(self.field_width):
            for y in range(self.field_height):
                self.land_list[x + self.field_width * y].have_mine = False
                self.land_list[x + self.field_width * y].adjacent_mine_count = 0
                self.land_list[x + self.field_width * y].checked = False
                self.land_list[x + self.field_width * y].cover = SYMBOL_BLANK
                self.land_list[x + self.field_width * y].content = SYMBOL_BLANK

                self.land_list[x + self.field_width * y].update_ui()

        for _ in range(self.mine_count):
            x, y = -1, -1
            while x < 0 or y < 0 or self.land_list[x + self.field_width * y].have_mine:
                x = randint(0, self.field_width - 1)
                y = randint(0, self.field_height - 1)
                if abs(x - safe_x) <= 1 and abs(y - safe_y) <= 1:
                    x, y = -1, -1
            self.land_list[x + self.field_width * y].have_mine = True
            for _x, _y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                if _x == 0 and _y == 0:
                    continue
                if 0 <= (x + _x) < self.field_width and 0 <= (y + _y) < self.field_height:
                    self.land_list[(x + _x) + self.field_width * (y + _y)].adjacent_mine_count += 1

        for y in range(self.field_height):
            for x in range(self.field_width):
                land = self.land_list[x + self.field_width * y]
                if land.have_mine:
                    land.content = SYMBOL_MINE
                elif land.adjacent_mine_count == 0:
                    land.content = SYMBOL_BLANK
                else:
                    land.content = f"{land.adjacent_mine_count}"

    def field_size(self):
        return {
            "field_width": self.field_width,
            "field_height": self.field_height,
            "mine_count": self.mine_count,
        }

    def revealed_land_count(self):
        return len([x for x in self.land_list if x.checked])

    def marked_land_count(self):
        return len([x for x in self.land_list if not x.checked and x.cover == SYMBOL_FLAG])

    def check_end_game(self, x, y):
        if self.land_list[x + self.field_width * y].have_mine:
            MainWindow().game_terminated = True
            MainWindow().game_result = "LOSE"
            self.parent().set_message("YOU LOSE")
            for land in self.land_list:
                if land.have_mine:
                    land.cover = SYMBOL_MINE
                    land.update_ui()
        elif self.revealed_land_count() == self.field_width * self.field_height - self.mine_count:
            MainWindow().game_terminated = True
            MainWindow().game_result = "WIN"
            self.parent().set_message("YOU WIN")
            for y in range(self.field_height):
                for x in range(self.field_width):
                    if self.land_list[x + self.field_width * y].have_mine:
                        self.land_list[x + self.field_width * y].cover = SYMBOL_FLAG
                        self.land_list[x + self.field_width * y].update_ui()

    def left_click(self):
        self.sender().left_click()

    def right_click(self):
        self.sender().right_click()


def singleton(cls):
    instances = dict()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


class NumberLineEdit(QLineEdit):

    def wheelEvent(self, event):
        current_value = int(self.text()) if self.text().isdigit() else 0
        delta = event.angleDelta().y()
        if delta > 0:
            current_value += 1
        else:
            current_value -= 1
        self.setText(str(current_value))


class CustomFieldDialog(QDialog):
    width, height, mine = PRESET[0]

    mine_validator = None
    width_edit = None
    height_edit = None
    preset_combo = None
    preset_combo_change = False
    mine_edit = None
    difficulty_label = "10%"

    def __init__(self, parent, width, height, mine):
        super().__init__(parent)

        self.width = width
        self.height = height
        self.mine = mine

        self.setWindowTitle("Custom Mine Field")

        width_validator = QIntValidator()
        width_validator.setRange(MIN_WIDTH, MAX_WIDTH)

        height_validator = QIntValidator()
        height_validator.setRange(MIN_HEIGHT, MAX_HEIGHT)

        self.mine_validator = QIntValidator()

        self.width_edit = NumberLineEdit()
        self.width_edit.setText(str(self.width))
        self.width_edit.setValidator(width_validator)
        self.width_edit.textChanged.connect(self.width_change)

        self.height_edit = NumberLineEdit()
        self.height_edit.setText(str(self.height))
        self.height_edit.setValidator(height_validator)
        self.height_edit.textChanged.connect(self.height_change)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([x[1] for x in DIFFICULTY_PRESET])
        self.preset_combo.currentIndexChanged.connect(self.preset_change)

        self.mine_edit = NumberLineEdit()
        self.mine_edit.setText(str(self.mine))
        self.mine_edit.setValidator(self.mine_validator)
        self.mine_edit.textChanged.connect(self.mine_change)

        self.difficulty_label = QLabel()

        self.update_variable()
        self.update_combo()

        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.confirm)

        grid = QGridLayout()

        grid.addWidget(QLabel("Width:"), 1, 1)
        grid.addWidget(self.width_edit, 1, 2)

        grid.addWidget(QLabel("Height:"), 2, 1)
        grid.addWidget(self.height_edit, 2, 2)

        grid.addWidget(QLabel("Difficulty Preset:"), 3, 1)
        grid.addWidget(self.preset_combo, 3, 2)

        grid.addWidget(QLabel("Mines:"), 4, 1)
        grid.addWidget(self.mine_edit, 4, 2)

        grid.addWidget(QLabel("Difficulty:"), 5, 1)
        grid.addWidget(self.difficulty_label, 5, 2)

        grid.addWidget(confirm, 6, 1, 1, 2)

        self.setLayout(grid)

    def width_change(self, text):
        if self.width_edit.hasAcceptableInput():
            self.width = int(text)
            self.update_variable()
            self.preset_combo_change = False
            self.update_combo()
        else:
            self.width_edit.setText(str(self.width))

    def height_change(self, text):
        if self.height_edit.hasAcceptableInput():
            self.height = int(text)
            self.preset_combo_change = False
            self.update_variable()
            self.update_combo()
        else:
            self.height_edit.setText(str(self.height))

    def preset_change(self, index):
        if self.preset_combo_change:
            mine = max(1, int(self.width * self.height * DIFFICULTY_PRESET[index][0]))
            self.mine_edit.setText(str(mine))

    def mine_change(self, text):
        if self.mine_edit.hasAcceptableInput():
            self.mine = int(text)
            self.update_variable()
            self.preset_combo_change = False
            self.update_combo()
        else:
            self.mine_edit.setText(str(self.mine))

    def update_variable(self):
        self.mine_validator.setRange(1, (self.width - 1) * (self.height - 1))
        difficulty = self.mine / (self.width * self.height)
        self.difficulty_label.setText(f"{difficulty * 100:.2f}%")

    def update_combo(self):
        difficulty = self.mine / (self.width * self.height)
        for i, preset in reversed(list(enumerate(DIFFICULTY_PRESET))):
            if preset[0] > difficulty:
                continue
            self.preset_combo.setCurrentIndex(i)
            break
        self.preset_combo_change = True

    def confirm(self):
        self.parent().init_mine_field(self.width, self.height, self.mine)
        self.done(0)


class StatisticDialog(QDialog):

    total_count = None
    win_count, win_rate = None, None
    lose_count, lose_rate = None, None
    click_count, click_rate = None, None
    mark_count, mark_rate = None, None
    guess_count, guess_rate = None, None
    usage_time_avg = None
    cur_click_count, cur_click_rate = None, None
    cur_mark_count, cur_mark_rate = None, None
    cur_guess_count, cur_guess_rate  = None, None
    cur_usage_time = None
    cur_result = None

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Bot Statistic")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "Mine.ico")))
        self.setFixedSize(190, 300)

        self.total_count = QLabel("0")
        self.win_count, self.win_rate = QLabel("0"), QLabel("0")
        self.lose_count, self.lose_rate = QLabel("0"), QLabel("0")
        self.click_count, self.click_rate = QLabel("0"), QLabel("0")
        self.mark_count, self.mark_rate = QLabel("0"), QLabel("0")
        self.guess_count, self.guess_rate = QLabel("0"), QLabel("0")
        self.usage_time_avg = QLabel("0")
        self.cur_click_count, self.cur_click_rate = QLabel("0"), QLabel("0")
        self.cur_mark_count, self.cur_mark_rate = QLabel("0"), QLabel("0")
        self.cur_guess_count, self.cur_guess_rate = QLabel("0"), QLabel("0")
        self.cur_usage_time = QLabel("0")
        self.cur_result = QLabel("")

        for label in [
            self.total_count,
            self.win_count, self.win_rate,
            self.lose_count, self.lose_rate,
            self.click_count, self.click_rate,
            self.mark_count, self.mark_rate,
            self.guess_count, self.guess_rate,
            self.usage_time_avg,
            self.cur_click_count, self.cur_click_rate,
            self.cur_mark_count, self.cur_mark_rate,
            self.cur_guess_count, self.cur_guess_rate,
            self.cur_usage_time,
            self.cur_result,
        ]:
            label.setAlignment(Qt.AlignmentFlag.AlignRight)

        grid = QGridLayout()

        count_label = QLabel("Count:")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(count_label, 1, 2)
        rate_label = QLabel("Rate:")
        rate_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(rate_label, 1, 3)

        grid.addWidget(QLabel("Total:"), 2, 1)
        grid.addWidget(self.total_count, 2, 2)

        grid.addWidget(QLabel("Win:"), 3, 1)
        grid.addWidget(self.win_count, 3, 2)
        grid.addWidget(self.win_rate, 3, 3)

        grid.addWidget(QLabel("Lose:"), 4, 1)
        grid.addWidget(self.lose_count, 4, 2)
        grid.addWidget(self.lose_rate, 4, 3)

        grid.addWidget(QLabel("Click:"), 5, 1)
        grid.addWidget(self.click_count, 5, 2)
        grid.addWidget(self.click_rate, 5, 3)

        grid.addWidget(QLabel("Mark:"), 6, 1)
        grid.addWidget(self.mark_count, 6, 2)
        grid.addWidget(self.mark_rate, 6, 3)

        grid.addWidget(QLabel("Guess:"), 7, 1)
        grid.addWidget(self.guess_count, 7, 2)
        grid.addWidget(self.guess_rate, 7, 3)

        grid.addWidget(QLabel("Avg. Usage Time:"), 8, 1, 1, 2)
        grid.addWidget(self.usage_time_avg, 8, 3)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(line, 9, 1, 1, 3)

        grid.addWidget(QLabel("Cur. Status:"), 10, 1, 1, 2)
        grid.addWidget(self.cur_result, 10, 3)

        grid.addWidget(QLabel("Cur. Click:"), 11, 1)
        grid.addWidget(self.cur_click_count, 11, 2)
        grid.addWidget(self.cur_click_rate, 11, 3)

        grid.addWidget(QLabel("Cur. Mark:"), 12, 1)
        grid.addWidget(self.cur_mark_count, 12, 2)
        grid.addWidget(self.cur_mark_rate, 12, 3)

        grid.addWidget(QLabel("Cur. Guess:"), 13, 1)
        grid.addWidget(self.cur_guess_count, 13, 2)
        grid.addWidget(self.cur_guess_rate, 13, 3)

        grid.addWidget(QLabel("Cur. Usage Time:"), 14, 1, 1, 2)
        grid.addWidget(self.cur_usage_time, 14, 3)

        self.setLayout(grid)

    def refresh(self, record_list):

        win = len([r for r in record_list if r["win"] is True])
        lose = len([r for r in record_list if r["win"] is False])
        total = max(1, win + lose)

        click = sum([r["click"] for r in record_list])
        mark = sum([r["mark"] for r in record_list])
        guess = sum([r["random_click"] for r in record_list])
        total_op = max(1, click + mark + guess)
        total_time = sum([r["usage_time"] for r in record_list])

        self.total_count.setText(f"{(win + lose)}")

        self.win_count.setText(f"{win}")
        self.win_rate.setText(f"{win / total * 100:.2f}%")

        self.lose_count.setText(f"{lose}")
        self.lose_rate.setText(f"{lose / total * 100:.2f}%")

        self.click_count.setText(f"{click}")
        self.click_rate.setText(f"{click / total_op * 100:.2f}%")

        self.mark_count.setText(f"{mark}")
        self.mark_rate.setText(f"{mark / total_op * 100:.2f}%")

        self.guess_count.setText(f"{guess}")
        self.guess_rate.setText(f"{guess / total_op * 100:.2f}%")

        self.usage_time_avg.setText(f"{total_time / total:.6f}")

        if len(record_list) > 0:
            time_delta = datetime.datetime.now() - record_list[-1]["start_time"]
            cur_click = record_list[-1]["click"]
            cur_mark = record_list[-1]["mark"]
            cur_guess = record_list[-1]["random_click"]
            cur_total_op = max(1, cur_click + cur_mark + cur_guess)

            self.cur_click_count.setText(f"{cur_click}")
            self.cur_click_rate.setText(f"{cur_click / cur_total_op * 100:.2f}%")

            self.cur_mark_count.setText(f"{cur_mark}")
            self.cur_mark_rate.setText(f"{cur_mark / cur_total_op * 100:.2f}%")

            self.cur_guess_count.setText(f"{cur_guess}")
            self.cur_guess_rate.setText(f"{cur_guess / cur_total_op * 100:.2f}%")

            self.cur_usage_time.setText(f"{time_delta.seconds}.{time_delta.microseconds}")

            if record_list[-1]["win"] is True:
                self.cur_result.setText("WIN")
            elif record_list[-1]["win"] is False:
                self.cur_result.setText("LOSE")
            else:
                self.cur_result.setText("solving")

        # self.update()


@singleton
class MainWindow(QMainWindow):
    mine_field = None
    game_terminated = False
    game_result = None
    cheat_mode = False

    app = None
    statistic_dialog = None

    emote = ""
    menu_action_dict = dict()
    status = ""

    bot = None
    bot_start_time = None
    bot_looper = None
    bot_pool = None
    bot_stat = None

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.init_window()

        self.bot_stat = BotStat()

        self.init_mine_field()

        self.bot = Bot()
        self.bot.result.click.connect(self.bot_click)
        self.bot.result.random_click.connect(self.bot_random_click)
        self.bot.result.mark.connect(self.bot_mark)
        self.bot.result.highlight.connect(self.bot_highlight)
        self.bot.result.emote.connect(self.set_emote)
        self.bot.result.message.connect(self.set_message)
        self.bot.result.bot_finished.connect(self.bot_finished)

        self.bot_looper = BotLooper()
        self.bot_looper.status.init_map.connect(self.init_mine_field)
        self.bot_looper.status.start_bot.connect(self.start_bot)

        self.bot_pool = QThreadPool()
        self.bot_pool.setMaxThreadCount(20)

    def init_window(self):
        self.setWindowFlags(Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        self.move(
            int(QApplication.primaryScreen().size().width() * 0.3),
            int(QApplication.primaryScreen().size().height() * 0.8),
        )
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "Mine.ico")))

        self.statistic_dialog = StatisticDialog(self)

        menu = self.menuBar()
        # Menu: Game
        game_menu = menu.addMenu("&Game")
        game_menu.addAction(
            self.create_menu_action(
                "New Game", "New Game",
                Qt.Key.Key_R, self.menu_re_init_mine_field))
        game_menu.addSeparator()
        # Menu: Game -> Difficulty
        difficulty_menu = game_menu.addMenu("Difficulty")
        difficulty_menu.addAction(
            self.create_menu_action(
                "Easy", "{} x {} with {} mines".format(*PRESET[0]),
                Qt.Key.Key_Q, self.menu_init_easy_mine_field))
        difficulty_menu.addAction(
            self.create_menu_action(
                "Medium", "{} x {} with {} mines".format(*PRESET[1]),
                Qt.Key.Key_W, self.menu_init_middle_mine_field))
        difficulty_menu.addAction(
            self.create_menu_action(
                "Hard", "{} x {} with {} mines".format(*PRESET[2]),
                Qt.Key.Key_E, self.menu_init_hard_mine_field))
        game_menu.addSeparator()
        difficulty_menu.addAction(
            self.create_menu_action(
                "Custom...", "Custom field size and mine number",
                Qt.Key.Key_C, self.menu_custom_mine_field))
        game_menu.addSeparator()
        game_menu.addAction(
            self.create_menu_action(
                "Exit", "Exit the game",
                Qt.Key.Key_Escape, self.menu_app_exit))
        # Menu: Bot
        bot_menu = menu.addMenu("&Bot")
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Click", "Auto click if empty land found when solving",
                Qt.Key.Key_A, self.menu_bot_switch_auto_click, check_able=True))
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Random Click", "Auto random click if no empty land found when solving",
                Qt.Key.Key_S, self.menu_bot_switch_auto_random_click, check_able=True))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "Random Click Once", "Auto click a random unmarked land",
                Qt.Key.Key_D, self.menu_bot_random_click))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve One Step", "Try to solve current game one step",
                Qt.Key.Key_F, self.menu_bot_solve_once))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Current Game", "Try to solve current game until win or lose",
                Qt.Key.Key_G, self.menu_bot_solve))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Continuously", "Try to solve games continuously",
                Qt.Key.Key_H, self.menu_bot_solve_looping))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "Statistic...", "Show solving records",
                Qt.Key.Key_X, trigger=self.menu_statistic))
        # Menu: About
        about_menu = menu.addMenu("&About")
        about_menu.addAction(
            self.create_menu_action(
                "&About...", "Visit project homepage",
                trigger=self.menu_about))

    def update_title(self):
        field = self.mine_field
        self.setWindowTitle(
            f"{field.field_width} X {field.field_height} with {field.mine_count} "
            f"({field.mine_count / (field.field_width * field.field_height) * 100:.2f}%) Mines "
            f"{self.emote}"
        )

    def update_status_bar(self):
        self.statusBar().showMessage(self.status)

    def set_emote(self, emote):
        self.emote = emote
        self.update_title()

    def set_message(self, msg):
        self.status = msg
        self.update_status_bar()

    def menu_re_init_mine_field(self):
        self.stop_looper()
        if not self.cheat_mode:
            self.init_mine_field()
        else:
            self.mine_field.reset_mine_field()
            self.game_terminated = False

    def menu_init_easy_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(*PRESET[0])

    def menu_init_middle_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(*PRESET[1])

    def menu_init_hard_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(*PRESET[2])

    def menu_custom_mine_field(self):
        field_size = self.mine_field.field_size()
        dialog = CustomFieldDialog(
            self, field_size["field_width"], field_size["field_height"], field_size["mine_count"])
        dialog.exec()

    def menu_bot_switch_auto_click(self):
        self.stop_looper()
        self.bot.auto_click = not self.bot.auto_click
        print(f"AUTO_CLICK: {self.bot.auto_click}")

    def menu_bot_switch_auto_random_click(self):
        self.stop_looper()
        self.bot.auto_random_click = not self.bot.auto_random_click
        print(f"AUTO_RAMDOM_CLICK: {self.bot.auto_random_click}")

    def menu_bot_random_click(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.bot.random_click()

    def menu_bot_solve_once(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.start_bot(step=1)

    def menu_bot_solve(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.bot.auto_click = True
            self.menu_action_dict["Auto Click"].setChecked(True)
            self.bot_stat.create_record()
            self.start_bot()

    def menu_bot_solve_looping(self):
        self.bot_looper.looping = not self.bot_looper.looping
        if self.bot_looper.looping:
            self.start_looper()
        else:
            self.stop_looper()

    def menu_statistic(self):
        self.statistic_dialog.refresh(self.bot_stat.record_list)
        self.statistic_dialog.move(self.geometry().x() - 200, self.geometry().y() - 30)
        self.statistic_dialog.show()

    @staticmethod
    def menu_about():
        webbrowser.open("https://github.com/Qionglu735/MineSweeperBot")

    def menu_app_exit(self):
        sys.exit(self.app.exec())

    def create_menu_action(self, title, status_tip, short_cut=None, trigger=None, check_able=None):
        menu_action = QAction(title, self)
        menu_action.setStatusTip(status_tip)
        if short_cut is not None:
            menu_action.setShortcut(short_cut)
        menu_action.triggered.connect(trigger)
        if check_able is not None:
            menu_action.setCheckable(check_able)
        self.menu_action_dict[title] = menu_action
        return menu_action

    def init_mine_field(self, field_width=0, field_height=0, mine_count=0):
        if self.mine_field is not None:
            field_size = self.mine_field.field_size()
        else:
            field_size = dict()
        if field_width > 0:
            field_size["field_width"] = field_width
        if field_height > 0:
            field_size["field_height"] = field_height
        if mine_count > 0:
            field_size["mine_count"] = mine_count

        self.mine_field = MineField(self, **field_size)
        self.game_terminated = False

        self.setCentralWidget(self.mine_field)
        self.adjustSize()
        self.set_emote("")
        self.set_message("New Game Ready")

        if self.bot_looper is not None and self.bot_looper.looping:
            self.bot_looper.status.map_ready.emit()  # --> bot_looper

    def keyPressEvent(self, event):
        # if event.key() < 256:
        #     print(chr(event.key()))
        # else:
        #     print(event.key())

        modifiers = QApplication.keyboardModifiers()

        if event.key() == Qt.Key.Key_U:
            new_width = self.mine_field.field_width + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_width = self.mine_field.field_width + 5
            self.init_mine_field(field_width=new_width)
        elif event.key() == Qt.Key.Key_I:
            new_width = self.mine_field.field_width - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_width = self.mine_field.field_width - 5
            self.init_mine_field(field_width=new_width)

        elif event.key() == Qt.Key.Key_J:
            new_height = self.mine_field.field_height + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_height = self.mine_field.field_height + 5
            self.init_mine_field(field_height=new_height)
        elif event.key() == Qt.Key.Key_K:
            new_height = self.mine_field.field_height - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_height = self.mine_field.field_height - 5
            self.init_mine_field(field_height=new_height)

        elif event.key() == Qt.Key.Key_M:
            new_count = self.mine_field.mine_count + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_count = self.mine_field.mine_count + 5
            self.init_mine_field(mine_count=new_count)
        elif event.key() == Qt.Key.Key_Period:
            new_count = self.mine_field.mine_count - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_count = self.mine_field.mine_count - 5
            self.init_mine_field(mine_count=new_count)

        elif event.key() == Qt.Key.Key_T:
            self.cheat_mode = not self.cheat_mode
            print(f"CHEAT_MODE: {self.cheat_mode}")
            for land in self.mine_field.land_list:
                land.update_tooltip(self.cheat_mode)

    def closeEvent(self, event):
        self.menu_app_exit()

    def start_bot(self, step=-1):
        self.bot.auto_step = step
        if step == -1:
            self.bot_stat.create_record()
        self.bot_pool.start(self.bot)

    def bot_click(self, land):  # <-- bot
        land.auto_click()
        self.bot.result.game_update_completed.emit()  # --> bot
        self.bot_stat.record_click()
        self.statistic_dialog.refresh(self.bot_stat.record_list)

    def bot_random_click(self, land):  # <-- bot
        land.auto_click()
        self.bot.result.game_update_completed.emit()  # --> bot
        self.bot_stat.record_random_click()
        self.statistic_dialog.refresh(self.bot_stat.record_list)

    def bot_mark(self, land):  # <-- bot
        land.auto_mark()
        self.bot.result.game_update_completed.emit()  # --> bot
        self.bot_stat.record_mark()
        self.statistic_dialog.refresh(self.bot_stat.record_list)

    def bot_highlight(self, land, _type):
        land.highlight(_type)
        self.bot.result.game_update_completed.emit()  # --> bot

    def bot_finished(self):  # <-- bot
        self.bot_looper.status.bot_finished.emit()  # --> bot_looper
        self.bot_stat.record_game_result(MainWindow().game_result)
        self.statistic_dialog.refresh(self.bot_stat.record_list)

    def start_looper(self):
        self.bot.auto_click = True
        self.menu_action_dict["Auto Click"].setChecked(True)
        self.bot.auto_random_click = True
        self.menu_action_dict["Auto Random Click"].setChecked(True)
        try:
            self.bot_pool.start(self.bot_looper)
        except RuntimeError:
            self.bot_looper = BotLooper()
            self.bot_looper.status.init_map.connect(self.init_mine_field)
            self.bot_looper.status.start_bot.connect(self.start_bot)
            self.bot_pool.start(self.bot_looper)

    def stop_looper(self):
        if self.bot_looper is not None and self.bot_looper.looping:
            self.bot_looper.status.stop_looping.emit()  # --> bot_looper
            self.bot.result.stop_solving.emit()  # --> bot
            self.statistic_dialog.refresh(self.bot_stat.record_list)
            while self.bot_looper.looping:
                pass


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    MainWindow(app).show()
    sys.exit(app.exec())


class Bot(QRunnable):
    class Result(QObject):
        click = Signal(object)  # --> Master
        random_click = Signal(object)  # --> Master
        mark = Signal(object)  # --> Master
        highlight = Signal(object, str)  # --> Master
        emote = Signal(str)   # --> Master
        message = Signal(str)  # --> Master

        game_update_completed = Signal()  # Master ->
        stop_solving = Signal()  # Master ->
        bot_finished = Signal()  # Master ->

    auto_click = False
    auto_random_click = False
    auto_step = -1
    game_updating = False

    auto_solving = False
    condition_list = list()
    result = None

    debug_print = False

    def __init__(self):
        super().__init__()
        self.setAutoDelete(False)
        self.result = Bot.Result()
        self.result.game_update_completed.connect(self.game_update_completed)
        self.result.stop_solving.connect(self.stop_solving)

    def game_update_completed(self):
        if MainWindow().game_terminated:
            self.auto_solving = False
        self.game_updating = False

    def stop_solving(self):
        self.auto_solving = False

    @Slot()
    def run(self):
        self.auto_solving = True
        self.game_updating = False
        while self.auto_solving and self.auto_step != 0:
            self.game_updating = True
            solve_success = self.solve()
            if not solve_success:
                break
            if self.auto_step > 0:
                self.auto_step -= 1
            while self.auto_solving and self.auto_step != 0 and self.game_updating:
                # wait until game update completed
                pass
        self.auto_solving = False
        self.result.bot_finished.emit()

    def solve(self):
        self.collect_condition()
        # print("[Bot]Try to analyse ...")
        if len(self.condition_list) == 0:
            self.result.emote.emit(":(")
            if self.auto_click:
                return self.random_click(is_first_click=True)
            else:
                print("[Bot] No conclusion found.")
                self.result.message.emit(f"No conclusion found")
                return False
        land, have_mine = self.analyse_condition()
        if land is not None:
            if self.auto_click:
                if not have_mine:
                    self.result.click.emit(land)
                else:
                    self.result.mark.emit(land)
            else:
                if not have_mine:
                    print(f"[Bot] ({land.x}, {land.y}) is empty")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) is empty")
                    self.result.highlight.emit(land, "safe")
                else:
                    print(f"[Bot] ({land.x}, {land.y}) have mine")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) have mine")
                    self.result.highlight.emit(land, "danger")
            self.result.emote.emit(":D")
            if self.debug_print:
                for cond in self.condition_list:
                    print({
                        "land": cond["land"].to_string(),
                        "possible_mine": cond["possible_mine"],
                        "adj_land": [land.to_string() for land in cond["adj_land"]],
                    })
            return True
        else:
            self.result.emote.emit(":(")
            if self.auto_random_click:
                return self.random_click()
            else:
                print("[Bot] No conclusion found.")
                self.result.message.emit(f"No conclusion found")
                return False

    def collect_condition(self):
        mine_field = MainWindow().mine_field
        self.condition_list = list()
        land_list = mine_field.land_list[:]
        shuffle(land_list)
        for land in land_list:
            if land.checked and land.adjacent_mine_count != 0:
                x, y = land.x, land.y
                condition = {
                    "land": land,
                    "possible_mine": land.adjacent_mine_count,
                    "adj_land": list()
                }
                for _x, _y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                    if _x == 0 and _y == 0:
                        continue
                    if 0 <= x + _x < mine_field.field_width and 0 <= y + _y < mine_field.field_height:
                        adj_land = mine_field.land_list[(x + _x) + mine_field.field_width * (y + _y)]
                        if not adj_land.checked:
                            if adj_land.cover != SYMBOL_FLAG:
                                condition["adj_land"].append(adj_land)
                            else:
                                condition["possible_mine"] -= 1

                if condition["possible_mine"] > 0 or len(condition["adj_land"]) > 0:
                    self.condition_list.append(condition)

        if self.debug_print:
            for cond in self.condition_list:
                print({
                    "land": cond["land"].to_string(),
                    "possible_mine": cond["possible_mine"],
                    "adj_land": [land.to_string() for land in cond["adj_land"]],
                })

    def random_click(self, is_first_click=False):
        print("[Bot] Random Click")
        mine_field = MainWindow().mine_field
        land_list = [land for land in mine_field.land_list if not land.checked and land.cover == SYMBOL_BLANK]
        if len(land_list) == 0:
            return False
        x = randint(0, len(land_list) - 1)
        if is_first_click:
            self.result.click.emit(land_list[x])
        else:
            self.result.random_click.emit(land_list[x])
        return True

    def analyse_condition(self):
        while True:
            for condition in self.condition_list:
                if condition["possible_mine"] == 0:
                    return condition["adj_land"][0], False

                elif condition["possible_mine"] == len(condition["adj_land"]):
                    return condition["adj_land"][0], True

            condition_updated = False
            for a, b in itertools.product(range(len(self.condition_list)), range(len(self.condition_list))):
                if a >= b:
                    continue
                cond_a, cond_b = self.condition_list[a], self.condition_list[b]
                if self.is_include(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id):
                    if cond_a["possible_mine"] == cond_b["possible_mine"]:
                        if len(cond_a["adj_land"]) != len(cond_b["adj_land"]):
                            empty_land = self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id)[0][0]
                            return empty_land, False

                    else:  # cond_a["possible_mine"] != cond_b["possible_mine"]
                        possible_mine_land, cond_a_new_adj, cond_b_new_adj = \
                            self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id)
                        if abs(cond_a["possible_mine"] - cond_b["possible_mine"]) \
                                == abs(len(cond_a["adj_land"]) - len(cond_b["adj_land"])):
                            return possible_mine_land[0], True
                        elif len(cond_a_new_adj) > 0:
                            self.condition_list[a]["adj_land"] = cond_a_new_adj
                            self.condition_list[a]["possible_mine"] = cond_a["possible_mine"] - cond_b["possible_mine"]
                            condition_updated = True
                            print({
                                "land": self.condition_list[a]["land"].to_string(),
                                "possible_mine": self.condition_list[a]["possible_mine"],
                                "adj_land": [land.to_string() for land in self.condition_list[a]["adj_land"]],
                            })
                        else:  # len(cond_b_new_adj) > 0:
                            self.condition_list[b]["adj_land"] = cond_b_new_adj
                            self.condition_list[b]["possible_mine"] = cond_b["possible_mine"] - cond_a["possible_mine"]
                            condition_updated = True
                            print({
                                "land": self.condition_list[b]["land"].to_string(),
                                "possible_mine": self.condition_list[b]["possible_mine"],
                                "adj_land": [land.to_string() for land in self.condition_list[b]["adj_land"]],
                            })
            if not condition_updated:
                break
        return None, None

    @staticmethod
    def is_include(a, b, func):
        if len(a) < len(b):
            tmp = a
            a = b
            b = tmp
        i, j, k = 0, 0, 0
        while i < len(a) and j < len(b):
            if func(a[i]) == func(b[j]):
                i += 1
                j += 1
                k += 1
            elif func(a[i]) < func(b[j]):
                i += 1
            else:
                j += 1
        return k == len(b)

    @staticmethod
    def sub(a, b, func):
        i, j = 0, 0
        _a, _b = a[:], b[:]
        while i < len(_a) and j < len(_b):
            __a, __b = func(_a[i]), func(_b[j])
            if __a == __b:
                _a.remove(_a[i])
                _b.remove(_b[j])
            elif __a < __b:
                i += 1
            else:
                j += 1
        if len(_a) != 0:
            return _a, _a, list()
        else:
            return _b, list(), _b


class BotLooper(QRunnable):
    class Status(QObject):
        init_map = Signal()         # --> Master
        map_ready = Signal()        # Master -->
        start_bot = Signal()         # --> Master
        bot_finished = Signal()      # Master -->
        stop_looping = Signal()     # Master -->

    looping = False
    map_initializing = False
    bot_running = False

    def __init__(self):
        super().__init__()
        self.status = BotLooper.Status()
        self.status.map_ready.connect(self.map_ready)
        self.status.bot_finished.connect(self.bot_finished)
        self.status.stop_looping.connect(self.stop_looping)

    def map_ready(self):
        self.map_initializing = False

    def bot_finished(self):
        self.bot_running = False

    def stop_looping(self):
        self.looping = False

    @Slot()
    def run(self):
        self.looping = True
        while self.looping:
            # print("[Looper] Start Bot")
            self.bot_running = True
            self.status.start_bot.emit()
            while self.bot_running:
                pass
            for _ in range(3 * 10):
                time.sleep(0.1)
                if not self.looping:
                    break

            if not self.looping:
                break
            # print("[Looper] Init Map")
            self.map_initializing = True
            self.status.init_map.emit()
            while self.map_initializing:
                pass
            for _ in range(1 * 10):
                time.sleep(0.1)
                if not self.looping:
                    break


class BotStat:
    record_list = list()
    current = -1

    def create_record(self):
        record = {
            "no": len(self.record_list) + 1,
            "win": None,
            "click": 0,
            "mark": 0,
            "random_click": 0,
            "start_time": datetime.datetime.now(),
            "usage_time": 0,
        }
        self.record_list.append(record)
        self.current += 1

    def clear_record(self):
        self.record_list = list()
        self.current = -1

    def record_click(self):
        self.record_list[self.current]["click"] += 1

    def record_mark(self):
        self.record_list[self.current]["mark"] += 1

    def record_random_click(self):
        self.record_list[self.current]["random_click"] += 1

    def record_game_result(self, game_result):
        if self.current >= 0 and self.record_list[self.current]["win"] is None:
            time_delta = datetime.datetime.now() - self.record_list[self.current]["start_time"]
            self.record_list[self.current]["usage_time"] = float(f"{time_delta.seconds}.{time_delta.microseconds}")
            if game_result in ["WIN", "LOSE"]:
                self.record_list[self.current]["win"] = game_result == "WIN"
            # print(self.record_list[self.current])


if __name__ == '__main__':
    main()
