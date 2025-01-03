
from PySide6.QtCore import QObject, Qt, QRunnable, Slot, QThreadPool, Signal, QEvent, QTimer
from PySide6.QtGui import QIcon, QAction, QIntValidator, QScreen, QKeySequence, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QToolBar, QSizePolicy
from PySide6.QtWidgets import QWidget, QGridLayout, QFileDialog
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox, QFrame
from inspect import currentframe, getframeinfo
from random import seed, randint, shuffle

import datetime
import functools
import gzip
import itertools
import json
import math
import os
import sys
import time
import webbrowser

import dark_theme

try:
    from ctypes import windll
    windll.shell32.SetCurrentProcessExplicitAppUserModelID("Qionglu735.MineSweeperBot.1.0")
except ImportError:
    windll = None

# import faulthandler
# faulthandler.enable()

PRESET = [
    # (3, 3, 1, "Debug", QKeySequence("Ctrl+Tab"), ),  # Debug
    (9, 9, 10, "Easy", QKeySequence("Ctrl+E"), ),  # Easy, 12.35%
    (16, 16, 40, "Moderate", QKeySequence("Ctrl+W"), ),  # Moderate, 15.62%
    (30, 16, 99, "Hard", QKeySequence("Ctrl+Q"), ),  # Hard, 20.62%
]

FIELD_PRESET = [
    (10, 10, "Small", ),
    (20, 20, "Medium", ),
    (40, 20, "Large", ),
    (60, 30, "Huge", ),
    (80, 40, "Expansive", ),
    (100, 50, "Gigantic", ),
]

DIFFICULTY_PRESET = [
    (0.10, "Simple", ),
    (0.12, "Easy", ),
    (0.14, "Moderate", ),
    (0.16, "Intermediate", ),
    (0.18, "Challenging", ),
    (0.20, "Hard", ),
    (0.22, "Punishing", ),
    (0.24, "Brutal", ),
]

MIN_WIDTH = 3
MAX_WIDTH = 1000

MIN_HEIGHT = 3
MAX_HEIGHT = 1000

SYMBOL_BLANK = " "
SYMBOL_MINE = "X"
SYMBOL_FLAG = "!"
SYMBOL_WRONG_FLAG = "#"
SYMBOL_UNKNOWN = "?"

COLOR_DICT = {
    SYMBOL_BLANK: "white",
    SYMBOL_MINE: "#ff0000",
    SYMBOL_FLAG: "#f02020",
    SYMBOL_WRONG_FLAG: "#f02020",
    SYMBOL_UNKNOWN: "#2020f0",
    "1": "#8080f0",
    "2": "#80f080",
    "3": "#f08080",
    "4": "#4040f0",
    "5": "#a0a040",
    "6": "#40a040",
    "7": "#000000",
    "8": "#404040",
}

SAFETY_LEVEL_DEFAULT = 1
BUTTON_SIZE_DEFAULT = 20


def singleton(cls):
    instances = dict()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


class Land(object):
    mine_field = None

    x = 0
    y = 0
    id = 0
    cover = SYMBOL_BLANK
    content = SYMBOL_BLANK
    have_mine = False
    adjacent_mine_count = 0
    checked = False
    focus = False
    wrong_flag = False

    ui = None

    def __init__(self, mine_field, x, y):
        self.mine_field = mine_field
        self.x, self.y = x, y
        self.id = x + self.mine_field.field_width * y

    def left_click(self, chain=False):
        field_width = self.mine_field.field_width
        field_height = self.mine_field.field_height

        if Game().game_terminated or not Game().game_terminated and self.cover in [
            SYMBOL_FLAG,
            SYMBOL_UNKNOWN,
        ]:
            # prevent changing check status
            self.ui.setChecked(self.checked)
            return

        if not chain:
            # print(f"Click ({self.x}, {self.y})")
            if len([x for x in self.mine_field.land_list if x.have_mine is True]) == 0:
                if self.mine_field.game.safety_level >= 1:
                    # first click always safe
                    self.mine_field.generate_mine(self.x, self.y)
                else:
                    self.mine_field.generate_mine()

        self.checked = True

        # check if click on mine
        self.mine_field.check_end_game(self.x, self.y)

        if not self.mine_field.game.game_terminated:
            flag_num = 0
            for x, y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                if x == 0 and y == 0:
                    continue
                if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                    land = self.mine_field.land_list[(self.x + x) + field_width * (self.y + y)]
                    if not land.checked and land.cover == SYMBOL_FLAG:
                        flag_num += 1
            if flag_num >= self.adjacent_mine_count:
                for x, y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                    if x == 0 and y == 0:
                        continue
                    if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                        land = self.mine_field.land_list[(self.x + x) + field_width * (self.y + y)]
                        if not land.checked and land.cover not in [
                            SYMBOL_FLAG,
                            SYMBOL_UNKNOWN,
                        ]:
                            land.left_click(chain=True)

        if not chain:
            if self.mine_field.game.safety_level >= 2:
                for _land in self.mine_field.land_list:
                    if _land.checked is False and _land.content == SYMBOL_BLANK:
                        _land.left_click(chain=True)

            self.focus = True
            self.ui.update_display()

            # check if chain click on mine
            self.mine_field.check_end_game(self.x, self.y)

            for _land in self.mine_field.land_list:
                if _land == self:
                    continue
                _land.focus = False
                _land.ui.update_display()

            self.mine_field.game.ui.update_title()
            if not self.mine_field.game.game_terminated:
                self.mine_field.game.ui.set_message(
                    f"{self.mine_field.mine_count - self.mine_field.marked_land_count()} mines left")

    def auto_click(self):
        # print(f"Auto Click")
        self.left_click()

    def right_click(self):
        if not self.mine_field.game.game_terminated:
            # print(f"Mark  ({self.x}, {self.y})")
            if not self.checked:
                if self.cover == SYMBOL_BLANK:
                    self.cover = SYMBOL_FLAG
                elif self.cover == SYMBOL_FLAG:
                    self.cover = SYMBOL_UNKNOWN
                elif self.cover == SYMBOL_UNKNOWN:
                    self.cover = SYMBOL_BLANK
                else:
                    self.cover = SYMBOL_FLAG
            self.mine_field.game.ui.set_message(
                f"{self.mine_field.mine_count - self.mine_field.marked_land_count()} mines left")
            self.mine_field.game.ui.update_title()
            self.focus = True
            self.ui.update_display()

            for _land in self.mine_field.land_list:
                if _land == self:
                    continue
                _land.focus = False
                _land.ui.update_display()

    def auto_mark(self):
        # print(f"Auto Mark")
        while not self.mine_field.game.game_terminated and self.cover != SYMBOL_FLAG:
            self.right_click()

    def to_string(self):
        return f"{self.id} ({self.x}, {self.y})"

    def save(self):
        res = dict()
        for key in [
            "x",
            "y",
            "id",
            "cover",
            "content",
            "have_mine",
            "adjacent_mine_count",
            "checked",
            "focus",
        ]:
            res[key] = getattr(self, key)
        return res

    def load(self, data):
        for key in data:
            setattr(self, key, data[key])

    def ui_init(self, parent):
        self.ui = LandUI(self, parent)

    def ui_setup(self):
        self.ui.update_display()
        self.ui.update_tooltip()


