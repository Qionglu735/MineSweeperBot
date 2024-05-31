
from random import randint
from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget,  QGridLayout, QPushButton

import datetime
import itertools
import sys

MAP_X = 9
MAP_Y = 9
MINE_COUNT = 10

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

    def __init__(self, parent, x, y):
        super().__init__(text=SYMBOL_BLANK)

        self.x, self.y = x, y
        self.id = x + parent.field_width * y
        
        self.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        q_font = QtGui.QFont("Roman Times", 10)
        q_font.setBold(True)
        self.setFont(q_font)
        self.setToolTip(str(x + MAP_X * y) + "(" + str(x) + ", " + str(y) + ")")
        
        self.setCheckable(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
    
    def left_click(self):

        mine_field = self.parent()

        field_width = self.parent().field_width
        field_height = self.parent().field_height

        # if MainWindow().game_terminated or not MainWindow().game_terminated and self.cover != SYMBOL_BLANK:
        #     if self.isChecked():
        #         self.setChecked(False)
        #     else:
        #         self.setChecked(True)
        if self.isChecked():
            print(f"Left Click ({self.x}, {self.y})")
            if len([x for x in mine_field.land_list if x.have_mine is True]) == 0:
                mine_field.generate_mine(self.x, self.y)

            self.setText(self.content)
            self.parent().check_end_game(self.x, self.y)
            if not MainWindow().game_terminated and self.content == SYMBOL_BLANK:
                for _x in [-1, 0, 1]:
                    for _y in [-1, 0, 1]:
                        if _x == 0 and _y == 0:
                            continue
                        if 0 <= self.x + _x < field_width and 0 <= self.y + _y < field_height:
                            land = self.parent().land_list[(self.x + _x) + field_width * (self.y + _y)]
                            if not land.isChecked():
                                land.left_click()
                self.parent().check_end_game(self.x, self.y)
        else:
            # print(f"Chain Click ({self.x}, {self.y})")
            self.setChecked(True)
            self.setText(self.content)
            flag_num = 0
            for x in [-1, 0, 1]:
                for y in [-1, 0, 1]:
                    if x == 0 and y == 0:
                        continue
                    if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                        land = self.parent().land_list[(self.x + x) + field_width * (self.y + y)]
                        if not land.isChecked() and land.cover == SYMBOL_FLAG:
                            flag_num += 1
            if flag_num == self.adjacent_mine_count:
                for x in [-1, 0, 1]:
                    for y in [-1, 0, 1]:
                        if x == 0 and y == 0:
                            continue
                        if 0 <= self.x + x < field_width and 0 <= self.y + y < field_height:
                            land = self.parent().land_list[(self.x + x) + field_width * (self.y + y)]
                            if not land.isChecked() and land.cover != SYMBOL_FLAG:
                                land.left_click()

        if not MainWindow().game_terminated:
            mine_field = self.parent()
            MainWindow().show_message(f"{mine_field.mine_count - mine_field.marked_land_count()} mines remained")

    def auto_left_click(self):
        print(f"Auto Left Click ({self.x}, {self.y})")
        self.setChecked(True)
        self.left_click()
    
    def right_click(self):
        if not MainWindow().game_terminated:
            print(f"Right Click ({self.x}, {self.y})")
            if not self.isChecked():
                if self.cover == SYMBOL_BLANK:
                    self.cover = SYMBOL_FLAG
                elif self.cover == SYMBOL_FLAG:
                    self.cover = SYMBOL_UNKNOWN
                elif self.cover == SYMBOL_UNKNOWN:
                    self.cover = SYMBOL_BLANK
                self.setText(self.cover)
            # else:
            #     if not MainWindow().cheat_mode:
            #         self.setChecked(True)
            mine_field = self.parent()
            MainWindow().show_message(f"{mine_field.mine_count - mine_field.marked_land_count()} mines remained")
    
    def auto_mark(self):
        print(f"Auto Mark ({self.x}, {self.y})")
        while not MainWindow().game_terminated and self.cover != SYMBOL_FLAG:
            self.right_click()
    
    def reveal(self, flag):
        if self.have_mine:
            if flag:
                self.setToolTip(f"! {self.x + MAP_X * self.y}({self.x}, {self.y}) !")
            else:
                self.setToolTip(f"{self.x + MAP_X * self.y}({self.x}, {self.y})")

    def to_string(self):
        return f"{self.id} ({self.x}, {self.y})"


class MineField(QWidget):
    field_width = 0
    field_height = 0
    mine_count = 0

    land_list = list()

    def __init__(self, field_width=MAP_X, field_height=MAP_Y, mine_count=MINE_COUNT):
        super().__init__()
        self.field_width = min(max(9, field_width), 1000)
        self.field_height = min(max(9, field_height), 1000)
        self.mine_count = min(max(1, mine_count), self.field_width * self.field_height - 9)
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
                self.land_list.append(land)
                grid.addWidget(land, y, x)

        self.setLayout(grid)

    def reset_mine_field(self):
        for land in self.land_list:
            land.setChecked(False)
            land.cover = SYMBOL_BLANK
            land.setText(land.cover)

    def generate_mine(self, safe_x=-9, safe_y=-9):
        for x in range(self.field_width):
            for y in range(self.field_height):
                self.land_list[x + self.field_width * y].have_mine = False
                self.land_list[x + self.field_width * y].adjacent_mine_count = 0
                self.land_list[x + self.field_width * y].checked = False
                self.land_list[x + self.field_width * y].cover = SYMBOL_BLANK
                self.land_list[x + self.field_width * y].content = SYMBOL_BLANK
                self.land_list[x + self.field_width * y].setChecked(False)
                self.land_list[x + self.field_width * y].setText(SYMBOL_BLANK)

        for _ in range(self.mine_count):
            x, y = -1, -1
            while x < 0 or y < 0 or self.land_list[x + self.field_width * y].have_mine:
                x = randint(0, self.field_width - 1)
                y = randint(0, self.field_height - 1)
                if abs(x - safe_x) <= 1 and abs(y - safe_y) <= 1:
                    x, y = -1, -1
            self.land_list[x + self.field_width * y].have_mine = True
            for _x in [-1, 0, 1]:
                for _y in [-1, 0, 1]:
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
        return len([x for x in self.land_list if x.isChecked()])

    def marked_land_count(self):
        return len([x for x in self.land_list if not x.isChecked() and x.cover == SYMBOL_FLAG])

    def check_end_game(self, x, y):
        if self.land_list[x + self.field_width * y].have_mine:
            MainWindow().game_terminated = True
            self.parent().show_message("YOU FAILED")
            for land in self.land_list:
                if land.have_mine:
                    # land.cover = SYMBOL_MINE
                    land.setText(SYMBOL_MINE)
        elif self.revealed_land_count() == self.field_width * self.field_height - self.mine_count:
            MainWindow().game_terminated = True
            self.parent().show_message("YOU WIN")
            for y in range(self.field_height):
                for x in range(self.field_width):
                    if self.land_list[x + self.field_width * y].have_mine:
                        self.land_list[x + self.field_width * y].cover = SYMBOL_FLAG
                        self.land_list[x + self.field_width * y].setText(SYMBOL_FLAG)
    
    def left_click(self):
        self.sender().left_click()
    
    def right_click(self):
        self.sender().right_click()


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


@singleton
class MainWindow(QMainWindow):
    mine_field = None
    game_terminated = False

    cheat_mode = False
    auto_click = False
    auto_random_click = False

    status = ""

    def __init__(self):
        super().__init__()
        self.init_ui()
     
    def init_ui(self):
        # self.setWindowFlag(QtCore.Qt.WindowType.WindowMinimizeButtonHint)
        self.move(900, 1800)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("Mine.ico"))
        self.setWindowIcon(icon)

        self.init_mine_field()

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

        self.mine_field = MineField(**field_size)
        self.game_terminated = False

        self.setCentralWidget(self.mine_field)
        self.adjustSize()
        self.setWindowTitle(
            f"{self.mine_field.field_width} "
            f"X {self.mine_field.field_height} "
            f"with {self.mine_field.mine_count} Mines :)"
        )
        self.show_message("New Game Ready")
    
    def show_message(self, msg):
        self.statusBar().showMessage(self.status + msg)
    
    def set_status(self, status):
        self.status = status
        self.statusBar().showMessage(self.status)
    
    def keyPressEvent(self, event):
        # if event.key() < 256:
        #     print(chr(event.key()))
        # else:
        #     print(event.key())

        modifiers = QApplication.keyboardModifiers()
        
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif event.key() == QtCore.Qt.Key.Key_R:
            if not self.cheat_mode:
                self.init_mine_field()
            else:
                self.mine_field.reset_mine_field()
                self.game_terminated = False
        elif event.key() == QtCore.Qt.Key.Key_Q:
            self.init_mine_field(9, 9, 10)
        elif event.key() == QtCore.Qt.Key.Key_W:
            self.init_mine_field(16, 16, 40)
        elif event.key() == QtCore.Qt.Key.Key_E:
            self.init_mine_field(30, 16, 99)

        elif event.key() == QtCore.Qt.Key.Key_Y:
            new_width = self.mine_field.field_width + 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_width = self.mine_field.field_width + 5
            self.init_mine_field(field_width=new_width)
        elif event.key() == QtCore.Qt.Key.Key_U:
            new_width = self.mine_field.field_width - 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_width = self.mine_field.field_width - 5
            self.init_mine_field(field_width=new_width)

        elif event.key() == QtCore.Qt.Key.Key_H:
            new_height = self.mine_field.field_height + 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_height = self.mine_field.field_height + 5
            self.init_mine_field(field_height=new_height)
        elif event.key() == QtCore.Qt.Key.Key_J:
            new_height = self.mine_field.field_height - 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_height = self.mine_field.field_height - 5
            self.init_mine_field(field_height=new_height)

        elif event.key() == QtCore.Qt.Key.Key_N:
            new_count = self.mine_field.mine_count + 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_count = self.mine_field.mine_count + 5
            self.init_mine_field(mine_count=new_count)
        elif event.key() == QtCore.Qt.Key.Key_M:
            new_count = self.mine_field.mine_count - 1
            if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_count = self.mine_field.mine_count - 5
            self.init_mine_field(mine_count=new_count)

        elif event.key() == QtCore.Qt.Key.Key_T:
            self.cheat_mode = not self.cheat_mode
            print(f"CHEAT_MODE: {self.cheat_mode}")
            for land in self.mine_field.land_list:
                land.reveal(self.cheat_mode)

        elif event.key() == QtCore.Qt.Key.Key_A:
            self.auto_click = not self.auto_click
            print(f"AUTO_CLICK: {self.auto_click}")
        elif event.key() == QtCore.Qt.Key.Key_S:
            self.auto_random_click = not self.auto_random_click
            print(f"AUTO_RAMDOM_CLICK: {self.auto_random_click}")

        elif event.key() == QtCore.Qt.Key.Key_D:
            AI().random_click(1)
        elif event.key() == QtCore.Qt.Key.Key_F:
            if not MainWindow().game_terminated:
                AI().solve(auto_click=self.auto_click, auto_random_click=self.auto_random_click)
        elif event.key() == QtCore.Qt.Key.Key_G:
            if not MainWindow().game_terminated:
                auto_solving = True
                start_time = datetime.datetime.now()
                while auto_solving and not self.game_terminated:
                    auto_solving = AI().solve(auto_click=self.auto_click, auto_random_click=self.auto_random_click)
                    # self.update()
                end_time = datetime.datetime.now()
                print(f"Usage Time: {(end_time - start_time).seconds}.{(end_time - start_time).microseconds}")

        # elif event.key() == QtCore.Qt.Key.Key_0:
        #     while AUTO_SOLVING:
        #         self.mine_field.generate_mine()
        #         self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MINE_COUNT) + " Mines" + " : )")
        #         self.show_message("New Game Ready")
        #         while AUTO_SOLVING and not GAME_TERMINATED:
        #             AUTO_SOLVING = AI().solve()
        #             self.update()


