
from PySide6.QtCore import QObject, Qt, QRunnable, Slot, QThreadPool, Signal
from PySide6.QtGui import QIcon, QPixmap, QAction, QIntValidator
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtWidgets import QWidget, QGridLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit
from random import randint

import datetime
import itertools
import sys
import time

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
            border: 2px solid #a02020;
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
            border: 2px solid #a02020;
            background-color: #434343;
        }
        QPushButton:pressed {
            border: 2px solid #a02020;
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


class MineField(QWidget):
    field_width = 0
    field_height = 0
    mine_count = 0

    land_list = list()

    def __init__(self, parent, field_width=9, field_height=9, mine_count=10):
        super().__init__(parent)
        self.field_width = min(max(9, field_width), 1000)
        self.field_height = min(max(3, field_height), 1000)
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
            self.parent().set_message("YOU LOSE")
            for land in self.land_list:
                if land.have_mine:
                    land.cover = SYMBOL_MINE
                    land.update_ui()
        elif self.revealed_land_count() == self.field_width * self.field_height - self.mine_count:
            MainWindow().game_terminated = True
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
    width = 9
    height = 9
    mine = 10

    mine_validator = None
    width_edit = None
    height_edit = None
    mine_edit = None
    difficulty_label = "10%"

    def __init__(self, parent, width, height, mine):
        super().__init__(parent)

        self.width = width
        self.height = height
        self.mine = mine

        self.setWindowTitle("Custom Mine Field")

        size_validator = QIntValidator()
        size_validator.setRange(9, 1000)

        self.mine_validator = QIntValidator()

        self.width_edit = NumberLineEdit()
        self.width_edit.setText(str(self.width))
        self.width_edit.setValidator(size_validator)
        self.width_edit.textChanged.connect(self.width_change)

        self.height_edit = NumberLineEdit()
        self.height_edit.setText(str(self.height))
        self.height_edit.setValidator(size_validator)
        self.height_edit.textChanged.connect(self.height_change)

        self.mine_edit = NumberLineEdit()
        self.mine_edit.setText(str(self.mine))
        self.mine_edit.setValidator(self.mine_validator)
        self.mine_edit.textChanged.connect(self.mine_change)

        self.difficulty_label = QLabel()

        self.update_variable()

        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.confirm)

        grid = QGridLayout()

        grid.addWidget(QLabel("Width:"), 1, 1)
        grid.addWidget(self.width_edit, 1, 2)

        grid.addWidget(QLabel("Height:"), 2, 1)
        grid.addWidget(self.height_edit, 2, 2)

        grid.addWidget(QLabel("Mines:"), 3, 1)
        grid.addWidget(self.mine_edit, 3, 2)

        grid.addWidget(QLabel("Difficulty:"), 4, 1)
        grid.addWidget(self.difficulty_label, 4, 2)

        grid.addWidget(confirm, 5, 1, 1, 2)

        self.setLayout(grid)

    def width_change(self):
        try:
            self.width = int(self.width_edit.text())
        except ValueError:
            self.width = 9
        self.update_variable()

    def height_change(self):
        try:
            self.height = int(self.height_edit.text())
        except ValueError:
            self.height = 9
        self.update_variable()

    def mine_change(self):
        try:
            self.mine = int(self.mine_edit.text())
        except ValueError:
            self.mine = 10
        self.update_variable()

    def update_variable(self):
        self.mine_validator.setRange(1, (self.width - 1) * (self.height - 1))
        self.difficulty_label.setText(f"{self.mine / (self.width * self.height) * 100:.2f}%")

    def confirm(self):
        self.parent().init_mine_field(self.width, self.height, self.mine)
        self.done(0)