class MineField(object):
    game = None

    field_width = 0
    field_height = 0
    mine_count = 0

    land_list = None

    ui = None

    def __init__(self, game):
        self.game = game
        self.init_mine_field()

    def init_mine_field(self):
        self.field_width = min(max(MIN_WIDTH, self.field_width), MAX_WIDTH)
        self.field_height = min(max(MIN_HEIGHT, self.field_height), MAX_HEIGHT)
        self.mine_count = min(max(1, self.mine_count), (self.field_width - 1) * (self.field_height - 1))

        self.land_list = list()
        for y in range(self.field_height):
            for x in range(self.field_width):
                land = Land(self, x, y)
                land.cover = SYMBOL_BLANK
                self.land_list.append(land)

    def reset_mine_field(self):
        for land in self.land_list:
            land.cover = SYMBOL_BLANK
            land.checked = False
            land.focus = False
            land.ui.update_display()

    def generate_mine(self, safe_x=-9, safe_y=-9):
        for x in range(self.field_width):
            for y in range(self.field_height):
                self.land_list[x + self.field_width * y].have_mine = False
                self.land_list[x + self.field_width * y].adjacent_mine_count = 0
                self.land_list[x + self.field_width * y].checked = False
                self.land_list[x + self.field_width * y].content = SYMBOL_BLANK

                # self.land_list[x + self.field_width * y].ui.update_display()

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
                # land.ui.update_tooltip(Game().cheat_mode)

        self.game.game_start_time = datetime.datetime.now()

    def field_size(self):
        return {
            "field_width": self.field_width,
            "field_height": self.field_height,
            "mine_count": self.mine_count,
        }

    def land(self, _id=None, x=None, y=None):
        if type(_id) is int:
            return self.land_list[_id]
        elif type(x) is int and type(y) is int:
            x = max(0, min(x, self.field_width - 1))
            y = max(0, min(y, self.field_height - 1))
            return self.land_list[x + y * self.field_width]

    def get_focus(self):
        for land in self.land_list:
            if land.focus is True:
                return land
        return None

    def revealed_land_count(self):
        return len([x for x in self.land_list if x.checked])

    def marked_land_count(self):
        return len([x for x in self.land_list if not x.checked and x.cover == SYMBOL_FLAG])

    def row_mark_count(self, _id):
        land = self.land(_id)
        count = 0
        for x in range(0, self.field_width):
            if x == land.x:
                continue
            if self.land_list[x + self.field_width * land.y].cover == SYMBOL_FLAG:
                count += 1
        return count

    def col_mark_count(self, _id):
        land = self.land(_id)
        count = 0
        for y in range(0, self.field_height):
            if y == land.y:
                continue
            if self.land_list[land.x + self.field_width * y].cover == SYMBOL_FLAG:
                count += 1
        return count

    def check_end_game(self, x, y):
        if self.land_list[x + self.field_width * y].have_mine:
            self.game.game_end_time = datetime.datetime.now()
            self.game.game_terminated = True
            self.game.game_result = "LOSE"
            self.game.ui.set_message("YOU LOSE")
            for land in self.land_list:
                if land.have_mine:
                    if land.cover != SYMBOL_FLAG:
                        land.cover = SYMBOL_MINE
                        land.ui.update_display()
                else:
                    if land.cover == SYMBOL_FLAG:
                        land.wrong_flag = True
                        land.ui.update_display()
        elif self.revealed_land_count() == self.field_width * self.field_height - self.mine_count:
            self.game.game_end_time = datetime.datetime.now()
            self.game.game_terminated = True
            self.game.game_result = "WIN"
            self.game.ui.set_message("YOU WIN")
            for y in range(self.field_height):
                for x in range(self.field_width):
                    if self.land_list[x + self.field_width * y].have_mine:
                        self.land_list[x + self.field_width * y].cover = SYMBOL_FLAG
                        # self.land_list[x + self.field_width * y].ui.update_display()

    def save(self):
        res = dict()
        for key in [
            "field_width",
            "field_height",
            "mine_count",
        ]:
            res[key] = getattr(self, key)
        res["land_list"] = list()
        for land in self.land_list:
            res["land_list"].append(land.save())
        return res

    def load(self, data):
        for key in [
            "field_width",
            "field_height",
            "mine_count",
        ]:
            setattr(self, key, data[key])
        self.init_mine_field()
        for i, land in enumerate(data["land_list"]):
            self.land_list[i].load(land)

    def ui_init(self, parent):
        self.ui = MineFieldUI(parent)

    def ui_setup(self):
        self.ui.init_grid()
        for land in self.land_list:
            land.ui_init(self.ui)
            self.ui.add_land(land.ui, land.y, land.x)
            land.ui_setup()

        self.game.ui.setFixedWidth(20 + self.field_width * self.game.ui.button_size)
        self.game.ui.setFixedHeight(106 + self.field_height * self.game.ui.button_size)