def main():
    # sys.argv += ['-platform', 'windows:darkmode=2']
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    MainWindow().show()
    sys.exit(app.exec())


class AI:
    condition_list = list()
    next_id = -1
    click_or_mark = 0

    debug_print = False

    def __init__(self):
        pass
    
    def solve(self, auto_click=False, auto_random_click=False):
        mine_field = MainWindow().mine_field
        self.collect_condition()
        # print("[AI]Try to analyse ...")
        land, have_mine = self.analyse_condition()
        if land is not None:
            if auto_click:
                if not have_mine:
                    land.auto_left_click()
                else:
                    land.auto_mark()
            else:
                if not have_mine:
                    print(f"[AI]({land.x}, {land.y}) is empty")
                    MainWindow().show_message(f"({land.x}, {land.y}) is empty")
                else:
                    print(f"[AI]({land.x}, {land.y}) have mine")
                    MainWindow().show_message(f"({land.x}, {land.y}) have mine")
            MainWindow().setWindowTitle(
                f"{mine_field.field_width} X {mine_field.field_height} with {mine_field.mine_count} Mines :D"
            )
            if self.debug_print:
                for cond in self.condition_list:
                    print({
                        "land": cond["land"].to_string(),
                        "possible_mine": cond["possible_mine"],
                        "adj_land": [land.to_string() for land in cond["adj_land"]],
                    })
            return True
        else:
            MainWindow().setWindowTitle(
                f"{mine_field.field_width} X {mine_field.field_height} with {mine_field.mine_count} Mines :(")
            if auto_random_click:
                return self.random_click(1)
            else:
                print("[AI]No conclusion found.")
                return False
    
    def collect_condition(self):
        mine_field = MainWindow().mine_field
        self.condition_list = list()
        for land in mine_field.land_list:
            if land.isChecked() and land.adjacent_mine_count != 0:
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
                        if not adj_land.isChecked():
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

    @staticmethod
    def random_click(num):
        print("[AI]Random Click")
        mine_field = MainWindow().mine_field
        land_list = [land for land in mine_field.land_list if not land.isChecked() and land.cover == SYMBOL_BLANK]
        if len(land_list) == 0:
            return False
        i = 0
        while i < num:
            x = randint(0, len(land_list) - 1)
            land_list[x].auto_left_click()
            del land_list[x]
            i += 1
        return True
    
    def analyse_condition(self):
        while True:
            for condition in self.condition_list:
                if condition["possible_mine"] == 0:
                    return condition["adj_land"][0], False

                elif condition["possible_mine"] == len(condition["adj_land"]):
                    return condition["adj_land"][0], True

            for cond_a,cond_b in itertools.product(self.condition_list, self.condition_list):
                if cond_a["land"].id >= cond_b["land"].id:
                    continue
                if cond_a["possible_mine"] == cond_b["possible_mine"] \
                        and len(cond_a["adj_land"]) != len(cond_b["adj_land"]) \
                        and self.is_include(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id):
                    empty_land = self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id)[0]
                    return empty_land, False

                elif cond_a["possible_mine"] != cond_b["possible_mine"] \
                        and abs(cond_a["possible_mine"] - cond_b["possible_mine"]) \
                        == abs(len(cond_a["adj_land"]) - len(cond_b["adj_land"])) \
                        and self.is_include(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id):
                    mine_land = self.sub(cond_a["adj_land"], cond_b["adj_land"], lambda x: x.id)[0]
                    return mine_land, True
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
            return _a
        else:
            return _b


if __name__ == '__main__':
    main()
