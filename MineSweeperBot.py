
from random import randint
from PySide6 import QtGui, QtCore, QtWidgets
import datetime
import sys

MAP_X = 16  # NW N NE
MAP_Y = 16  # W  O  E
MAP_Z = 40  # SW S SE
MAP = []

REVEALED_COUNT = 0
MARKED_COUNT = 0

TRICK_MODE = False
REVEALED = False
GAME_TERMINATED = False

AUTO_RANDOM_CLICK = False
AUTO_SOLVING = False

SYMBOL_BLANK = " "
SYMBOL_MINE = "O"
SYMBOL_FLAG = "!"
SYMBOL_UNKNOWN = "?"

BUTTON_SIZE = 20

ui = None


class Land(QtWidgets.QPushButton):
    def __init__(self, x, y):
        QtWidgets.QPushButton.__init__(self, SYMBOL_BLANK)
        
        self.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        q_font = QtGui.QFont("Roman Times", 10)
        q_font.setBold(True)
        self.setFont(q_font)
        self.setToolTip(str(x + MAP_X * y) + "(" + str(x) + ", " + str(y) + ")")
        
        self.setCheckable(True)
        # self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        
        self.x, self.y= x, y
        self.cover, self.content= SYMBOL_BLANK, SYMBOL_BLANK
        self.haveMine = False
        self.mine_num = 0
    
    def left_click(self):
        global GAME_TERMINATED
        if GAME_TERMINATED or (not GAME_TERMINATED and self.cover != SYMBOL_BLANK):
            if self.isChecked():
                self.setChecked(False)
            else:
                self.setChecked(True)
        elif self.isChecked():
            self.parent().button_set_text(self, self.content)
            global REVEALED_COUNT
            REVEALED_COUNT += 1
            self.parent().check_end_game(self.x, self.y)
            if not GAME_TERMINATED and self.content == " ":
                x, y = self.x, self.y
                tmpX, tmpY = [], []
                #NW
                if x - 1 >= 0 and y - 1 >= 0 and not MAP[(x - 1) + MAP_X * (y - 1)].isChecked():
                    MAP[(x - 1) + MAP_X * (y - 1)].setChecked(True)
                    tmpX.append(x - 1)
                    tmpY.append(y - 1)
                #W
                if x - 1 >= 0 and not MAP[(x - 1) + MAP_X * y].isChecked():
                    MAP[(x - 1) + MAP_X * y].setChecked(True)
                    tmpX.append(x - 1)
                    tmpY.append(y)
                #SW
                if x - 1 >= 0 and y + 1 <MAP_Y and not MAP[(x - 1) + MAP_X * (y + 1)].isChecked():
                    MAP[(x - 1) + MAP_X * (y + 1)].setChecked(True)
                    tmpX.append(x - 1)
                    tmpY.append(y + 1)
                #N
                if y - 1 >= 0 and not MAP[x + MAP_X * (y - 1)].isChecked():
                    MAP[x + MAP_X * (y - 1)].setChecked(True)
                    tmpX.append(x)
                    tmpY.append(y - 1)
                #S
                if y + 1 < MAP_Y and not MAP[x + MAP_X * (y + 1)].isChecked():
                    MAP[x + MAP_X * (y + 1)].setChecked(True)
                    tmpX.append(x)
                    tmpY.append(y + 1)
                #NE
                if x + 1 < MAP_X and y - 1 >= 0 and not MAP[(x + 1) + MAP_X * (y -1)].isChecked():
                    MAP[(x + 1) + MAP_X * (y -1)].setChecked(True)
                    tmpX.append(x + 1)
                    tmpY.append(y - 1)
                #E
                if x + 1 < MAP_X and not MAP[(x + 1) + MAP_X * y].isChecked():
                    MAP[(x + 1) + MAP_X * y].setChecked(True)
                    tmpX.append(x + 1)
                    tmpY.append(y)
                #SE
                if x + 1 < MAP_X and y + 1 < MAP_Y and not MAP[(x + 1) + MAP_X * (y + 1)].isChecked():
                    MAP[(x + 1) + MAP_X * (y + 1)].setChecked(True)
                    tmpX.append(x + 1)
                    tmpY.append(y + 1)
                for i in range(len(tmpX)):
                    MAP[tmpX[i] + MAP_X * tmpY[i]].left_click()
        else:
            self.setChecked(True)
            x, y = self.x, self.y
            flag_num = 0
            # NW
            if x - 1 >= 0 and y - 1 >= 0 and not MAP[(x - 1) + MAP_X * (y - 1)].isChecked() and MAP[(x - 1) + MAP_X * (y - 1)].cover == SYMBOL_FLAG:
                flag_num += 1
            # W
            if x - 1 >= 0 and not MAP[(x - 1) + MAP_X * y].isChecked() and MAP[(x - 1) + MAP_X * y].cover == SYMBOL_FLAG:
                flag_num += 1
            # SW
            if x - 1 >= 0 and y + 1 <MAP_Y and not MAP[(x - 1) + MAP_X * (y + 1)].isChecked() and MAP[(x - 1) + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                flag_num += 1
            # N
            if y - 1 >= 0 and not MAP[x + MAP_X * (y - 1)].isChecked() and MAP[x + MAP_X * (y - 1)].cover == SYMBOL_FLAG:
                flag_num += 1
            # S
            if y + 1 < MAP_Y and not MAP[x + MAP_X * (y + 1)].isChecked() and MAP[x + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                flag_num += 1
            # NE
            if x + 1 < MAP_X and y - 1 >= 0 and not MAP[(x + 1) + MAP_X * (y - 1)].isChecked() and MAP[(x + 1) + MAP_X * (y -1)].cover == SYMBOL_FLAG:
                flag_num += 1
            # E
            if x + 1 < MAP_X and not MAP[(x + 1) + MAP_X * y].isChecked() and MAP[(x + 1) + MAP_X * y].cover == SYMBOL_FLAG:
                flag_num += 1
            # SE
            if x + 1 < MAP_X and y + 1 < MAP_Y and not MAP[(x + 1) + MAP_X * (y + 1)].isChecked() and MAP[(x + 1) + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                flag_num += 1
            if flag_num == MAP[x + MAP_X * y].mine_num:
                # NW
                if x - 1 >= 0 and y - 1 >= 0 and not MAP[(x - 1) + MAP_X * (y - 1)].isChecked() and MAP[(x - 1) + MAP_X * (y - 1)].cover != SYMBOL_FLAG:
                    MAP[(x - 1) + MAP_X * (y - 1)].auto_left_click()
                # W
                if x - 1 >= 0 and not MAP[(x - 1) + MAP_X * y].isChecked() and MAP[(x - 1) + MAP_X * y].cover != SYMBOL_FLAG:
                    MAP[(x - 1) + MAP_X * y].auto_left_click()
                # SW
                if x - 1 >= 0 and y + 1 <MAP_Y and not MAP[(x - 1) + MAP_X * (y + 1)].isChecked() and MAP[(x - 1) + MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    MAP[(x - 1) + MAP_X * (y + 1)].auto_left_click()
                # N
                if y - 1 >= 0 and not MAP[x + MAP_X * (y - 1)].isChecked() and MAP[x + MAP_X * (y - 1)].cover != SYMBOL_FLAG:
                    MAP[x + MAP_X * (y - 1)].auto_left_click()
                # S
                if y + 1 < MAP_Y and not MAP[x + MAP_X * (y + 1)].isChecked() and MAP[x + MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    MAP[x + MAP_X * (y + 1)].auto_left_click()
                # NE
                if x + 1 < MAP_X and y - 1 >= 0 and not MAP[(x + 1) + MAP_X * (y - 1)].isChecked() and MAP[(x + 1) + MAP_X * (y -1)].cover != SYMBOL_FLAG:
                    MAP[(x + 1) + MAP_X * (y - 1)].auto_left_click()
                # E
                if x + 1 < MAP_X and not MAP[(x + 1) + MAP_X * y].isChecked() and MAP[(x + 1) + MAP_X * y].cover != SYMBOL_FLAG:
                    MAP[(x + 1) + MAP_X * y].auto_left_click()
                # SE
                if x + 1 < MAP_X and y + 1 < MAP_Y and not MAP[(x + 1) + MAP_X * (y + 1)].isChecked() and MAP[(x + 1) + MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    MAP[(x + 1) + MAP_X * (y + 1)].auto_left_click()
        if not GAME_TERMINATED:
            self.parent().parent().show_message(str(MAP_Z - MARKED_COUNT) + " mines remained")
    
    def auto_left_click(self):
        print("Auto Left Click (" + str(self.x) + ", " + str(self.y) + ")")
        self.setChecked(True)
        self.left_click()
    
    def right_click(self):
        global GAME_TERMINATED
        global MARKED_COUNT
        global TRICK_MODE
        global REVEALED_COUNT
        
        if not GAME_TERMINATED:
            if not self.isChecked():
                if self.cover == SYMBOL_BLANK:
                    self.cover = SYMBOL_FLAG
                    MARKED_COUNT += 1
                elif self.cover == SYMBOL_FLAG:
                    self.cover = SYMBOL_UNKNOWN
                    MARKED_COUNT -= 1
                elif self.cover == SYMBOL_UNKNOWN:
                    self.cover = SYMBOL_BLANK
                self.parent().button_set_text(self, self.cover)
            else:
                if not TRICK_MODE:
                    self.setChecked(True)
                else:
                    REVEALED_COUNT -= 1
            self.parent().parent().show_message(str(MAP_Z - MARKED_COUNT) + " mines remianed")
    
    def auto_mark(self):
        print("Auto Mark (" + str(self.x) + ", " + str(self.y) + ")")
        while not GAME_TERMINATED and self.cover != SYMBOL_FLAG:
            self.right_click()
    
    def reveal(self, flag):
        if self.haveMine:
            if flag:
                self.setToolTip("!" + str(self.x + MAP_X * self.y) + "(" + str(self.x) + ", " + str(self.y) + ")")
            else:
                self.setToolTip(str(self.x + MAP_X * self.y) + "(" + str(self.x) + ", " + str(self.y) + ")")


class MineField(QtWidgets.QWidget):
    def __init__(self):
        super(MineField, self).__init__()
        self.init_mine_field()
    
    def init_mine_field(self):
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(0)
        
        for y in range(MAP_Y):
            for x in range(MAP_X):
                tmpLand = Land(x, y)
                tmpLand.clicked.connect(self.left_click)
                tmpLand.customContextMenuRequested.connect(self.right_click)
                MAP.append(tmpLand)
                grid.addWidget(tmpLand, y, x)
        
        self.generate_map()
        
        self.setLayout(grid)
        
    def generate_map(self):
        global REVEALED_COUNT
        global MARKED_COUNT
        global GAME_TERMINATED
        REVEALED_COUNT, MARKED_COUNT, GAME_TERMINATED = 0, 0, False
        
        for x in range(MAP_X):
            for y in range(MAP_Y):
                MAP[x + MAP_X * y].haveMine = False
                MAP[x + MAP_X * y].setChecked(False)
                MAP[x + MAP_X * y].cover = SYMBOL_BLANK
                MAP[x + MAP_X * y].content = SYMBOL_BLANK
                MAP[x + MAP_X * y].setText(SYMBOL_BLANK)
        
        for i in range(MAP_Z):
            x = randint(0, MAP_X-1)
            y = randint(0, MAP_Y-1)
            while MAP[x + MAP_X * y].haveMine:
                x = randint(0, MAP_X-1)
                y = randint(0, MAP_Y-1)
            MAP[x + MAP_X * y].haveMine = True
        
        for x in range(MAP_X):
            for y in range(MAP_Y):
                if MAP[x + MAP_X * y].haveMine:
                    MAP[x + MAP_X * y].content = SYMBOL_MINE
                else:
                    mine_num = 0
                    # NW
                    if x - 1 >= 0 and y - 1 >= 0 and MAP[(x - 1) + MAP_X * (y - 1)].haveMine:
                        mine_num += 1
                    # W
                    if x - 1 >= 0 and MAP[(x - 1) + MAP_X * y].haveMine:
                        mine_num += 1
                    # SW
                    if x - 1 >= 0 and y + 1 <MAP_Y and MAP[(x - 1) + MAP_X * (y + 1)].haveMine:
                        mine_num += 1
                    # N
                    if y - 1 >= 0 and MAP[x + MAP_X * (y - 1)].haveMine:
                        mine_num += 1
                    # S
                    if y + 1 < MAP_Y and MAP[x + MAP_X * (y + 1)].haveMine:
                        mine_num += 1
                    # NE
                    if x + 1 < MAP_X and y - 1 >= 0 and MAP[(x + 1) + MAP_X * (y -1)].haveMine:
                        mine_num += 1
                    # E
                    if x + 1 < MAP_X and MAP[(x + 1) + MAP_X * y].haveMine:
                        mine_num += 1
                    # SE
                    if x + 1 < MAP_X and y + 1 < MAP_Y and MAP[(x + 1) + MAP_X * (y + 1)].haveMine:
                        mine_num += 1
                    if mine_num == 0:
                        MAP[x + MAP_X * y].mine_num = mine_num
                        MAP[x + MAP_X * y].content = " "
                    elif mine_num > 0:
                        MAP[x + MAP_X * y].mine_num = mine_num
                        MAP[x + MAP_X * y].content = str(mine_num)
    
    def check_end_game(self, x, y):
        global GAME_TERMINATED
        global REVEALED_COUNT
        if MAP[x + MAP_X * y].haveMine:
            GAME_TERMINATED = True
            self.parent().show_message("YOU FAILED")
            for i in MAP:
                    if i.haveMine:
                        i.cover = SYMBOL_MINE
                        self.button_set_text(i, SYMBOL_MINE)
        elif REVEALED_COUNT == MAP_X * MAP_Y - MAP_Z:
            GAME_TERMINATED = True
            self.parent().show_message("YOU WIN")
            for x in range(MAP_X):
                for y in range(MAP_Y):
                    if MAP[x + MAP_X * y].haveMine:
                        MAP[x + MAP_X * y].cover = SYMBOL_FLAG
                        self.button_set_text(MAP[x + MAP_X * y], SYMBOL_FLAG)

    @staticmethod
    def button_set_text(button, text):
        button.setText(text)
    
    def left_click(self):
        print("Left Click")
        self.sender().left_click()
    
    def right_click(self):
        print("Right Click")
        self.sender().right_click()


class UI(QtWidgets.QMainWindow):
    mine_field = None

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.status = ""
        self.init_ui()
     
    def init_ui(self):
        self.mine_field = MineField()
        
        self.setCentralWidget(self.mine_field)
        self.adjustSize()
        # self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
        self.move(300, 150)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("Mine.ico"))
        self.setWindowIcon(icon)
        self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
        self.statusBar().showMessage("New Game Ready")
        
        self.show()
    
    def show_message(self, ss):
        self.statusBar().showMessage(self.status + ss)
    
    def set_status(self, ss):
        self.status = ss
        self.statusBar().showMessage(self.status)
    
    def keyPressEvent(self, event):
        if event.key() < 256:
            print(chr(event.key()))
        else:
            print(event.key())
        
        global MAP_X
        global MAP_Y
        global MAP_Z
         
        global REVEALED_COUNT
        global MARKED_COUNT
        
        global TRICK_MODE
        global REVEALED
        global GAME_TERMINATED
        
        global AUTO_RANDOM_CLICK
        global AUTO_SOLVING
        
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif event.key() == QtCore.Qt.Key.Key_R:
            self.mine_field.generate_map()
            self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_Q:
            MAP_X, MAP_Y, MAP_Z = 9, 9, 10
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_W:
            MAP_X, MAP_Y, MAP_Z = 16, 16, 40
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_E:
            MAP_X, MAP_Y, MAP_Z = 30, 16, 99
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_Y:
            MAP_X += 5
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_U:
            MAP_X += 1
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_I:
            if MAP_X - 1 >= 10 and (MAP_X - 1) * MAP_Y > MAP_Z:
                MAP_X -= 1
                del MAP[:]
                del self.mine_field
                self.init_ui()
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_O:
            if MAP_X - 5 >= 10 and (MAP_X - 5) * MAP_Y > MAP_Z:
                MAP_X -= 5
                del MAP[:]
                del self.mine_field
                self.init_ui()
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_H:
            MAP_Y += 5
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_J:
            MAP_Y += 1
            del MAP[:]
            del self.mine_field
            self.init_ui()
            self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_K:
            if MAP_X - 1 >= 10 and MAP_X * (MAP_Y - 1) > MAP_Z:
                MAP_Y -= 1
                del MAP[:]
                del self.mine_field
                self.init_ui()
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_L:
            if MAP_Y - 5 >= 10 and MAP_X * (MAP_Y - 5) > MAP_Z:
                MAP_Y -= 5
                del MAP[:]
                del self.mine_field
                self.init_ui()
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_N:
            if MAP_Z + 5 < MAP_X * MAP_Y:
                MAP_Z += 5
                self.mine_field.generate_map()
                self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_M:
            if MAP_Z + 1 < MAP_X * MAP_Y:
                MAP_Z += 1
                self.mine_field.generate_map()
                self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_Comma:
            if MAP_Z - 1 > 0:
                MAP_Z -= 1
                self.mine_field.generate_map()
                self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_Period:
            if MAP_Z - 5 > 0:
                MAP_Z -= 5
                self.mine_field.generate_map()
                self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
                self.show_message("New Game Ready")
        elif event.key() == QtCore.Qt.Key.Key_T:
            TRICK_MODE = not TRICK_MODE
            if TRICK_MODE:
                self.set_status("(Trick Mode On)")
            else:
                self.set_status("(Trick Mode Off)")
        elif event.key() == QtCore.Qt.Key.Key_S and TRICK_MODE:
            REVEALED = not REVEALED
            for i in range(len(MAP)):
                MAP[i].reveal(REVEALED)
        elif event.key() == QtCore.Qt.Key.Key_R and TRICK_MODE:
            REVEALED_COUNT = 0
            MARKED_COUNT = 0
            for i in range(len(MAP)):
                MAP[i].setChecked(False)
                MAP[i].cover = SYMBOL_BLANK
                self.mine_field.button_set_text(MAP[i], MAP[i].cover)
        elif event.key() == QtCore.Qt.Key.Key_A:
            startTime = datetime.datetime.now()
            AUTO_SOLVING = True
            while AUTO_SOLVING and not GAME_TERMINATED:
                AUTO_SOLVING = AI().solve()
                self.update()
            endTime = datetime.datetime.now()
            print("Usage Time: " + str((endTime - startTime).seconds) + "." + str((endTime - startTime).microseconds))
        elif event.key() == QtCore.Qt.Key.Key_F:
            while AUTO_SOLVING:
                self.mine_field.generate_map()
                self.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : )")
                self.show_message("New Game Ready")
                while AUTO_SOLVING and not GAME_TERMINATED:
                    AUTO_SOLVING = AI().solve()
                    self.update()
        elif event.key() == QtCore.Qt.Key.Key_Z:
            AI().solve()
        elif event.key() == QtCore.Qt.Key.Key_X:
            AI().random_click(1)
        elif event.key() == QtCore.Qt.Key.Key_C:
            AUTO_RANDOM_CLICK = not AUTO_RANDOM_CLICK   


def main():
    app = QtWidgets.QApplication(sys.argv)
    global ui
    ui = UI()
    sys.exit(app.exec())


class AI(object):
    def __init__(self):
        self.conditionList = []  # [land_id, mine_num, ...]
        self.nextID = -1
        self.clickOrMark = 0
        self.debugFlag = False
    
    def solve(self):
        global AUTO_RANDOM_CLICK
        print("===AI===")
        self.collect_condition()
        if self.debugFlag:
            for i in self.conditionList:
                print(i)
        print("Try to analyse ...")
        if self.analyse_condition():
            ui.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : D")
            if self.debugFlag:
                for i in self.conditionList:
                    print(i)
            return True
        else:
            print("No conclusion found.")
            ui.setWindowTitle(str(MAP_X) + " X " + str(MAP_Y) + " with " + str(MAP_Z) + " Mines" + " : (")
            if AUTO_RANDOM_CLICK:
                self.random_click(1)
                return True
            else:
                return False
    
    def collect_condition(self):
        for i in MAP:
            if i.isChecked() and i.mine_num != 0:
                x, y = i.x, i.y
                tmp_list = [x + MAP_X * y, i.mine_num]
                # NW
                if x - 1 >= 0 and y - 1 >= 0 and not MAP[(x - 1) + MAP_X * (y - 1)].isChecked() and MAP[(x - 1) + MAP_X * (y - 1)].cover != SYMBOL_FLAG:
                    tmp_list.append((x - 1) + MAP_X * (y - 1))
                # N
                if y - 1 >= 0 and not MAP[x + MAP_X * (y - 1)].isChecked() and MAP[x + MAP_X * (y - 1)].cover != SYMBOL_FLAG:
                    tmp_list.append(x + MAP_X * (y - 1))
                # NE
                if x + 1 < MAP_X and y - 1 >= 0 and not MAP[(x + 1) + MAP_X * (y - 1)].isChecked() and MAP[(x + 1) + MAP_X * (y - 1)].cover != SYMBOL_FLAG:
                    tmp_list.append((x + 1) + MAP_X * (y - 1))
                # W
                if x - 1 >= 0 and not MAP[(x - 1) + MAP_X * y].isChecked() and MAP[(x - 1) + MAP_X * y].cover != SYMBOL_FLAG:
                    tmp_list.append((x - 1) + MAP_X * y)
                # E
                if x + 1 < MAP_X and not MAP[(x + 1) + MAP_X * y].isChecked() and MAP[(x + 1) + MAP_X * y].cover != SYMBOL_FLAG:
                    tmp_list.append((x + 1) + MAP_X * y)
                # SW
                if x - 1 >= 0 and y + 1 <MAP_Y and not MAP[(x - 1) + MAP_X * (y + 1)].isChecked() and MAP[(x - 1) + MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    tmp_list.append((x - 1) + MAP_X * (y + 1))
                # S
                if y + 1 < MAP_Y and not MAP[x + MAP_X * (y + 1)].isChecked() and MAP[x+ MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    tmp_list.append(x + MAP_X * (y + 1))
                # SE
                if x + 1 < MAP_X and y + 1 < MAP_Y and not MAP[(x + 1) + MAP_X * (y + 1)].isChecked() and MAP[(x + 1) + MAP_X * (y + 1)].cover != SYMBOL_FLAG:
                    tmp_list.append((x + 1) + MAP_X * (y + 1))
                flag_num = 0
                # NW
                if x - 1 >= 0 and y - 1 >= 0 and not MAP[(x - 1) + MAP_X * (y - 1)].isChecked() and MAP[(x - 1) + MAP_X * (y - 1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                # N
                if y - 1 >= 0 and not MAP[x + MAP_X * (y - 1)].isChecked() and MAP[x + MAP_X * (y - 1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                # NE
                if x + 1 < MAP_X and y - 1 >= 0 and not MAP[(x + 1) + MAP_X * (y - 1)].isChecked() and MAP[(x + 1) + MAP_X * (y -1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                # W
                if x - 1 >= 0 and not MAP[(x - 1) + MAP_X * y].isChecked() and MAP[(x - 1) + MAP_X * y].cover == SYMBOL_FLAG:
                    flag_num += 1
                # E
                if x + 1 < MAP_X and not MAP[(x + 1) + MAP_X * y].isChecked() and MAP[(x + 1) + MAP_X * y].cover == SYMBOL_FLAG:
                    flag_num += 1
                # SW
                if x - 1 >= 0 and y + 1 <MAP_Y and not MAP[(x - 1) + MAP_X * (y + 1)].isChecked() and MAP[(x - 1) + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                # S
                if y + 1 < MAP_Y and not MAP[x + MAP_X * (y + 1)].isChecked() and MAP[x + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                # SE
                if x + 1 < MAP_X and y + 1 < MAP_Y and not MAP[(x + 1) + MAP_X * (y + 1)].isChecked() and MAP[(x + 1) + MAP_X * (y + 1)].cover == SYMBOL_FLAG:
                    flag_num += 1
                tmp_list[1] = i.mine_num - flag_num
                if tmp_list[1] != 0 or len(tmp_list) - 2 != 0:
                    self.conditionList.append(tmp_list)

    @staticmethod
    def random_click(num):
        print("Random Click")
        i = 0
        while i < num:
            k = randint(0, MAP_X * MAP_Y -1)
            if not MAP[k].isChecked() and not MAP[k].cover == SYMBOL_FLAG:
                MAP[k].auto_left_click()
                i += 1
    
    def analyse_condition(self):
        flag = False
        while True:
            for i in range(len(self.conditionList)):
                if self.conditionList[i][1] == 0:
                    for k in self.conditionList[i][2:]:
                        if MAP[k].cover != SYMBOL_FLAG:
                            if AUTO_SOLVING:
                                MAP[k].auto_left_click()
                            else:
                                ui.show_message(str(k) + " is empty")
                            flag = True
                            break
                elif self.conditionList[i][1] == len(self.conditionList[i]) - 2:
                    for k in range(2, len(self.conditionList[i])):
                        if AUTO_SOLVING:
                            MAP[self.conditionList[i][k]].auto_mark()
                        else:
                            ui.show_message(str(self.conditionList[i][k]) + " have mine")
                        flag = True
                        break
                if flag: break
            if flag: break
            for i in range(len(self.conditionList) - 1):
                for j in range(i + 1, len(self.conditionList)):
                    if self.conditionList[i][1] == self.conditionList[j][1] and len(self.conditionList[i]) != len(self.conditionList[j]) and self.is_include(self.conditionList[i], self.conditionList[j]):
                        tmp_list = self.sub(self.conditionList[i], self.conditionList[j])
                        # for k in tmp_list:
                        #     MAP[k].auto_left_click()
                        if AUTO_SOLVING:
                            MAP[tmp_list[0]].auto_left_click()
                        else:
                            ui.show_message(str(tmp_list[0]) + " is empty.")
                        flag = True
                    elif self.conditionList[i][1] != self.conditionList[j][1] and abs(self.conditionList[i][1] - self.conditionList[j][1]) == abs(len(self.conditionList[i]) - len(self.conditionList[j])) and self.is_include(self.conditionList[i], self.conditionList[j]):
                        # if self.conditionList[i][1] > self.conditionList[j][1]:
                        #     tmp_list = self.conditionList[j][2:]
                        # else:
                        #     tmp_list = self.conditionList[i][2:]
                        tmp_list = self.sub(self.conditionList[i], self.conditionList[j])
                        # for k in tmp_list:
                        #     MAP[k].auto_mark()
                        if AUTO_SOLVING:
                            MAP[tmp_list[0]].auto_mark()
                        else:
                            ui.show_message(str(tmp_list[0]) + " have mine.")
                        flag = True
                    if flag:
                        break
                if flag:
                    break
            break
        return flag

    @staticmethod
    def is_include(a, b):
        if len(a) < len(b):
            tmp = a
            a = b
            b = tmp
        i, j, k = 2, 2, 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i += 1
                j += 1
                k += 1
            elif a[i] < b[j]:
                i += 1
            else:   # a[i] > b[j]
                j += 1
        return k == len(b) - 2

    @staticmethod
    def sub(a, b):
        i, j = 0, 0
        c, d = a[2:], b[2:]
        while i < len(c) and j < len(d):
            if c[i] == d[j]:
                c.remove(c[i])
                d.remove(d[j])
            elif c[i] < d[j]:
                i += 1
            else:   # c[i] > d[j]
                j += 1
        if len(c) != 0:
            tmp_list = c
        else:
            tmp_list = d
        return tmp_list


if __name__ == '__main__':
    main()