@singleton
class Game(object):
    game_terminated = False
    game_start_time = None
    game_end_time = None
    game_result = None
    safety_level = SAFETY_LEVEL_DEFAULT
    cheat_mode = False

    mine_field = None

    bot = None
    bot_start_time = None
    bot_looper = None
    bot_pool = None
    bot_stat = None

    ui_app = None
    ui = None

    def __init__(self):
        self.mine_field = MineField(self)

        self.bot = Bot()
        self.bot.result.click.connect(self.bot_click)
        self.bot.result.random_click.connect(self.bot_random_click)
        self.bot.result.mark.connect(self.bot_mark)
        self.bot.result.custom_cover_ui.connect(self.bot_custom_cover_ui)
        self.bot.result.bot_finished.connect(self.bot_finished)

        self.bot_looper = BotLooper()
        self.bot_looper.status.init_map.connect(self.new_game_setup)
        self.bot_looper.status.start_bot.connect(self.start_bot)

        self.bot_pool = QThreadPool()
        self.bot_pool.setMaxThreadCount(20)

        self.bot_stat = BotStat()

    def new_game_setup(self, field_width=0, field_height=0, mine_count=0):
        if field_width > 0:
            self.mine_field.field_width = field_width
        if field_height > 0:
            self.mine_field.field_height = field_height
        if mine_count > 0:
            self.mine_field.mine_count = mine_count

        self.mine_field.init_mine_field()

        self.game_terminated = False
        self.game_start_time = None
        self.game_end_time = None

        if self.ui is not None:
            self.mine_field.ui_setup()
            self.ui.setCentralWidget(self.mine_field.ui)
            self.ui.adjustSize()
            self.ui.set_emote("")
            self.ui.set_message("New Game Ready")

        if self.bot_looper is not None and self.bot_looper.looping:
            self.bot_looper.status.map_ready.emit()  # --> bot_looper

    def save(self, file_path, data=None):
        pixmap = self.ui.take_screenshot()
        pixmap.save(file_path, "png")
        if data is None:
            data = self.mine_field.save()
        with open(file_path, "ab") as f:
            f.write(gzip.compress(json.dumps(data, separators=(",", ":", )).encode("utf-8")))

    def load(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            iend_index = data.rfind(b'IEND') + len(b'IEND') + 4
            json_data = json.loads(gzip.decompress(data[iend_index:]))
            self.game_terminated = False
            self.mine_field.load(json_data)
            self.mine_field.ui_setup()
            self.ui.update_title()
            self.ui.set_message(f"Load from {file_path.split("/")[-1]}")

    def start_bot(self, step=-1, guess=None):
        self.bot.auto_step = step
        if guess is not None:
            self.bot.random_step = guess
        if step == -1:
            self.bot_stat.create_record()
        self.bot_pool.start(self.bot)

    def bot_click(self, land):  # <-- bot
        land.auto_click()
        self.bot.result.game_update_completed.emit()  # --> bot
        if self.bot.auto_solving:
            self.bot_stat.record_click()
            self.ui.statistic_dialog.refresh(self.bot_stat.record_list)

    def bot_random_click(self, land):  # <-- bot
        land.auto_click()
        self.bot.result.game_update_completed.emit()  # --> bot
        if self.bot.auto_solving:
            self.bot_stat.record_random_click()
            self.ui.statistic_dialog.refresh(self.bot_stat.record_list)

    def bot_mark(self, land):  # <-- bot
        land.auto_mark()
        self.bot.result.game_update_completed.emit()  # --> bot
        if self.bot.auto_solving:
            self.bot_stat.record_mark()
            self.ui.statistic_dialog.refresh(self.bot_stat.record_list)

    @staticmethod
    def bot_custom_cover_ui(land, custom_cover, custom_color):
        land.ui.update_display(custom_cover=custom_cover, custom_color=custom_color)

    def bot_finished(self):  # <-- bot
        self.bot_looper.status.bot_finished.emit()  # --> bot_looper
        self.bot_stat.record_game_result(self.game_result)
        self.ui.statistic_dialog.refresh(self.bot_stat.record_list)
        if self.game_terminated and self.game_result == "LOSE":
            now = datetime.datetime.now()
            if not os.path.isdir("screenshot"):
                os.mkdir("screenshot")
            file_path = f"screenshot/{now.strftime("%Y_%m_%d_%H_%M_%S_%f")}.png"
            self.save(file_path, self.bot.data_before_solve)

    def start_looper(self):
        self.bot.auto_click = True
        self.ui.menu_action_dict["Auto Click"].setChecked(True)
        self.bot.auto_mark = True
        self.ui.menu_action_dict["Auto Mark"].setChecked(True)
        # self.bot.auto_random_click = True
        self.bot.random_step = -1
        self.ui.menu_action_dict["Auto Guess"].setChecked(True)
        try:
            self.bot_pool.start(self.bot_looper)
        except RuntimeError:
            self.bot_looper = BotLooper()
            self.bot_looper.status.init_map.connect(self.new_game_setup)
            self.bot_looper.status.start_bot.connect(self.start_bot)
            self.bot_pool.start(self.bot_looper)

    def stop_looper(self):
        if self.bot_looper is not None and self.bot_looper.looping:
            self.bot_looper.status.stop_looping.emit()  # --> bot_looper
            self.bot.result.stop_solving.emit()  # --> bot
            self.ui.statistic_dialog.refresh(self.bot_stat.record_list)
            while self.bot_looper.looping:
                pass
            self.ui.menu_action_dict["Solve Continuously"].setChecked(False)

    def ui_init(self):
        self.ui_app = QApplication(sys.argv)
        self.ui_app.setStyle("Fusion")
        self.ui_app.setPalette(dark_theme.PALETTE)

        self.ui = GameUI(self)
        self.ui.show()

        self.mine_field.ui_init(self.ui)

        self.bot.result.emote.connect(self.ui.set_emote)
        self.bot.result.message.connect(self.ui.set_message)
        self.bot.result.highlight.connect(self.ui.bot_highlight)

    def ui_setup(self):
        pass

    def wait_for_exit(self):
        if self.ui_app is not None:
            sys.exit(self.ui_app.exec())
        else:
            while not self.game_terminated:
                pass
            sys.exit()


class LandUI(QPushButton):
    land = None

    custom_color = None
    style_sheet = """
        QPushButton {
            color: FONT_COLOR;
            font: "Roman Times";
            font-size: FONT_SIZE;
            font-weight: bold;
            /* BORDER_STYLE */
            background-color: #292929;
        }
        QPushButton:pressed {
            border: 2px solid #797917;
        }
        QPushButton:checked {
            background-color: #232323;
        }
    """

    def __init__(self, land, parent):
        super().__init__(parent, text=SYMBOL_BLANK)

        self.land = land

        button_size = self.land.mine_field.game.ui.button_size
        self.setFixedSize(button_size, button_size)
        self.setStyleSheet(
            self.style_sheet
                .replace("FONT_COLOR", "white")
                .replace("FONT_SIZE", "{:.0f}px".format(button_size * 0.6)))
        self.setCheckable(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def left_click(self, chain=False):
        self.land.left_click(chain)

    def right_click(self):
        self.land.right_click()

    def update_display(self, custom_cover=None, custom_color=None):
        style_sheet = self.style_sheet
        button_size = self.land.mine_field.game.ui.button_size
        if self.land.focus:
            self.setFocus()
            style_sheet = style_sheet.replace("/* BORDER_STYLE */", "border: 2px solid #a3a323;")
        self.setChecked(self.land.checked)
        if self.land.checked:
            self.setText(self.land.content)
            style_sheet = style_sheet \
                .replace("FONT_COLOR", COLOR_DICT[self.land.content]) \
                .replace("FONT_SIZE", "{:.0f}px".format(button_size * 0.6))
        else:
            if self.land.wrong_flag:
                self.setText(SYMBOL_WRONG_FLAG)
                style_sheet = style_sheet \
                    .replace("FONT_COLOR", COLOR_DICT[SYMBOL_WRONG_FLAG]) \
                    .replace("FONT_SIZE", "{:.0f}px".format(button_size * 0.6))
            else:
                cover = self.land.cover
                if custom_cover is not None:
                    cover = custom_cover
                self.setText(cover)
                if cover in COLOR_DICT:
                    style_sheet = style_sheet \
                        .replace("FONT_COLOR", COLOR_DICT[cover]) \
                        .replace("FONT_SIZE", "{:.0f}px".format(button_size * 0.6))
                else:
                    if custom_color is not None:
                        self.custom_color = custom_color
                    custom_color = self.custom_color
                    if custom_color is None:
                        custom_color = "#ffffff"
                    style_sheet = style_sheet \
                        .replace("FONT_COLOR", custom_color) \
                        .replace("FONT_SIZE", "{:.0f}px".format(button_size * 0.5))

        self.setStyleSheet(style_sheet)
        self.update_tooltip(self.land.mine_field.game.cheat_mode)

    def update_tooltip(self, cheat_mode=False):
        if self.land.have_mine and cheat_mode:
            self.setToolTip(f"! ({self.land.x + 1}, {self.land.y + 1}) {self.land.id} !")
        else:
            self.setToolTip(f"({self.land.x + 1}, {self.land.y + 1}) {self.land.id}")

    def highlight(self, _type):
        style_sheet = self.styleSheet()
        if _type == "danger":
            style_sheet = style_sheet.replace("/* BORDER_STYLE */", "border: 2px solid #a02020;")
        elif _type == "safe":
            style_sheet = style_sheet.replace("/* BORDER_STYLE */", "border: 2px solid #20a020;")
        self.setStyleSheet(style_sheet)


class MineFieldUI(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

    def init_grid(self):
        if self.layout() is None:
            grid = QGridLayout()
            grid.setSpacing(0)
            self.setLayout(grid)
        else:
            grid = self.layout()
            while grid.count() > 0:
                grid.itemAt(0).widget().setParent(None)

    def add_land(self, land, y, x):
        land.clicked.connect(self.left_click)
        land.customContextMenuRequested.connect(self.right_click)
        grid = self.layout()
        grid.addWidget(land, y, x)

    def left_click(self):
        self.sender().left_click()

    def right_click(self):
        self.sender().right_click()


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
    width, height, mine = PRESET[0][:3]

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

        grid.addWidget(QLabel("Difficulty Level:"), 3, 1)
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
            mine = max(1, int(self.width * self.height * DIFFICULTY_PRESET[index][0] + 1))
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
        self.parent().game.new_game_setup(self.width, self.height, self.mine)
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
        self.setFixedSize(191 - 2, 372 - 32)

        self.total_count = QLabel("0")
        self.win_count, self.win_rate = QLabel("0"), QLabel("0.00%")
        self.lose_count, self.lose_rate = QLabel("0"), QLabel("0.00%")
        self.click_count, self.click_rate = QLabel("0"), QLabel("0.00%")
        self.mark_count, self.mark_rate = QLabel("0"), QLabel("0.00%")
        self.guess_count, self.guess_rate = QLabel("0"), QLabel("0.00%")
        self.guess_success_count, self.guess_success_rate = QLabel("0"), QLabel("0.00%")
        self.guess_fail_count, self.guess_fail_rate = QLabel("0"), QLabel("0.00%")
        self.usage_time_avg = QLabel("0.000000")
        self.cur_click_count, self.cur_click_rate = QLabel("0"), QLabel("0.00%")
        self.cur_mark_count, self.cur_mark_rate = QLabel("0"), QLabel("0.00%")
        self.cur_guess_count, self.cur_guess_rate = QLabel("0"), QLabel("0.00%")
        self.cur_usage_time = QLabel("0.000000")
        self.cur_result = QLabel("")

        for label in [
            self.total_count,
            self.win_count, self.win_rate,
            self.lose_count, self.lose_rate,
            self.click_count, self.click_rate,
            self.mark_count, self.mark_rate,
            self.guess_count, self.guess_rate,
            self.guess_success_count, self.guess_success_rate,
            self.guess_fail_count, self.guess_fail_rate,
            self.usage_time_avg,
            self.cur_click_count, self.cur_click_rate,
            self.cur_mark_count, self.cur_mark_rate,
            self.cur_guess_count, self.cur_guess_rate,
            self.cur_usage_time,
            self.cur_result,
        ]:
            label.setAlignment(Qt.AlignmentFlag.AlignRight)

        grid = QGridLayout()

        grid_row = 1
        count_label = QLabel("Count:")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(count_label, grid_row, 2)
        rate_label = QLabel("Rate:")
        rate_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(rate_label, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Total:"), grid_row, 1)
        grid.addWidget(self.total_count, grid_row, 2)

        grid_row += 1
        grid.addWidget(QLabel("Win:"), grid_row, 1)
        grid.addWidget(self.win_count, grid_row, 2)
        grid.addWidget(self.win_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Lose:"), grid_row, 1)
        grid.addWidget(self.lose_count, grid_row, 2)
        grid.addWidget(self.lose_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Click:"), grid_row, 1)
        grid.addWidget(self.click_count, grid_row, 2)
        grid.addWidget(self.click_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Mark:"), grid_row, 1)
        grid.addWidget(self.mark_count, grid_row, 2)
        grid.addWidget(self.mark_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Guess:"), grid_row, 1)
        grid.addWidget(self.guess_count, grid_row, 2)
        grid.addWidget(self.guess_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Guess Suc.:"), grid_row, 1)
        grid.addWidget(self.guess_success_count, grid_row, 2)
        grid.addWidget(self.guess_success_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Guess Fail:"), grid_row, 1)
        grid.addWidget(self.guess_fail_count, grid_row, 2)
        grid.addWidget(self.guess_fail_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Avg. Usage Time:"), grid_row, 1, 1, 2)
        grid.addWidget(self.usage_time_avg, grid_row, 3)

        grid_row += 1
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(line, grid_row, 1, 1, 3)

        grid_row += 1
        grid.addWidget(QLabel("Cur. Status:"), grid_row, 1, 1, 2)
        grid.addWidget(self.cur_result, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Cur. Click:"), grid_row, 1)
        grid.addWidget(self.cur_click_count, grid_row, 2)
        grid.addWidget(self.cur_click_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Cur. Mark:"), grid_row, 1)
        grid.addWidget(self.cur_mark_count, grid_row, 2)
        grid.addWidget(self.cur_mark_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Cur. Guess:"), grid_row, 1)
        grid.addWidget(self.cur_guess_count, grid_row, 2)
        grid.addWidget(self.cur_guess_rate, grid_row, 3)

        grid_row += 1
        grid.addWidget(QLabel("Cur. Usage Time:"), grid_row, 1, 1, 2)
        grid.addWidget(self.cur_usage_time, grid_row, 3)

        self.setLayout(grid)

    def refresh(self, record_list):

        win = len([r for r in record_list if r["win"] is True])
        lose = len([r for r in record_list if r["win"] is False])
        total = win + lose

        click = sum([r["click"] for r in record_list])
        mark = sum([r["mark"] for r in record_list])
        guess = sum([r["random_click"] for r in record_list])
        total_op = click + mark + guess
        total_time = sum([r["usage_time"] for r in record_list if r["win"] is True])

        self.total_count.setText(f"{(win + lose)}")

        if total > 0:
            self.win_count.setText(f"{win}")
            self.win_rate.setText(f"{win / total * 100:.2f}%")

            self.lose_count.setText(f"{lose}")
            self.lose_rate.setText(f"{lose / total * 100:.2f}%")

        if total_op > 0:
            self.click_count.setText(f"{click}")
            self.click_rate.setText(f"{click / total_op * 100:.2f}%")

            self.mark_count.setText(f"{mark}")
            self.mark_rate.setText(f"{mark / total_op * 100:.2f}%")

            self.guess_count.setText(f"{guess}")
            self.guess_rate.setText(f"{guess / total_op * 100:.2f}%")

        self.guess_success_count.setText(f"{guess - lose}")
        self.guess_fail_count.setText(f"{lose}")
        if guess > 0:
            self.guess_success_rate.setText(f"{(guess - lose) / guess * 100:.2f}%")
            self.guess_fail_rate.setText(f"{lose / guess * 100:.2f}%")

        if win > 0:
            self.usage_time_avg.setText(f"{total_time / win:.6f}")

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

            self.cur_usage_time.setText(f"{time_delta.seconds}.{time_delta.microseconds:06}")

            if record_list[-1]["win"] is True:
                self.cur_result.setText("Win")
            elif record_list[-1]["win"] is False:
                self.cur_result.setText("Lose")
            else:
                self.cur_result.setText("Solving")

        # self.update()


class GameUI(QMainWindow):
    game = None

    button_size = BUTTON_SIZE_DEFAULT
    ui_activated = True
    ui_opacity_max = 1000
    ui_opacity = ui_opacity_max
    statistic_dialog = None

    menu_action_dict = dict()
    emote = ""
    title_label = None
    land_label = None
    mine_label = None
    time_label = None
    update_timer = None
    status = ""

    def __init__(self, game):
        super().__init__()
        self.game = game

        self.init_window()

    def init_window(self):
        self.setWindowTitle("MineSweeper")
        # self.setWindowFlags(Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.move(
            int(QApplication.primaryScreen().size().width() * 0.37),
            int(QApplication.primaryScreen().size().height() * 0.73),
        )
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "Mine.ico")))

        self.statistic_dialog = StatisticDialog(self)

        self.title_label = QLabel()

        self.init_menu()

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addWidget(self.title_label)

        label_font = QFont("Lucida Console", 9)
        self.land_label = QLabel("")
        self.land_label.setFont(label_font)
        self.mine_label = QLabel("")
        self.mine_label.setFont(label_font)
        self.time_label = QLabel("")
        self.time_label.setFont(label_font)

        toolbar_2 = QToolBar()
        toolbar_2.setMovable(False)
        toolbar_2.addWidget(self.land_label)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar_2.addWidget(spacer_left)

        toolbar_2.addWidget(self.mine_label)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar_2.addWidget(spacer_right)

        toolbar_2.addWidget(self.time_label)

        self.addToolBar(toolbar)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(toolbar_2)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_time_label)
        self.update_timer.start(10)

    def init_menu(self):
        menu = self.menuBar()
        # Menu: Game
        game_menu = menu.addMenu("&Game")
        game_menu.addAction(
            self.create_menu_action(
                "New &Game", "Start a new game",
                Qt.Key.Key_R, self.menu_new_game_reset))
        game_menu.addSeparator()
        for preset in PRESET:
            game_menu.addAction(
                self.create_menu_action(
                    f"&{preset[3]}", "{} x {} with {} mines".format(*preset[:3]),
                    preset[4], functools.partial(self.menu_new_game_setup, *preset[:3])))
        # Menu: Game -> Difficulty
        difficulty_menu = game_menu.addMenu("More &Difficulty")
        # Menu: Game -> Difficulty -> Field Size
        field_size_menu = difficulty_menu.addMenu("&Field Size")
        for preset in FIELD_PRESET:
            field_size_menu.addAction(
                self.create_menu_action(
                    f"&{preset[2]}", "{} x {}".format(*preset[:2]),
                    trigger=functools.partial(self.menu_new_game_setup, *preset[:2])))
        # Menu: Game -> Difficulty -> Difficulty Level
        difficulty_level_menu = difficulty_menu.addMenu("&Difficulty Level")
        for preset in DIFFICULTY_PRESET:
            difficulty_level_menu.addAction(
                self.create_menu_action(
                    f"&{preset[1]}", "{}% lands have mine".format(int(preset[0] * 100)),
                    trigger=functools.partial(self.menu_new_game_setup, percent=preset[0])))
        difficulty_menu.addAction(
            self.create_menu_action(
                "&Custom...", "Custom field size and number of mines",
                QKeySequence("Ctrl+A"), self.menu_custom_mine_field))

        game_menu.addSeparator()
        game_menu.addAction(
            self.create_menu_action(
                "&Save", "Save game ...",
                QKeySequence("Ctrl+S"), self.menu_save))
        game_menu.addAction(
            self.create_menu_action(
                "&Load", "Load game ...",
                QKeySequence("Ctrl+L"), self.menu_load))
        game_menu.addSeparator()
        game_menu.addAction(
            self.create_menu_action(
                "E&xit", "Exit the game",
                Qt.Key.Key_Escape, self.menu_exit))

        # Menu: Bot
        bot_menu = menu.addMenu("&Bot")
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Click", "Auto click if empty land found while solving",
                QKeySequence("Ctrl+Z"), self.menu_bot_switch_auto_click, check_able=True))
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Mark", "Auto click if empty land found while solving",
                QKeySequence("Ctrl+X"), self.menu_bot_switch_auto_mark, check_able=True))
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Guess", "Auto guess if no conclusion found while solving",
                QKeySequence("Ctrl+C"), self.menu_bot_switch_auto_random_click, check_able=True))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "&Guess Once", "Auto click a random unmarked land",
                Qt.Key.Key_G, self.menu_bot_random_click))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Onc&e", "Try to solve current game one step",
                Qt.Key.Key_F, self.menu_bot_solve_once))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve &Current Game", "Try to solve current game until win or lose",
                Qt.Key.Key_B, self.menu_bot_solve))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Continuously", "Auto start new games and solve them continuously",
                Qt.Key.Key_V, self.menu_bot_solve_looping, check_able=True))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "&Statistic...", "Show solving records",
                Qt.Key.Key_C, trigger=self.menu_statistic))
        bot_menu.addAction(
            self.create_menu_action(
                "Clea&r Statistic", "Clear solving records",
                QKeySequence("Ctrl+D"), trigger=self.menu_clear_statistic))

        # Menu: Option
        option_menu = menu.addMenu("&Option")
        option_menu.addAction(
            self.create_menu_action(
                "Safety First", "First click always safe",
                None, self.menu_safety_first,
                check_able=True, checked=(self.game.safety_level >= 1)))
        option_menu.addAction(
            self.create_menu_action(
                "Protective Measure", "Reveal all safe area",
                None, self.menu_protective_measure,
                check_able=True, checked=(self.game.safety_level >= 2)))
        option_menu.addSeparator()

        # Menu: About
        about_menu = menu.addMenu("&About")
        about_menu.addAction(
            self.create_menu_action(
                "&About...", "Visit project homepage",
                trigger=self.menu_about))

    def update_title(self):
        field = self.game.mine_field
        title_string = \
            f"{field.field_width} X {field.field_height} with {field.mine_count} " \
            f"({field.mine_count / (field.field_width * field.field_height) * 100:.2f}%) Mines " \
            f"{self.emote}"
        self.title_label.setText(title_string)
        self.title_label.setToolTip(title_string)

        empty_land_count = field.field_width * field.field_height \
            - field.revealed_land_count() - field.marked_land_count()
        empty_land_rate = 0
        if empty_land_count > 0:
            empty_land_rate = 100 * (empty_land_count - (field.mine_count - field.marked_land_count())) \
                              / empty_land_count
        mine_rate = 0
        if empty_land_count > 0:
            mine_rate = 100 * (field.mine_count - field.marked_land_count()) \
                        / empty_land_count

        if field.field_width * self.button_size < 80:
            land_string_label = "L"
            mine_string_label = "M"
        elif field.field_width * self.button_size < 110:
            land_string_label = "Land"
            mine_string_label = "Mine"
        elif field.field_width * self.button_size < 350:
            land_string_label = "L"
            mine_string_label = "M"
        else:
            land_string_label = "Land"
            mine_string_label = "Mine"
        if field.field_width * self.button_size < 110:
            land_string_data = ""
            mine_string_data = ""
        else:
            land_string_data = f":{empty_land_count}/{field.field_width * field.field_height}"
            mine_string_data = f":{field.mine_count - field.marked_land_count()}/{field.mine_count}"
        if field.field_width * self.button_size < 280:
            land_string_rate = ""
            mine_string_rate = ""
        else:
            land_string_rate = f" ({empty_land_rate:.2f}%)"
            mine_string_rate = f" ({mine_rate:.2f}%)"

        self.land_label.setText(
            f"{land_string_label}{land_string_data}{land_string_rate}")
        self.land_label.setToolTip(
            f"Land:{empty_land_count}/{field.field_width * field.field_height} ({empty_land_rate:.2f}%)")
        self.mine_label.setText(
            f"{mine_string_label}{mine_string_data}{mine_string_rate}")
        self.mine_label.setToolTip(
            f"Mine:{field.mine_count - field.marked_land_count()} / {field.mine_count} ({mine_rate:.2f}%)")

    def update_time_label(self):
        time_delta = datetime.timedelta()
        if self.game.game_start_time is not None:
            if self.game.game_end_time is not None:
                time_delta = self.game.game_end_time - self.game.game_start_time
            else:
                time_delta = datetime.datetime.now() - self.game.game_start_time
        display_second = time_delta.seconds
        display_milliseconds = time_delta.microseconds / 1000
        if time_delta.seconds > 999:
            display_second = 999
            display_milliseconds = 999

        field = self.game.mine_field
        if field.field_width * self.button_size < 80:
            time_string_label = "T"
        elif field.field_width * self.button_size < 110:
            time_string_label = "Time"
        elif field.field_width * self.button_size < 350:
            time_string_label = "T"
        else:
            time_string_label = "Time"
        if field.field_width * self.button_size < 110:
            time_string_data = ""
        else:
            time_string_data = f":{display_second}.{math.floor(display_milliseconds / 10):02.0f}"

        self.time_label.setText(
            f"{time_string_label}{time_string_data}")
        self.time_label.setToolTip(
            f"Time:{time_string_data}")

    def update_status_bar(self):
        self.statusBar().showMessage(self.status)

    def set_emote(self, emote):
        self.emote = emote
        self.update_title()

    def set_message(self, msg):
        self.status = msg
        self.update_status_bar()

    def take_screenshot(self):
        # win_id = self.winId()
        # g = self.geometry()
        # fg = self.frameGeometry()
        # rfg = fg.translated(-g.left(), -g.top())
        # screen = self.game.ui_app.primaryScreen()
        # pixmap = QScreen.grabWindow(
        #     screen, win_id,
        #     rfg.left(), rfg.top(),
        #     rfg.width(), rfg.height(),
        #     # rfg.left() - 1, rfg.top() - 1,
        #     # rfg.width() + 2, rfg.height() + 2,
        # )
        pixmap = self.grab()
        return pixmap

    def menu_new_game_reset(self):
        self.game.stop_looper()
        if not self.game.cheat_mode:
            self.game.new_game_setup()
        else:
            self.game.mine_field.reset_mine_field()
            self.game.game_terminated = False

    def menu_new_game_setup(self, *args, **kwargs):
        self.game.stop_looper()
        if "percent" in kwargs:
            mine_count = int(self.game.mine_field.field_width * self.game.mine_field.field_height * kwargs["percent"])
            kwargs["mine_count"] = mine_count
            del kwargs["percent"]
        return self.game.new_game_setup(*args, **kwargs)

    def menu_custom_mine_field(self):
        field_size = self.game.mine_field.field_size()
        dialog = CustomFieldDialog(
            self, field_size["field_width"], field_size["field_height"], field_size["mine_count"])
        dialog.exec()

    def menu_save(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save to file",
            f"{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")}",
            "PNG (*.png);;All Files (*)"
        )
        if file_path:
            self.game.save(file_path)

    def menu_load(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Load from file",
            filter="PNG (*.png);;All Files (*)",
        )
        if os.path.isfile(file_path):
            self.game.load(file_path)

    def menu_exit(self):
        self.close()

    def menu_bot_switch_auto_click(self):
        self.game.stop_looper()
        self.game.bot.auto_click = not self.game.bot.auto_click
        print(f"AUTO_CLICK: {self.game.bot.auto_click}")

    def menu_bot_switch_auto_mark(self):
        self.game.stop_looper()
        self.game.bot.auto_mark = not self.game.bot.auto_mark
        print(f"AUTO_MARK: {self.game.bot.auto_mark}")

    def menu_bot_switch_auto_random_click(self):
        self.game.stop_looper()
        # self.bot.auto_random_click = not self.bot.auto_random_click
        if self.game.bot.random_step >= 0:
            self.game.bot.random_step = -1  # unlimited
        else:
            self.game.bot.random_step = 0  # not allow

        print(f"AUTO_RAMDOM_CLICK: {self.game.bot.random_step == -1}")

    def menu_bot_random_click(self):
        self.game.stop_looper()
        if not self.game.game_terminated:
            self.game.bot.random_click()

    def menu_bot_solve_once(self, allow_guess=False):
        self.game.stop_looper()
        if not self.game.game_terminated:
            if allow_guess:
                self.game.start_bot(step=1, guess=1)
            else:
                self.game.start_bot(step=1)

    def menu_bot_solve(self):
        self.game.stop_looper()
        if not self.game.game_terminated:
            self.game.bot.auto_click = True
            self.menu_action_dict["Auto Click"].setChecked(True)
            self.game.bot.auto_mark = True
            self.menu_action_dict["Auto Mark"].setChecked(True)
            self.game.bot_stat.create_record()
            self.game.start_bot()

    def menu_bot_solve_looping(self):
        if not self.game.bot_looper.looping:
            if self.game.game_terminated:
                self.game.new_game_setup()
            self.game.start_looper()
        else:
            self.game.stop_looper()

    def menu_statistic(self):
        self.statistic_dialog.refresh(self.game.bot_stat.record_list)
        self.statistic_dialog.move(self.geometry().x() - 200, self.geometry().y() - 30)
        self.statistic_dialog.show()
        self.activateWindow()

    def menu_clear_statistic(self):
        self.game.bot_stat.clear_record()
        self.statistic_dialog.refresh(self.game.bot_stat.record_list)

    def menu_safety_first(self):
        if self.menu_action_dict["Safety First"].isChecked() is True:
            self.game.safety_level = 1
        else:
            self.game.safety_level = 0
            self.menu_action_dict["Protective Measure"].setChecked(False)

    def menu_protective_measure(self):
        if self.menu_action_dict["Protective Measure"].isChecked() is True:
            self.game.safety_level = 2
            self.menu_action_dict["Safety First"].setChecked(True)
        else:
            if self.menu_action_dict["Safety First"].isChecked() is True:
                self.game.safety_level = 1
            else:
                self.game.safety_level = 0

    @staticmethod
    def menu_about():
        webbrowser.open("https://github.com/Qionglu735/MineSweeperBot")

    def create_menu_action(self, title, status_tip, short_cut=None, trigger=None, check_able=None, checked=False):
        menu_action = QAction(title, self)
        menu_action.setStatusTip(status_tip)
        if short_cut is not None:
            menu_action.setShortcut(short_cut)
        menu_action.triggered.connect(trigger)
        if check_able is not None:
            menu_action.setCheckable(check_able)
            if checked is True:
                menu_action.setChecked(True)
        self.menu_action_dict[title] = menu_action
        return menu_action

    def keyPressEvent(self, event):
        # print(event.key(), event.keyCombination().key().name)

        modifiers = QApplication.keyboardModifiers()

        if event.key() == Qt.Key.Key_U:
            new_width = self.game.mine_field.field_width + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_width = self.game.mine_field.field_width + 5
            self.game.new_game_setup(field_width=new_width)
        elif event.key() == Qt.Key.Key_I:
            new_width = self.game.mine_field.field_width - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_width = self.game.mine_field.field_width - 5
            self.game.new_game_setup(field_width=new_width)

        elif event.key() == Qt.Key.Key_J:
            new_height = self.game.mine_field.field_height + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_height = self.game.mine_field.field_height + 5
            self.game.new_game_setup(field_height=new_height)
        elif event.key() == Qt.Key.Key_K:
            new_height = self.game.mine_field.field_height - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_height = self.game.mine_field.field_height - 5
            self.game.new_game_setup(field_height=new_height)

        elif event.key() == Qt.Key.Key_M:
            new_count = self.game.mine_field.mine_count + 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_count = self.game.mine_field.mine_count + 5
            self.game.new_game_setup(mine_count=new_count)
        elif event.key() == Qt.Key.Key_Comma:
            new_count = self.game.mine_field.mine_count - 1
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                new_count = self.game.mine_field.mine_count - 5
            self.game.new_game_setup(mine_count=new_count)

        elif event.key() == Qt.Key.Key_T:
            self.game.cheat_mode = not self.game.cheat_mode
            print(f"CHEAT_MODE: {self.game.cheat_mode}")
            for land in self.game.mine_field.land_list:
                land.ui.update_tooltip(self.game.cheat_mode)

        elif event.key() == Qt.Key.Key_F and modifiers == Qt.KeyboardModifier.ControlModifier:
            print("allow_guess")
            self.menu_bot_solve_once(allow_guess=True)

        elif event.key() == Qt.Key.Key_Z:
            self.showMinimized()

        elif event.key() in [
            Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D,
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
        ]:
            land_list = self.game.mine_field.land_list
            focus_land = self.game.mine_field.get_focus()
            if focus_land is None:
                land_list[int(len(land_list) / 2)].focus = True
                land_list[int(len(land_list) / 2)].ui.update_display()
            else:
                focus_land_new = focus_land
                if event.key() in [Qt.Key.Key_W, Qt.Key.Key_Up]:
                    focus_land_new = self.game.mine_field.land(x=focus_land.x, y=focus_land.y - 1)
                elif event.key() in [Qt.Key.Key_S, Qt.Key.Key_Down]:
                    focus_land_new = self.game.mine_field.land(x=focus_land.x, y=focus_land.y + 1)
                elif event.key() in [Qt.Key.Key_A, Qt.Key.Key_Left]:
                    focus_land_new = self.game.mine_field.land(x=focus_land.x - 1, y=focus_land.y)
                elif event.key() in [Qt.Key.Key_D, Qt.Key.Key_Right]:
                    focus_land_new = self.game.mine_field.land(x=focus_land.x + 1, y=focus_land.y)
                if focus_land_new != focus_land:
                    focus_land.focus = False
                    focus_land_new.focus = True
                    focus_land.ui.update_display()
                    focus_land_new.ui.update_display()

        elif event.key() == Qt.Key.Key_X:
            focus_land = self.game.mine_field.get_focus()
            if focus_land is not None:
                focus_land.ui.right_click()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.game.load(file_path)
                self.activateWindow()
                break

    def wheelEvent(self, event):
        angle_delta = event.angleDelta().y()
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            self.button_size = max(1, self.button_size + int(angle_delta / abs(angle_delta)))
            self.game.mine_field.ui_setup()
            self.update_title()
            self.update_time_label()
        else:
            self.ui_opacity = max(2, min(self.ui_opacity + int(angle_delta / 5), self.ui_opacity_max))
            self.setWindowOpacity(self.ui_opacity / self.ui_opacity_max)

    def closeEvent(self, event):
        self.game.stop_looper()
        if self.game.bot and self.game.bot.auto_solving:
            self.game.bot.result.stop_solving.emit()
        event.accept()

    def event(self, event):
        if isinstance(event, QEvent):
            if event.type() == QEvent.Type.WindowActivate:
                self.ui_activated = True
                self.ui_opacity = min(self.ui_opacity * 2, self.ui_opacity_max)
                self.setWindowOpacity(self.ui_opacity / self.ui_opacity_max)
            elif event.type() == QEvent.Type.WindowDeactivate:
                self.ui_activated = False
                self.ui_opacity = max(1, int(self.ui_opacity / 2))
                self.setWindowOpacity(self.ui_opacity / self.ui_opacity_max)
            return super().event(event)
        else:
            # print(event, event.__dir__(), event.__dict__)
            return False

    def bot_highlight(self, land, _type):  # <-- bot
        land.ui.highlight(_type)
        self.game.bot.result.game_update_completed.emit()  # --> bot