@singleton
class MainWindow(QMainWindow):
    mine_field = None
    game_terminated = False
    cheat_mode = False

    app = None
    emote = ""
    menu_action_dict = dict()
    status = ""

    ai = None
    ai_looper = None
    ai_pool = None
    ai_start_time = None

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.init_window()

        self.init_mine_field()

        self.ai = AI()
        self.ai.result.click.connect(self.ai_click)
        self.ai.result.mark.connect(self.ai_mark)
        self.ai.result.emote.connect(self.set_emote)
        self.ai.result.message.connect(self.set_message)
        self.ai.result.ai_finished.connect(self.ai_finished)

        self.ai_looper = AILooper()
        self.ai_looper.status.init_map.connect(self.init_mine_field)
        self.ai_looper.status.start_ai.connect(self.start_ai)

        self.ai_pool = QThreadPool()
        self.ai_pool.setMaxThreadCount(20)

    def init_window(self):
        self.setWindowFlags(Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        self.move(700, 1700)
        icon = QIcon()
        icon.addPixmap(QPixmap("Mine.ico"))
        self.setWindowIcon(icon)

        menu = self.menuBar()
        # Menu: Game
        game_menu = menu.addMenu("&Game")
        game_menu.addAction(
            self.create_menu_action(
                "New Game", "New Game", Qt.Key.Key_R, self.re_init_mine_field))
        game_menu.addSeparator()
        # Menu: Game -> Difficulty
        difficulty_menu = game_menu.addMenu("Difficulty")
        difficulty_menu.addAction(
            self.create_menu_action(
                "Easy", "10 x 10 with 9 mines", Qt.Key.Key_Q, self.init_easy_mine_field))
        difficulty_menu.addAction(
            self.create_menu_action(
                "Middle", "16 x 16 with 40 mines", Qt.Key.Key_W, self.init_middle_mine_field))
        difficulty_menu.addAction(
            self.create_menu_action(
                "Hard", "30 x 16 with 99 mines", Qt.Key.Key_E, self.init_hard_mine_field))
        game_menu.addSeparator()
        difficulty_menu.addAction(
            self.create_menu_action(
                "Custom...", "Custom field size and mine number",
                Qt.Key.Key_C, self.custom_mine_field))
        game_menu.addSeparator()
        game_menu.addAction(
            self.create_menu_action(
                "Exit", "Exit the game", Qt.Key.Key_Escape, self.exit))
        # Menu: Bot
        bot_menu = menu.addMenu("&Bot")
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Click", "Auto click if empty land found when solving",
                Qt.Key.Key_A, self.ai_switch_auto_click, check_able=True))
        bot_menu.addAction(
            self.create_menu_action(
                "Auto Random Click", "Auto random click if no empty land found when solving",
                Qt.Key.Key_S, self.ai_switch_auto_random_click, check_able=True))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "Random Click Once", "Auto click a random unmarked land",
                Qt.Key.Key_D, self.ai_random_click))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve One Step", "Try to solve current game one step",
                Qt.Key.Key_F, self.ai_solve_once))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Current Game", "Try to solve current game until win or lose",
                Qt.Key.Key_G, self.ai_solve))
        bot_menu.addAction(
            self.create_menu_action(
                "Solve Continuously", "Try to solve games continuously",
                Qt.Key.Key_H, self.ai_solve_looping))
        bot_menu.addSeparator()
        bot_menu.addAction(
            self.create_menu_action(
                "Statistic ...", "Show solving record (TODO)"))
        menu.addAction(
            self.create_menu_action(
                "&About", "Go to project home page",
                trigger=self.about))

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

    def re_init_mine_field(self):
        self.stop_looper()
        if not self.cheat_mode:
            self.init_mine_field()
        else:
            self.mine_field.reset_mine_field()
            self.game_terminated = False

    def init_easy_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(9, 9, 10)

    def init_middle_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(16, 16, 40)

    def init_hard_mine_field(self):
        self.stop_looper()
        return self.init_mine_field(30, 16, 99)

    def custom_mine_field(self):
        field_size = self.mine_field.field_size()
        dialog = CustomFieldDialog(
            self, field_size["field_width"], field_size["field_height"], field_size["mine_count"])
        dialog.exec()

    def ai_switch_auto_click(self):
        self.stop_looper()
        self.ai.auto_click = not self.ai.auto_click
        print(f"AUTO_CLICK: {self.ai.auto_click}")

    def ai_switch_auto_random_click(self):
        self.stop_looper()
        self.ai.auto_random_click = not self.ai.auto_random_click
        print(f"AUTO_RAMDOM_CLICK: {self.ai.auto_random_click}")

    def ai_random_click(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.ai.random_click()

    def ai_solve_once(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.start_ai(step=1)

    def ai_solve(self):
        self.stop_looper()
        if not MainWindow().game_terminated:
            self.start_ai()

    def ai_solve_looping(self):
        self.ai_looper.looping = not self.ai_looper.looping
        if self.ai_looper.looping:
            self.start_looper()
        else:
            self.stop_looper()

    @staticmethod
    def about():
        import webbrowser
        webbrowser.open("https://github.com/Qionglu735/MineSweeperBot")

    def exit(self):
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

        if self.ai_looper is not None and self.ai_looper.looping:
            self.ai_looper.status.map_ready.emit()  # --> ai_looper

    def keyPressEvent(self, event):
        # if event.key() < 256:
        #     print(chr(event.key()))
        # else:
        #     print(event.key())

        modifiers = QApplication.keyboardModifiers()
        
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_R:
            if not self.cheat_mode:
                self.init_mine_field()
            else:
                self.mine_field.reset_mine_field()
                self.game_terminated = False

        elif event.key() == Qt.Key.Key_U:
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
        self.exit()

    def start_ai(self, step=-1):
        self.ai.auto_step = step
        self.ai_start_time = datetime.datetime.now()
        self.ai_pool.start(self.ai)

    def ai_click(self, land):  # <-- ai
        land.auto_click()
        self.ai.result.game_update_completed.emit()  # --> ai

    def ai_mark(self, land):  # <-- ai
        land.auto_mark()
        self.ai.result.game_update_completed.emit()  # --> ai

    def ai_finished(self):  # <-- ai
        time_delta = datetime.datetime.now() - self.ai_start_time
        print(f"Usage Time: {time_delta.seconds}.{time_delta.microseconds}")
        if self.ai_looper.looping:
            self.ai_looper.status.ai_finished.emit()  # --> ai_looper

    def start_looper(self):
        self.ai.auto_click = True
        self.menu_action_dict["Auto Click"].setChecked(True)
        self.ai.auto_random_click = True
        self.menu_action_dict["Auto Random Click"].setChecked(True)
        self.ai_pool.start(self.ai_looper)

    def stop_looper(self):
        self.ai_looper.status.stop_looping.emit()  # --> ai_looper


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    MainWindow(app).show()
    sys.exit(app.exec())


class AI(QRunnable):
    class Result(QObject):
        click = Signal(object)  # --> Master
        mark = Signal(object)  # --> Master
        emote = Signal(str)   # --> Master
        message = Signal(str)  # --> Master

        game_update_completed = Signal()  # Master ->
        game_terminated = Signal()  # Master ->
        ai_finished = Signal()  # Master ->

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
        self.result = AI.Result()
        self.result.game_update_completed.connect(self.game_update_completed)

    def game_update_completed(self):
        if MainWindow().game_terminated:
            self.auto_solving = False
        self.game_updating = False

    @Slot()
    def run(self):
        self.auto_solving = True
        self.game_updating = False
        while self.auto_solving and self.auto_step != 0:
            self.game_updating = True
            self.auto_solving = self.solve()
            if self.auto_step > 0:
                self.auto_step -= 1
            while self.auto_solving and self.auto_step != 0 and self.game_updating:
                # wait until game update completed
                pass
        self.result.ai_finished.emit()

    def solve(self):
        self.collect_condition()
        # print("[AI]Try to analyse ...")
        if len(self.condition_list) == 0:
            self.result.emote.emit(":(")
            if self.auto_click:
                return self.random_click()
            else:
                print("[AI] No conclusion found.")
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
                    print(f"[AI] ({land.x}, {land.y}) is empty")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) is empty")
                else:
                    print(f"[AI] ({land.x}, {land.y}) have mine")
                    self.result.message.emit(f"({land.x + 1}, {land.y + 1}) have mine")
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
                print("[AI] No conclusion found.")
                return False
    
    def collect_condition(self):
        mine_field = MainWindow().mine_field
        self.condition_list = list()
        for land in mine_field.land_list:
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

    def random_click(self):
        print("[AI] Random Click")
        mine_field = MainWindow().mine_field
        land_list = [land for land in mine_field.land_list if not land.checked and land.cover == SYMBOL_BLANK]
        if len(land_list) == 0:
            return False
        x = randint(0, len(land_list) - 1)
        self.result.click.emit(land_list[x])
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


class AILooper(QRunnable):
    class Status(QObject):
        init_map = Signal()         # --> Master
        map_ready = Signal()        # Master -->
        start_ai = Signal()         # --> Master
        ai_finished = Signal()      # Master -->
        stop_looping = Signal()     # Master -->

    status = None

    looping = False
    map_initializing = False
    ai_running = False

    def __init__(self):
        super().__init__()
        self.status = AILooper.Status()
        self.status.map_ready.connect(self.map_ready)
        self.status.ai_finished.connect(self.ai_finished)
        self.status.stop_looping.connect(self.stop_looping)

    def map_ready(self):
        self.map_initializing = False

    def ai_finished(self):
        self.ai_running = False

    def stop_looping(self):
        self.looping = False

    @Slot()
    def run(self):
        self.looping = True
        while self.looping:
            # print("[Looper] Start AI")
            self.ai_running = True
            self.status.start_ai.emit()
            while self.ai_running:
                pass
            if not self.looping:
                break
            time.sleep(3)
            # print("[Looper] Init Map")
            self.map_initializing = True
            self.status.init_map.emit()
            while self.map_initializing:
                pass
            time.sleep(1)


if __name__ == '__main__':
    main()