def main():
    game = Game()
    game.ui_init()
    game.new_game_setup(
        field_width=PRESET[0][0],
        field_height=PRESET[0][1],
        mine_count=PRESET[0][2],
    )
    game.wait_for_exit()


class Bot(QRunnable):
    class Result(QObject):
        click = Signal(object)  # --> Master
        random_click = Signal(object)  # --> Master
        mark = Signal(object)  # --> Master
        highlight = Signal(object, str)  # --> Master
        custom_cover_ui = Signal(object, str, str)  # --> Master
        emote = Signal(str)   # --> Master
        message = Signal(str)  # --> Master

        game_update_completed = Signal()  # Master ->
        stop_solving = Signal()  # Master ->
        bot_finished = Signal()  # Master ->

    auto_click = False
    auto_mark = False
    # auto_random_click = False
    auto_step = -1
    random_step = 0
    game_updating = False

    auto_solving = False
    condition_list = list()
    condition_id_list = list()
    result = None

    data_before_solve = None

    debug_print = False

    def __init__(self):
        super().__init__()
        self.setAutoDelete(False)
        self.result = Bot.Result()
        self.result.game_update_completed.connect(self.game_update_completed)
        self.result.stop_solving.connect(self.stop_solving)

    def game_update_completed(self):
        if Game().game_terminated:
            self.auto_solving = False
        self.game_updating = False

    def stop_solving(self):
        self.auto_solving = False

    @Slot()
    def run(self):
        self.auto_solving = True
        self.game_updating = False
        while self.auto_solving and self.auto_step != 0:
            self.data_before_solve = Game().mine_field.save()
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
        # print("[Bot] Try to analyse ...")
        if len(self.condition_list) == 0:
            if self.auto_click:
                self.result.emote.emit(":D")
                return self.random_click(is_first_click=True)
            else:
                print("[Bot] No conclusion found.")
                self.result.emote.emit(":(")
                self.result.message.emit(f"No conclusion found")
                return False
        land_id, have_mine = self.analyse_condition()
        if land_id is not None:
            land = Game().mine_field.land(land_id)
            if not have_mine:
                if self.auto_click:
                    self.result.click.emit(land)
                else:
                    print(f"[Bot] ({land.x}, {land.y}) {land.id} is empty")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) is empty")
                    self.result.highlight.emit(land, "safe")
            else:
                if self.auto_mark:
                    self.result.mark.emit(land)
                else:
                    print(f"[Bot] ({land.x}, {land.y}) {land.id} have mine")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) have mine")
                    self.result.highlight.emit(land, "danger")
            self.result.emote.emit(":D")
            if self.debug_print:
                for cond in self.condition_list:
                    print(cond)
            return True
        else:
            self.result.emote.emit(":(")
            possible_mine_list, possible_safe_list, possibility_dict = self.analyse_possibility()

            mine_field = Game().mine_field
            # if self.auto_random_click:
            if self.random_step == -1 or self.random_step > 0:
                if self.random_step > 0:
                    self.random_step -= 1

                if len(possible_safe_list) > 0:
                    choice_list = possible_safe_list
                else:
                    choice_list = [land.id for land in mine_field.land_list if not land.checked and land.cover not in [
                        SYMBOL_FLAG,
                        SYMBOL_UNKNOWN,
                    ]]
                    if len(choice_list) > len(possible_mine_list):
                        choice_list = [land_id for land_id in choice_list[:] if land_id not in possible_mine_list]

                # print("choice_list", len(choice_list))

                if choice_list[0] in possibility_dict and possibility_dict[choice_list[0]] > 0.3:  # >= 1/3
                    mark_count = dict()
                    min_mark_count = mine_field.mine_count
                    for land_id in choice_list:
                        mark_count[land_id] = mine_field.row_mark_count(land_id) + mine_field.col_mark_count(land_id)
                        min_mark_count = min(min_mark_count, mark_count[land_id])
                    # choice_list = sorted(choice_list, key=lambda x: mark_count[x])
                    # for land_id in choice_list:
                    #     print(land_id, mark_count[land_id])
                    choice_list = [x for x in choice_list[:] if mark_count[x] == min_mark_count]
                    # print("choice_list filter by mine count", len(choice_list), choice_list)

                return self.random_click(
                   choice_list=choice_list,
                )
            else:
                print("[Bot] No conclusion found.")
                self.result.message.emit(f"No conclusion found")
                return False

    def collect_condition(self):
        mine_field = Game().mine_field
        self.condition_list = list()
        self.condition_id_list = list()
        land_list = mine_field.land_list[:]
        # shuffle(land_list)
        for land in land_list:
            if land.checked and land.adjacent_mine_count != 0:
                x, y = land.x, land.y
                condition = {
                    "id": "",
                    "land": land.id,
                    "possible_mine": land.adjacent_mine_count,
                    "adj_land": list(),
                }
                for _x, _y in itertools.product([-1, 0, 1], [-1, 0, 1]):
                    if _x == 0 and _y == 0:
                        continue
                    if 0 <= x + _x < mine_field.field_width and 0 <= y + _y < mine_field.field_height:
                        adj_land = mine_field.land((x + _x) + mine_field.field_width * (y + _y))
                        if not adj_land.checked:
                            if adj_land.cover != SYMBOL_FLAG:
                                condition["adj_land"].append(adj_land.id)
                            else:
                                condition["possible_mine"] -= 1

                if condition["possible_mine"] > 0 or len(condition["adj_land"]) > 0:
                    self.condition_list.append(condition)
        for cond in self.condition_list:
            cond["id"] = f"{cond["land"]}:{",".join([str(x) for x in cond["adj_land"]])}"
            self.condition_id_list.append(cond["id"])
        shuffle(self.condition_list)

    def random_click(self, is_first_click=False, choice_list=None):
        mine_field = Game().mine_field
        if choice_list is not None:
            land_list = [land for land in mine_field.land_list if land.id in choice_list]
        else:
            land_list = [land for land in mine_field.land_list if not land.checked and land.cover not in [
                SYMBOL_FLAG,
                SYMBOL_UNKNOWN,
            ]]
        x = randint(0, len(land_list) - 1)
        if is_first_click:
            self.result.click.emit(land_list[x])
        else:
            if self.debug_print:
                print("[Bot] Random Click")
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
                if cond_a["land"] == cond_b["land"]:
                    continue
                if self.is_include(cond_a["adj_land"], cond_b["adj_land"], lambda x: x):
                    if cond_a["possible_mine"] == cond_b["possible_mine"]:
                        if len(cond_a["adj_land"]) != len(cond_b["adj_land"]):
                            empty_land = self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x)[0][0]
                            return empty_land, False

                    else:  # cond_a["possible_mine"] != cond_b["possible_mine"]
                        possible_mine_land, cond_a_new_adj, cond_b_new_adj = \
                            self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x)
                        if abs(cond_a["possible_mine"] - cond_b["possible_mine"]) \
                                == abs(len(cond_a["adj_land"]) - len(cond_b["adj_land"])):
                            return possible_mine_land[0], True
                        elif len(cond_a_new_adj) > 0:
                            cond_a_new = cond_a.copy()
                            cond_a_new.update({
                                "id": f"sub_{cond_a_new["land"]}:{",".join([str(x) for x in cond_a_new_adj])}",
                                "adj_land": cond_a_new_adj,
                                "possible_mine": cond_a["possible_mine"] - cond_b["possible_mine"],
                            })
                            if cond_a_new["id"] not in self.condition_id_list:
                                self.condition_list.append(cond_a_new)
                                self.condition_id_list.append(cond_a_new["id"])
                                condition_updated = True
                        else:  # len(cond_b_new_adj) > 0:
                            cond_b_new = cond_b.copy()
                            cond_b_new.update({
                                "id": f"sub_{cond_b_new["land"]}:{",".join([str(x) for x in cond_b_new_adj])}",
                                "adj_land": cond_b_new_adj,
                                "possible_mine": cond_b["possible_mine"] - cond_a["possible_mine"],
                            })
                            if cond_b_new["id"] not in self.condition_id_list:
                                self.condition_list.append(cond_b_new)
                                self.condition_id_list.append(cond_b_new["id"])
                                condition_updated = True
            if not condition_updated:
                break
        return None, None

    def analyse_possibility(self) -> (list, list, dict, ):
        mine_field = Game().mine_field
        cover_land_count = mine_field.field_width * mine_field.field_height \
            - mine_field.revealed_land_count() - mine_field.marked_land_count()
        cover_mine_count = mine_field.mine_count - mine_field.marked_land_count()
        avg_mine_rate = cover_mine_count / cover_land_count
        max_mine_rate, min_mine_rate = avg_mine_rate, avg_mine_rate
        all_adj_land_list = dict()
        for condition in self.condition_list:
            for land in condition["adj_land"]:
                if land not in all_adj_land_list:
                    all_adj_land_list[land] = {
                        "id": land,
                        "mine_rate": avg_mine_rate,
                    }
        for condition in self.condition_list:
            cond_mine_rate = condition["possible_mine"] / len(condition["adj_land"])
            for land in condition["adj_land"]:
                if cond_mine_rate >= 0.5:
                    if cond_mine_rate > all_adj_land_list[land]["mine_rate"]:
                        all_adj_land_list[land]["mine_rate"] = cond_mine_rate
                else:
                    if all_adj_land_list[land]["mine_rate"] >= 0.5:
                        pass
                    elif abs(cond_mine_rate - avg_mine_rate) > abs(all_adj_land_list[land]["mine_rate"] - avg_mine_rate):
                        all_adj_land_list[land]["mine_rate"] = cond_mine_rate
        for _id, land in all_adj_land_list.items():
            max_mine_rate = max(max_mine_rate, land["mine_rate"])
            min_mine_rate = min(min_mine_rate, land["mine_rate"])
        high_mine_rate_list, high_safe_rate_list, rate_dict = list(), list(), dict()
        for _id, land in all_adj_land_list.items():
            cover = "{:.2f}" \
                .format(land["mine_rate"]) \
                .replace("0.", ".") \
                .replace("1.00", "1.0")
            if land["mine_rate"] == max_mine_rate:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(mine_field.land(_id), cover, "#e08080")
                high_mine_rate_list.append(_id)
                rate_dict[_id] = land["mine_rate"]
            elif land["mine_rate"] == min_mine_rate:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(mine_field.land(_id), cover, "#80e080")
                high_safe_rate_list.append(_id)
                rate_dict[_id] = land["mine_rate"]
            else:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(mine_field.land(_id), cover, "#909090")
        avg_cover = "{:.2f}" \
            .format(avg_mine_rate) \
            .replace("0.", ".") \
            .replace("1.00", "1.0")
        for land in mine_field.land_list:
            if land.checked or land.cover != SYMBOL_BLANK or land.id in all_adj_land_list:
                continue
            if max_mine_rate == avg_mine_rate:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(land, avg_cover, "#e08080")
                high_mine_rate_list.append(land.id)
                rate_dict[land.id] = avg_mine_rate
            elif min_mine_rate == avg_mine_rate:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(land, avg_cover, "#80e080")
                high_safe_rate_list.append(land.id)
                rate_dict[land.id] = avg_mine_rate
            else:
                if Game().ui.ui_activated:
                    self.result.custom_cover_ui.emit(land, avg_cover, "#909090")

        print(f"[bot] "
              f"possible_mine_list: {len(high_mine_rate_list)} ({max_mine_rate:.2f}), "
              f"possible_safe_list: {len(high_safe_rate_list)} ({min_mine_rate:.2f}), "
              f"avg: {avg_mine_rate:.2f}")
        return high_mine_rate_list, high_safe_rate_list, rate_dict

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
                if not self.looping:
                    break
            if not self.looping:
                break

            for _ in range(1 * 10):
                time.sleep(0.1)
                if not self.looping:
                    break
            if not self.looping:
                break

            # print("[Looper] Init Map")
            self.map_initializing = True
            self.status.init_map.emit()
            while self.map_initializing:
                if not self.looping:
                    break
            if not self.looping:
                break

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
        if self.current < 0:
            self.create_record()
        self.record_list[self.current]["click"] += 1

    def record_mark(self):
        if self.current < 0:
            self.create_record()
        self.record_list[self.current]["mark"] += 1

    def record_random_click(self):
        if self.current < 0:
            self.create_record()
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
