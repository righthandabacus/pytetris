# pytetris - Implementing Tetris on Python

A pedegogical project to explain Python language, by implementing
[Tetris](https://en.wikipedia.org/wiki/Tetris).  Gameboy's implementation has
18 rows and 10 columns (see
[screenshots](http://www.oldiesrising.com/images_testsv3/Nintendo%20Game%20Boy/Tetris/))

There are several Tetris implementation out there. The first one I know of is
at <http://code.activestate.com/recipes/580680-tetris/>, in text console, and
another one is at <http://zetcode.com/wxpython/thetetrisgame/>, in GUI using
wxPython. This implementation is using wxPython and tkinter for GUI and some
design is borrowed from the latter.

The code are explained below:

## Tetris, tetrominoes, and abstraction

Python 2 will be obsoleted soon, so the code is in Python 3. Python 3 is a
duck-typing language but sometimes you will find that strong typing has its
benefits of clarity. One of my favorite features in recent update of Python 3
is type annotation, which allows type to be specified but not enforced. To use
it, this is the boilerplate:

```python
from __future__ import annotations
from typing import Tuple, List, Callable
```

The `annotations` from `__future__` is to allow postponed evaluation of
annotations, i.e., use the type in annotations before it is defined in the
later section of the code. The other generic types from `typing` module
may be imported if we find it useful.

Tetris is such named is because, in my opinion, is a game based on
[tetrominoes](https://en.wikipedia.org/wiki/Tetromino). Tetrominoes
are shapes composed of four squares connected on the edges. Consider
all rotations but not flipping, there are seven possible tetrominoes,
each is named after a capital alphabet that looks like its shape.

In this game, we want to separate the game logic from the graphical display.
This will help us easily replace the game with a different user interface while
we do not change the rule of the game. Such design is called "abstraction" in
software engineering. So there are a few `class` defined to hold a logical
concept with no reference to the user interface. Tetromino shapes is one of
them. But first, we want to define the names for tetromino shapes:

```python
from enum import IntEnum, unique
@unique
class Tetrominoes(IntEnum):
    """Name of one-sided tetrominoes, https://en.wikipedia.org/wiki/Tetromino"""
    NoShape = 0
    IShape = 1
    JShape = 2
    LShape = 3
    OShape = 4
    SShape = 5
    TShape = 6
    ZShape = 7
```

The above is a class but use as a *enum* structure. Which we can afterwards use
`Tetrominoes.IShape` to mean integer `1`. This is solely to make our code
easier to read such that we do not need to look up what a number like 1 means
in tetrominoes. The reason we need to associate names to number for all the
shapes is because we define how each shape looks like in an array:

```python
class Shape:
    """7 tetrominoes shapes + dummy. We make x axis the bottom edge each shape, hence min y for
    shape coordinates should be 0
    """
    shapeCoords = (
        (( 0, 0), (0, 0), (0, 0), (0, 0)),  # 0 = NoShape
        (( 0, 3), (0, 2), (0, 1), (0, 0)),  # 1 = I
        ((-1, 0), (0, 0), (0, 1), (0, 2)),  # 2 = J
        (( 1, 0), (0, 0), (0, 1), (0, 2)),  # 3 = L
        (( 0, 1), (1, 1), (0, 0), (1, 0)),  # 4 = O
        ((-1, 0), (0, 0), (0, 1), (1, 1)),  # 5 = S
        ((-1, 0), (0, 0), (1, 0), (0, 1)),  # 6 = T
        ((-1, 1), (0, 1), (0, 0), (1, 0)),  # 7 = Z
    )

    def __init__(self, shape: int = Tetrominoes.NoShape):
        """Construct a new shape. The variable self.coords is pre-created and later on modified
        in-place. It should not be a reference to Shape.shapeCoords as it will be modified when
        the shape is moved.
        """
        self.coords = [list(x) for x in Shape.shapeCoords[shape]]
        self._shape = shape

    @property
    def shape(self) -> int:
        """return shape of this piece"""
        return self._shape

    @shape.setter
    def shape(self, shape: int) -> None:
        """Reset this piece to another shape, with self.coords updated
        """
        self.coords[:] = [list(x) for x in self.shapeCoords[shape]]
        self._shape = shape

    @staticmethod
    def randomize() -> None:
        """Give a random piece"""
        shape = Tetrominoes(random.randint(1, len(Shape.shapeCoords)-1))
        return Shape(shape)
```

Python has two types of arrays: `list` and `tuple`. The former is mutable but
the latter is not. Here we create `shapeCoords` as a tuple, which each element
corresponds to a tetromino. A tetromino is represented as four coordinates. An
object of class `Shape` holds an integer to tell which shape it is. When we
generate a random shape, we pick the shape by generating a random integer from
1 to 7.

Some Python techniques are used in the class above:

- constructor has default for shape parameter, so creating an object without
  specifying any shape will be "no shape"
- we defined `shape` property, which the shape can be changed if this is
  assigned to a different value
- `randomize()` function is defined as a `staticmethod`, which do not depend on
  any instance of the class

Besides tetromino, game also have a board. A board can be any reasonable size
but we choose it to be 10x18. Below is how this is implemented:

```python
class TetrisBoard:
    def __init__(self, width: int = 10, height: int = 18):
        self.nTilesH = width  # i.e., row size in num of square tiles
        self.nTilesV = height # i.e., col size in num of square tiles
        # row major array to hold tiles, from the tile we can look up the shape
        self.tiles = []
        self.clear()

    def __setitem__(self, key: Tuple[int, int], value: Shape) -> None:
        col, row = key # board[x,y] -> key will be a tuple
        self.tiles[row*self.nTilesH + col] = value

    def __getitem__(self, key: Tuple[int, int]) -> Shape:
        col, row = key # board[x,y] -> key will be a tuple
        return self.tiles[row*self.nTilesH + col]

    def clear(self) -> None:
        self.tiles[:] = [Tetrominoes.NoShape] * (self.nTilesV * self.nTilesH)

    def check_pos(self, piece: Shape, x: int, y: int) -> bool:
        coords = [[px+x, py+y] for px, py in piece.coords if py+y < self.nTilesV]
        if not coords:
            return False
        if not all(0 <= cx < self.nTilesH and cy >= 0 for cx, cy in coords):
            return False
        if any(self[cx, cy] != Tetrominoes.NoShape for cx, cy in coords):
            return False
        return True # all other cases is OK

    def fix_pos(self, piece: Shape, x: int, y: int) -> None:
        coords = [[px+x, py+y] for px, py in piece.coords]
        for cx, cy in coords:
            self[cx, cy] = piece.shape

    def removefull(self) -> int:
        # Check each rows for what is not full
        notfull = [y for y in range(self.nTilesV)
                   if any(self[x, y] == Tetrominoes.NoShape for x in range(self.nTilesH))]
        if self.nTilesV == len(notfull):
            return 0
        # Remove anything that is full
        move = [(i, j) for i, j in enumerate(notfull) if i != j]
        for j, k in move:
            for i in range(self.nTilesH):
                self[i, j] = self[i, k]
        # Fill in any new lines at top with NoShape
        toprow = max(i for i, _ in move) + 1
        for j in range(toprow, self.nTilesV):
            for i in range(self.nTilesH):
                self[i, j] = Tetrominoes.NoShape
        return self.nTilesV - len(notfull)
```

Here we keep track of all the 10x18 tiles in a list. To provide a convenient
expression to access to a tile, we overrode `__setitem__()` and `__getitem__()`
to allow `self[column, row]` which both column and row are both zero-indexed.
When we have a tetromino shape, the board provide a function `check_pos()` to
verify if such particular shape can be placed at a specified position. If the
shape does not have any conflict with existing tetrominoes, we can fix it on
the board through function `fix_pos()`. And finally, the function
`removefull()` clean up the board for any completed rows. These are all the
basic operations to the board. We treat the board like this as the *state* of
the game, and the game proceeds by continuously updating the state. In other
words, the game is basically keeping no history of the moves.

The board does not provide any logic. We can extend the board to implement
these. Deriving a daughter class from `TetrisBoard` is not the best way
(composition is better than inheritance in this case) but for simplicity
and pedegogical reason, we settle for this. Below we implemented:

- other state variables to hold the current dropping Tetromino and the next one
- the current position of the dropping Tetromino piece
- game state: whether it is paused, started, just finished with a piece
- achievement: how many rows completed

```python
class TetrisGame(TetrisBoard):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This and next piece of tetrominoes, and the position of the current piece
        self.this_piece = Shape()
        self.next_piece = Shape()
        self.cur_x = 0
        self.cur_y = 0
        # State variable of the game
        self.neednewpiece = False   # Old piece dropped, new piece to be created
        self.paused = False         # Game paused, timer should be suspended
        self.started = False        # Game started, timer should be created
        self.rows_completed = 0     # Game state: number of rows completed

    def start(self) -> bool:
        if self.paused:
            return False
        self.started = True
        self.neednewpiece = False
        self.rows_completed = 0
        self.next_piece = Shape.randomize()
        self.make_new_piece()
        self.clear()
        return True

    def make_new_piece(self) -> bool:
        # generate new piece and position at top middle, then check if we can still proceed
        self.neednewpiece = False
        if self.try_pos(self.next_piece, self.nTilesH // 2, self.nTilesV - 1):
            self.next_piece = Shape.randomize() # next_piece became this_piece, replace it with a new one
            return True
        # cannot even place the shape at top middle of the board, finish the game
        self.this_piece.shape = Tetrominoes.NoShape
        self.started = False
        return False

    def pause(self) -> bool:
        if not self.started:
            return True
        self.paused = not self.paused
        return self.paused

    def try_pos(self, piece: Shape, x: int, y: int) -> bool:
        if self.check_pos(piece, x, y):
            # this position is good, remember it
            self.this_piece = piece
            self.cur_x = x
            self.cur_y = y
            return True
        return False # the piece cannot be placed at this position

    def piece_dropped(self) -> None:
        # fix this_piece into the board (ignore any tile above top boundary)
        xs = [self.cur_x + x for x in self.this_piece.x]
        ys = [self.cur_y + y for y in self.this_piece.y if self.cur_y + y < self.nTilesV]
        for x, y in zip(xs, ys):
            self[x, y] = self.this_piece.shape
        self.neednewpiece = True
        self.this_piece.shape = Tetrominoes.NoShape
        # find all rows that are full and remove them
        rows_removed = self.removefull()
        logging.debug("%d rows removed", rows_removed)
        if rows_removed:
            self.rows_completed += rows_removed

    def one_row_down(self) -> bool:
        if self.try_pos(self.this_piece, self.cur_x, self.cur_y - 1):
            return True
        self.piece_dropped()
        return False
```

Virtually all game movement are implemented. The function `make_new_piece()` will
create a new tetromino and place at the top middle of the game board. The
position of the piece is remembered by the variable `self.cur_x` and
`self.cur_y`. Then a movement of the piece can be tested with `try_pos()` for
validity, and in case of valid, it will be remembered as new position. The same
function can be used to handle the case of piece rotation as well. An example of
using `try_pos()` is in `one_row_down()`, which will be called by a timer to
handle a falling piece, and in that function, we check with position of
`self.cur_y-1`.

## Tetris game user interface

What is left behind is to connect the user interaction with the game logic. We
try wxPython as it seems to be a simple but mature library for GUI. A simple
wxPython application is simply create a frame, like below:

```python
app = wx.App()
win = Tetris(None, title="Tetris") # create a frame
win.Centre() # center the window on screen
win.Show()
app.MainLoop()
```

which `wx.App()` and `app.MainLoop()` are boilerplate items to start the "event
loop" of wxPython. The frame is created as `Tetris()` class instance, which is
defined as below:

```python
class Tetris(wx.Frame):
    def __init__(self, parent, id=-1, title="Tetris"):
        super().__init__(parent, id, title=title, size=(180, 380),
                         style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        # status bar for scoring
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("0")
        # create game board which this frame as parent
        self.board = GameBoard(self)
        self.board.SetFocus()
        self.board.start()
```

This frame, derived from `wx.Frame`, will create a window with a status bar at
bottom and a *panel* at middle. We predefined the window size to be 180x380
pixels. We do not need to assign anything to this frame besides creating a
panel `GameBoard()` under it (by setting parent of the panel as `self`) as all the
sophisticated logic are defined in the panel, as below:

```python
class GameBoard(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        n_hori, n_vert = 10, 18
        self.timer = wx.Timer(self, self.ID_TIMER)
        self.board = TetrisGame(n_hori, n_vert)
        # bind events on panel
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_TIMER, self.OnTimer, id=self.ID_TIMER)
        # start game
        self.start()

    def draw_tile(self, canvas: wx.PaintDC, x: int, y: int, shape: Shape) -> None:
        colors = ["#000000", "#CC6666", "#66CC66", "#6666CC",
                  "#CCCC66", "#CC66CC", "#66CCCC", "#DAAA00"]
        light = ["#000000", "#F89FAB", "#79FC79", "#7979FC",
                 "#FCFC79", "#FC79FC", "#79FCFC", "#FCC600"]
        dark = ["#000000", "#803C3B", "#3B803B", "#3B3B80",
                "#80803B", "#803B80", "#3B8080", "#806200"]
        W, H = self.tile_width, self.tile_height
        # draw left and bottom edge, with light color
        pen = wx.Pen(light[shape])
        pen.SetCap(wx.CAP_PROJECTING)
        canvas.SetPen(pen)
        canvas.DrawLine(x, y+H-1, x, y)
        canvas.DrawLine(x, y, x+W-1, y)
        # draw top and right edge, with dark color
        darkpen = wx.Pen(dark[shape])
        darkpen.SetCap(wx.CAP_PROJECTING)
        canvas.SetPen(darkpen)
        canvas.DrawLine(x+1, y+H-1, x+W-1, y+H-1)
        canvas.DrawLine(x+W-1, y+H-1, x+W-1, y+1)
        # fill square
        canvas.SetPen(wx.TRANSPARENT_PEN)
        canvas.SetBrush(wx.Brush(colors[shape]))
        canvas.DrawRectangle(x+1, y+1, W-2, H-2)

    def OnPaint(self, event: wx.Event):
        canvas = wx.PaintDC(self) # must create a PaintDC object in OnPaint()
        size = self.GetClientSize()
        topmargin = size.GetHeight() - self.board.nTilesV * self.tile_height
        # draw whatever on the tetris board
        for j in range(self.board.nTilesV): # for each square vertically down
            for i in range(self.board.nTilesH): # for each square horizontally right
                # find coordinate on canvas for upper left corner of this tile. wx.DC has (0,0) at top left corner
                x = i * self.tile_width
                y = (self.board.nTilesV - j - 1) * self.tile_height + topmargin
                if self.board[i, j] != Tetrominoes.NoShape:
                    self.draw_tile(canvas, x, y, self.board[i, j])
        # draw the dropping piece: 4 tiles
        if self.board.this_piece.shape != Tetrominoes.NoShape:
            xs = [(self.board.cur_x + x) * self.tile_width for x in self.board.this_piece.x]
            ys = [(self.board.nTilesV - (self.board.cur_y + y) - 1) * self.tile_height for y in self.board.this_piece.y]
            for x, y in zip(xs, ys):
                self.draw_tile(canvas, x, topmargin+y, self.board.this_piece.shape)

    def OnTimer(self, event: wx.Event):
        if event.GetId() != self.ID_TIMER:
            event.Skip() # we don"t process this event
        elif self.board.neednewpiece:
            # first timer after full row is removed, generate new piece instead of moving down
            if self.board.make_new_piece():
                logging.debug("This: %s; next: %s", self.board.this_piece.shape, self.board.next_piece.shape)
            else:
                # cannot even place the shape at top middle of the board, finish the game
                self.timer.Stop()
                self.GetParent().statusbar.SetStatusText("Game over")
                logging.debug("game over")
        else:
            # normal: move the current piece down for one row
            logging.debug("moving piece down, curr_y = %d", self.board.cur_y)
            self.move_down()
        self.Refresh()

    def OnKeyDown(self, event: wx.Event):
        if not self.board.started or self.board.this_piece.shape == Tetrominoes.NoShape:
            logging.debug("not started - ignore input")
            event.Skip()
            return
        keycode = event.GetKeyCode()
        logging.debug("OnKeyDown: keycode=%d", keycode)
        if keycode in [ord("P"), ord("p")]:
            self.pause()
            return
        if self.board.paused:
            return
        if keycode == wx.WXK_LEFT:
            self.try_move(self.board.this_piece, -1)
        elif keycode == wx.WXK_RIGHT:
            self.try_move(self.board.this_piece, +1)
        elif keycode == wx.WXK_DOWN:
            self.try_move(self.board.this_piece.rotate_ccw(), 0)
        elif keycode == wx.WXK_UP:
            self.try_move(self.board.this_piece.rotate_cw(), 0)
        elif keycode == wx.WXK_SPACE:
            self.drop_down()
        elif keycode == ord("D") or keycode == ord("d"):
            self.move_down()
        else:
            event.Skip()
```

These are the event handler of the panel. `Board` is derived from `wx.Panel`
and we need one to hold our *canvas* so that we can draw the game display.
*Events* are triggers in the GUI that causes a function to run. There are three
events in concern:

- Paint: When we request to refresh the panel, which will then draw the game status graphically
- Timer: The timer fires regularly to "move down" the tetromino piece for a row
- Key down: Whenever we press a key on the keyboard, this is the only way to control the game in our design

In the constructor, we register the event with a function, the event handler,
such that whenever a event happens, that handler will be invoked. We describe
each function handler below:

`OnPaint()` is to draw the logical game board on the panel. The wxPython way
to draw is to create a canvas and call its drawing functions such as
`DrawRectangle` and `DrawLine`. Because all tetrominoes are made of four square
tiles, we *factor out* the function `draw_tile()` to *encapsulate* the drawing
details. So in the function `OnPaint()`, you can see that we start with a new
canvas each time and draw each tile already in the game board and also the dropping
tetromino. If you look at the code you will find that we take the coordinate (0,0)
as the lower left corner in the game board representation and moving right and up
on increasing x- and y-coordinates, respectively. But for drawing in canvas, we
the origin (0,0) represents top left corner and y-coordinate increases as we move
downward. Therefore we have the coordinate calculation done in the function.

The second event handler, `OnTimer()`, simply try to move down the dropping
piece, or, in case the piece already dropped to its lowest possible position,
make a new piece at top. We have a new function `move_down()` to handle the
former case. It calls the game board's `one_row_down()` function and in
addition, update the status bar and trigger redraw of the game board.

The last event handler `OnKeyDown()` is the one list out all possible controls.
The current implementation accepts letter "P" for pause and resume, letter "D"
for one row down without waiting for the timer, space to drop the piece all
the way down, arrow keys up and down for rotation, clockwise and
counterclockwise respectively, and arrow keys left and right to move the
dropping tetromino piece left and right. The special keys are named in
wxPython, for example, `wx.WXK_LEFT` is to represent the left arrow key. Letter
keys, however, is simply the ASCII code of the key. In Python we get the ASCII
code by, for example, `ord("P")`. One can notice that the key down event will
pass in the key that triggered the event throught the `event` object. We
retrieve the key code information by `event.GetKeyCode()`. But as we do not
process all possible key events, we surrender our right to process such event
in case we do not know how to handle it. We do this by calling `event.Skip()`,
at the last row of this function, so that some other event handler may pick up
this event again.

The event handler `OnKeyDown()` calls a few other functions. Most noticable is
the `try_move()` function, which may be called with an altered position, or
rotated piece. The piece rotation is defined in the piece itself, as follows:

```python
class Shape:
    def _transform(self, transform: Callable) -> Shape:
        result = Shape(self.shape) # same piece
        result.coords = [transform(x, y) for x, y in self.coords]
        return result

    def rotate_cw(self) -> Shape:
        if self.shape == Tetrominoes.OShape:
            return self # no rotate for "O"
        cw = lambda x, y: [y, -x]
        return self._transform(cw)

    def rotate_ccw(self) -> Shape:
        if self.shape == Tetrominoes.OShape:
            return self # no rotate for "O"
        ccw = lambda x, y: [-y, x]
        return self._transform(ccw)
```

The rotation is applying a coordinate transformation to the four square tiles
of a tetromino. The rotation is independent of the postion coordinate but
manipulates the shape's coordinate in `self.coord`. In above, we do the
transformation by a generic `_transform()` function, which the actual
transformation rule in case of clockwise or counterclockwise rotation are
provided as a *lambda function*.

Below are the other functions invoked from the event handlers. They should be
self-explanatory.

```python
class GameBoard(wx.Panel):
    speed = 300
    ID_TIMER = 1

    @property
    def tile_width(self) -> int:
        return self.GetClientSize().GetWidth() // self.board.nTilesH

    @property
    def tile_height(self) -> int:
        return self.GetClientSize().GetHeight() // self.board.nTilesV

    def start(self) -> None:
        if self.board.start():
            self.timer.Start(self.speed) # timer fire regularly in pulses

    def pause(self) -> None:
        if self.board.pause():
            self.timer.Stop()
            self.GetParent().statusbar.SetStatusText("paused")
        else:
            self.timer.Start(self.speed)
            self.GetParent().statusbar.SetStatusText(str(self.board.rows_completed))
        self.Refresh()

    def move_down(self) -> bool:
        moved = self.board.one_row_down()
        if not moved:
            self.GetParent().statusbar.SetStatusText(str(self.board.rows_completed))
        self.Refresh()
        return moved

    def drop_down(self) -> None:
        while self.move_down():
            pass

    def try_move(self, piece, x_delta) -> None:
        if self.board.try_pos(piece, self.board.cur_x + x_delta, self.board.cur_y):
            self.Refresh()
```

## Enhancement to the user interface: Extra hint to the user

Usually a Tetris game will show to the player the current score and other
information. For example, the next tetromino piece. Indeed, the game engine as
we coded above already prepared for this by maintaining a few state variables.
To display them, we have a few options.  First we explore the *splitter window* in
wxPython, which shows the game and the dashboard side by side. The way to use a
splitter window is as follows:

```python
class Tetris(wx.Frame):
    def __init__(self, parent, id=-1, title="Tetris"):
        super().__init__(parent, id, title=title, size=(180*2, 380),
                         style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        self.splitter = wx.SplitterWindow(self)

        self.dashboard = Dashboard(self.splitter, style=wx.SUNKEN_BORDER)
        self.gameboard = GameBoard(self.splitter, style=wx.SUNKEN_BORDER)
        self.dashboard.gameboard = self.gameboard
        self.gameboard.dashboard = self.dashboard

        self.splitter.SplitVertically(self.gameboard, self.dashboard, 180)
        self.splitter.SetMinimumPaneSize(180)

        self.gameboard.SetFocus()
        self.gameboard.start()
```

Splitter window is a widget in wxPython. We create the game panel and dashboard
panel as children of the splitter window, then set up the splitter to be
vertical (i.e., the two panels are side by side horizontally).

We use the same game engine as it is still the same Tetris game with same
logic. The dashboard is created to expose some state variables in the engine.
The constructor of the dashboard panel has all the widgets prepared:

```python
class Dashboard(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetBackgroundColour((255, 255, 255))
        # make widget to display text
        text = wx.StaticText(self, -1, "SCORE", pos=(20, 15))
        text.SetFont(wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        text = wx.StaticText(self, -1, "LEVEL", pos=(20, 85))
        text.SetFont(wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        text = wx.StaticText(self, -1, "ROWS", pos=(20, 155))
        text.SetFont(wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))

        self.scoretxt = wx.StaticText(self, -1, "0", pos=(40, 30), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.scoretxt.SetFont(wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.leveltxt = wx.StaticText(self, -1, "1", pos=(40, 100), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.leveltxt.SetFont(wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.rowstxt = wx.StaticText(self, -1, "0", pos=(40, 170), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.rowstxt.SetFont(wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))

        self.message = wx.StaticText(self, -1, "", pos=(0, 250), size=(170, 50), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.message.SetForegroundColour((255, 0, 0))
        self.message.SetFont(wx.Font(28, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        # bind events on panel
        self.Bind(wx.EVT_PAINT, self.OnPaint)
```

And we hook up the panel's paint event handler to refresh. We first pull the
data such as game score from the game engine, and draw the "next tetromino
piece". So the dashboard is kind of unmanaged that it automatically display all
data.

```python
class Dashboard(wx.Panel):
    def update(self) -> None:
        """Update what this dashboard should show"""
        self.scoretxt.SetLabel(str(self.gameboard.board.score))
        self.leveltxt.SetLabel(str(self.gameboard.board.level))
        self.rowstxt.SetLabel(str(self.gameboard.board.rows_completed))

    def OnPaint(self, event: wx.Event):
        """Paint event handler. Triggered when window's contents need to be repainted, e.g. on
        Refresh() called.  Canvas coordinate is x going positive toward right and y going positive
        downwards
        """
        self.update()
        canvas = wx.PaintDC(self) # must create a PaintDC object in OnPaint()
        size = self.GetClientSize()
        tile_width, tile_height = self.gameboard.tile_width, self.gameboard.tile_height
        shape = self.gameboard.board.next_piece
        center_y = 270
        # draw square
        canvas.DrawRectangle(size.GetWidth()//2 - 2.5*tile_width, center_y - 2.5*tile_height,
                             5*tile_width, 5*tile_height)
        # position the piece at center
        min_x, min_y = min(shape.x), min(shape.y)
        shape_width = (max(shape.x) + 1 - min_x) * tile_width
        shape_height = (max(shape.y) + 1 - min_y) * tile_height
        offset_x = (size.GetWidth() - shape_width) // 2 - min_x * tile_width
        offset_y = center_y + (shape_height // 2) + (min_y-1) * tile_height
        xs = [offset_x+x * tile_width for x in shape.x]
        ys = [offset_y-y * tile_height for y in shape.y]
        for x, y in zip(xs, ys):
            logging.debug("dashboard draw (%s,%s) shape %s", x, y, shape.shape)
            self.gameboard.draw_tile(canvas, x, y, shape.shape)
```

The game panel side is roughly the same as before, except that we do not use a
status bar any more but use a message label at dashboard instead. For example,
when we pause the game, the pause function will update the label:

```python
class GameBoard(wx.Panel):
    def pause(self) -> None:
        """Toggle pause state: update status bar message and set/stop timers"""
        if self.board.pause():
            self.timer.Stop()
            self.dashboard.message.SetLabel("Paused")
            self.dashboard.SetBackgroundColour((225, 225, 225))
        else:
            self.timer.Start(self.speed)
            self.dashboard.message.SetLabel("")
            self.dashboard.SetBackgroundColour((255, 255, 255))
        self.Refresh()
        self.dashboard.Refresh()
```

## Enhancement to the user interface: Combined panel

If the dashboard panel is so simple that all the magic is in the paint event
handler, we can actually combine it with the game panel. We can simply create a
bigger panel, split it into two halves, and use one half to serve as dashboard
while the other half for the game. So we just need one panel for the Tetris
frame:

```python
class Tetris(wx.Frame):
    def __init__(self, parent, id=-1, title="Tetris"):
        super().__init__(parent, id, title=title, size=(180*2, 380),
                         style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        # create game board which this frame as parent
        self.gameboard = GameBoard(self)
        self.gameboard.SetFocus()
        self.gameboard.start()
```

and the game panel is now merge of the original game panel and dashboard panel:

```python
class GameBoard(wx.Panel):
    speed = 300
    ID_TIMER = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetBackgroundColour((255, 255, 255))
        n_hori, n_vert = 10, 18
        self.timer = wx.Timer(self, self.ID_TIMER)
        self.board = TetrisGame(n_hori, n_vert)
        # dashboard components
        textfont = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False)
        wx.StaticText(self, -1, "SCORE", pos=(200, 15)).SetFont(textfont)
        wx.StaticText(self, -1, "LEVEL", pos=(200, 85)).SetFont(textfont)
        wx.StaticText(self, -1, "ROWS", pos=(200, 155)).SetFont(textfont)
        dashfont = wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False)
        self.scoretxt = wx.StaticText(self, -1, "0", pos=(220, 30), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.leveltxt = wx.StaticText(self, -1, "1", pos=(220, 100), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.rowstxt = wx.StaticText(self, -1, "0", pos=(220, 170), size=(100, 30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        for txt in [self.scoretxt, self.leveltxt, self.rowstxt]:
            txt.SetFont(dashfont)
        self.message = wx.StaticText(self, -1, "", pos=(185, 250), size=(170, 50), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.message.SetForegroundColour((255, 0, 0))
        self.message.SetFont(wx.Font(28, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        # bind events on panel
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_TIMER, self.OnTimer, id=self.ID_TIMER)
```

and the paint event handler is now doing both of the original panels:

```python
class GameBoard(wx.Panel):
    def OnPaint(self, event: wx.Event):
        # update text component
        self.scoretxt.SetLabel(str(self.board.score))
        self.leveltxt.SetLabel(str(self.board.level))
        self.rowstxt.SetLabel(str(self.board.rows_completed))
        # prepare canvas
        canvas = wx.PaintDC(self) # must create a PaintDC object in OnPaint()
        size = self.GetClientSize()
        topmargin = size.GetHeight() - self.board.nTilesV * self.tile_height
        # draw gameboard border
        x = self.board.nTilesH * self.tile_width + 1
        canvas.DrawLine(x, 0, x, (self.board.nTilesV+1) * self.tile_height)
        # draw whatever on the tetris board
        for j in range(self.board.nTilesV): # for each square vertically down
            for i in range(self.board.nTilesH): # for each square horizontally right
                # find coordinate on canvas for upper left corner of this tile. wx.DC has (0,0) at top left corner
                x = i * self.tile_width
                y = (self.board.nTilesV - j - 1) * self.tile_height + topmargin
                if self.board[i, j] != Tetrominoes.NoShape:
                    self.draw_tile(canvas, x, y, self.board[i, j])
        # draw the dropping piece: 4 tiles
        if self.board.this_piece.shape != Tetrominoes.NoShape:
            xs = [(self.board.cur_x + x) * self.tile_width for x in self.board.this_piece.x]
            ys = [(self.board.nTilesV - (self.board.cur_y + y) - 1) * self.tile_height for y in self.board.this_piece.y]
            for x, y in zip(xs, ys):
                self.draw_tile(canvas, x, topmargin+y, self.board.this_piece.shape)
        # draw the square to hold the next piece
        center_x, center_y = size.GetWidth()*3//4, 270
        rec_x = center_x - 2.5*self.tile_width
        rec_y = center_y - 2.5*self.tile_height
        canvas.SetPen(wx.Pen("#000000"))
        canvas.SetBrush(wx.Brush("#FFFFFF", style=wx.TRANSPARENT))
        canvas.DrawRectangle(rec_x, rec_y, 5*self.tile_width, 5*self.tile_height)
        logging.debug("dashboard rectangle (%s,%s)x(%s,%s)", rec_x, rec_y, 5*self.tile_width, 5*self.tile_height)
        # position the piece at center
        min_x, min_y = min(self.board.next_piece.x), min(self.board.next_piece.y)
        shape_width = (max(self.board.next_piece.x) + 1 - min_x) * self.tile_width
        shape_height = (max(self.board.next_piece.y) + 1 - min_y) * self.tile_height
        offset_x = center_x - shape_width // 2 - min_x * self.tile_width
        offset_y = center_y + shape_height // 2 + (min_y-1) * self.tile_height
        xs = [offset_x+x * self.tile_width for x in self.board.next_piece.x]
        ys = [offset_y-y * self.tile_height for y in self.board.next_piece.y]
        for x, y in zip(xs, ys):
            logging.debug("dashboard draw (%s,%s) shape %s", x, y, self.board.next_piece.shape)
            self.draw_tile(canvas, x, y, self.board.next_piece.shape)
```

## Demonstration of portability of the game engine

While we used wxPython above, the game engine is indeed agnostic to the GUI
library to be used. For example, we can use the same engine but implement the
game on Tk widgets.

Python's Tk library, tkinter, is very similar to wxPython. The way we launch
the framework is like the following:

```python
import tkinter

def main():
    root = tkinter.Tk()
    game = Tetris(root)
    game.start()
    root.mainloop()
```

And the game similar to the case of using wx: we create a big panel with
dashboard widgets on the right half and the game itself on the left half. We
bind the keyboard event to a handler. The panel update, i.e. drawing the
tetromino pieces and update text labels, are handled on the refresh function.

```python
class Tetris(tkinter.Frame):
    """The tetris game implemented in tkinter. Dummy class with logic reside in the board class
    """
    speed = 300

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.parent.title("Tetris")
        self.parent.resizable(width=tkinter.FALSE, height=tkinter.FALSE)
        self.parent.geometry("360x400")
        self.init_widgets()
        n_hori, n_vert = 10, 18
        self.timer = None
        self.board = TetrisGame(n_hori, n_vert)
        # bind events on panel
        self.parent.bind("<Key>", self.OnKeyDown)
        self.Refresh()

    def init_widgets(self):
        self.pack(fill=tkinter.BOTH, expand=tkinter.TRUE)

        self.gamecanvas = tkinter.Canvas(self, width=180, height=360, bg="#F0F0F0", relief=tkinter.SUNKEN)
        self.gamecanvas.grid(row=0, column=0, rowspan=8, padx=3, pady=3, sticky=tkinter.N+tkinter.E+tkinter.S+tkinter.W)
        textfont = "Inconsolata 16 bold"
        dashfont = "Inconsolata 25"
        tkinter.Label(self, text="SCORE", font=textfont) \
               .grid(row=0, column=1, sticky=tkinter.W, padx=10, pady=(25, 0))
        self.scorelabel = tkinter.Label(self, text="0", compound=tkinter.CENTER, font=dashfont)
        self.scorelabel.grid(row=1, column=1, padx=10)
        tkinter.Label(self, text="LEVEL", font=textfont) \
               .grid(row=2, column=1, sticky=tkinter.W, padx=10, pady=(15, 0))
        self.levellabel = tkinter.Label(self, text="1", compound=tkinter.CENTER, font=dashfont)
        self.levellabel.grid(row=3, column=1, padx=10)
        tkinter.Label(self, text="ROWS", font=textfont) \
               .grid(row=4, column=1, sticky=tkinter.W, padx=10, pady=(15, 0))
        self.rowslabel = tkinter.Label(self, text="2", compound=tkinter.CENTER, font=dashfont)
        self.rowslabel.grid(row=5, column=1, padx=10)
        self.message = tkinter.Label(self, text="GAME OVER", compound=tkinter.CENTER, font="Inconsolata 25", fg="red")
        self.message.grid(row=6, column=1, padx=0, pady=5)
        self.hintcanvas = tkinter.Canvas(self, width=90, height=90)
        self.hintcanvas.grid(row=7, column=1, pady=(0, 25))

    @property
    def tile_width(self) -> int:
        return self.gamecanvas.winfo_width() // self.board.nTilesH

    @property
    def tile_height(self) -> int:
        return self.gamecanvas.winfo_height() // self.board.nTilesV

    def start(self) -> None:
        if self.board.start():
            self.message.config(text="")
            if self.timer:
                self.parent.after_cancel(self.timer) # in case after already set up
            self.timer = self.parent.after(self.speed, self.OnTimer) # timer fire regularly in pulses
            logging.debug("game started: %s", self.board.started)

    def pause(self) -> None:
        if self.board.pause():
            if self.timer:
                self.parent.after_cancel(self.timer)
                self.timer = None
            self.message.config(text="Paused")
            self.config(bg="#E1E1E1")
        else:
            if self.timer:
                self.parent.after_cancel(self.timer) # in case after already set up
            self.timer = self.parent.after(self.speed, self.OnTimer)
            self.message.config(text="")
            self.config(bg="#FFFFFF")
        self.Refresh()

    def move_down(self) -> bool:
        moved = self.board.one_row_down()
        self.Refresh()
        return moved

    def drop_down(self) -> None:
        while self.move_down():
            pass
        logging.debug("drop piece to curr_y = %d", self.board.cur_y)

    def try_move(self, piece, x_delta) -> None:
        if self.board.try_pos(piece, self.board.cur_x + x_delta, self.board.cur_y):
            logging.debug("Moved %s to (%s,%s)", piece.shape, self.board.cur_x, self.board.cur_y)
            self.Refresh()
        else:
            logging.debug("Cannot move %s to (%s,%s)", piece.shape, self.board.cur_x+x_delta, self.board.cur_y)

    def draw_tile(self, canvas, x: int, y: int, shape: Tetrominoes) -> None:
        colors = ["#000000", "#CC6666", "#66CC66", "#6666CC",
                  "#CCCC66", "#CC66CC", "#66CCCC", "#DAAA00"]
        light = ["#000000", "#F89FAB", "#79FC79", "#7979FC",
                 "#FCFC79", "#FC79FC", "#79FCFC", "#FCC600"]
        dark = ["#000000", "#803C3B", "#3B803B", "#3B3B80",
                "#80803B", "#803B80", "#3B8080", "#806200"]
        W, H = self.tile_width, self.tile_height
        # draw left and bottom edge, with light color
        canvas.create_line(x, y+H-1, x, y, fill=light[shape])
        canvas.create_line(x, y, x+W-1, y, fill=light[shape])
        # draw top and right edge, with dark color
        canvas.create_line(x+1, y+H-1, x+W-1, y+H-1, fill=dark[shape])
        canvas.create_line(x+W-1, y+H-1, x+W-1, y+1, fill=dark[shape])
        # fill square
        canvas.create_rectangle(x+1, y+1, x+W-1, y+H-1, fill=colors[shape])

    def Refresh(self):
        # update text component
        self.scorelabel.config(text=str(self.board.score))
        self.levellabel.config(text=str(self.board.level))
        self.rowslabel.config(text=str(self.board.rows_completed))
        # prepare canvas
        height, width = self.gamecanvas.winfo_height(), self.gamecanvas.winfo_width()
        topmargin = (height - self.board.nTilesV * self.tile_height) // 2
        leftmargin = (width - self.board.nTilesH * self.tile_width) // 2
        logging.debug("canvas width=%d, height=%d", width, height)
        logging.debug("topmargin=%d, leftmargin=%d, tile width=%d, height=%d", topmargin,
                leftmargin, self.tile_width, self.tile_height)
        # draw gameboard border
        self.gamecanvas.delete("all") # quick and dirty way to start from a clean canvas
        self.gamecanvas.create_rectangle(leftmargin-1, topmargin-1,
                leftmargin+1+self.board.nTilesH*self.tile_width,
                topmargin+1+self.board.nTilesV*self.tile_height)
        logging.debug("draw rectangle (%d,%d)--(%d,%d)", leftmargin-1, topmargin-1,
                leftmargin+1+self.board.nTilesH*self.tile_width,
                topmargin+1+self.board.nTilesV*self.tile_height)
        # draw whatever on the tetris board
        for j in range(self.board.nTilesV): # for each square vertically down
            for i in range(self.board.nTilesH): # for each square horizontally right
                # find coordinate on canvas for upper left corner of this tile. wx.DC has (0,0) at top left corner
                x = i * self.tile_width + leftmargin
                y = (self.board.nTilesV - j - 1) * self.tile_height + topmargin
                if self.board[i, j] != Tetrominoes.NoShape:
                    self.draw_tile(self.gamecanvas, x, y, self.board[i, j])
                    logging.debug("gameboard draw (%s,%s) shape %s", x, y, self.board[i, j])
        # draw the dropping piece: 4 tiles
        if self.board.this_piece.shape != Tetrominoes.NoShape:
            xs = [(self.board.cur_x + x) * self.tile_width for x in self.board.this_piece.x]
            ys = [(self.board.nTilesV - (self.board.cur_y + y) - 1) * self.tile_height for y in self.board.this_piece.y]
            for x, y in zip(xs, ys):
                self.draw_tile(self.gamecanvas, leftmargin+x, topmargin+y, self.board.this_piece.shape)
                logging.debug("gameboard draw (%s,%s) shape %s", leftmargin+x, topmargin+y, self.board.this_piece.shape)
        # draw the square to hold the next piece
        center_x, center_y = 45, 45
        self.hintcanvas.delete("all")
        self.hintcanvas.create_rectangle(1, 1, 88, 88, fill="#F0F0F0")
        # position the piece at center
        min_x, min_y = min(self.board.next_piece.x), min(self.board.next_piece.y)
        shape_width = (max(self.board.next_piece.x) + 1 - min_x) * self.tile_width
        shape_height = (max(self.board.next_piece.y) + 1 - min_y) * self.tile_height
        offset_x = center_x - shape_width // 2 - min_x * self.tile_width
        offset_y = center_y + shape_height // 2 + (min_y-1) * self.tile_height
        xs = [offset_x+x * self.tile_width for x in self.board.next_piece.x]
        ys = [offset_y-y * self.tile_height for y in self.board.next_piece.y]
        for x, y in zip(xs, ys):
            logging.debug("dashboard draw (%s,%s) shape %s", x, y, self.board.next_piece.shape)
            self.draw_tile(self.hintcanvas, x, y, self.board.next_piece.shape)

    def OnTimer(self):
        if self.board.neednewpiece:
            # first timer after full row is removed, generate new piece instead of moving down
            if self.board.make_new_piece():
                logging.debug("This: %s; next: %s", self.board.this_piece.shape, self.board.next_piece.shape)
            else:
                # cannot even place the shape at top middle of the board, finish the game
                self.timer = None
                self.message.config(text="Game over")
                self.config(bg="#E1E1E1")
                logging.debug("game over")
                return # do not restart timer
        else:
            # normal: move the current piece down for one row
            logging.debug("moving piece down, curr_y = %d", self.board.cur_y)
            self.move_down()
        # re-fire
        if self.timer:
            self.parent.after_cancel(self.timer) # in case after already set up
        self.timer = self.parent.after(self.speed, self.OnTimer)

    def OnKeyDown(self, event):
        if not self.board.started or self.board.this_piece.shape == Tetrominoes.NoShape:
            logging.debug("not started - ignore input")
            return
        logging.debug("OnKeyDown: key=%r", event.keysym)
        if event.char in ["P", "p"]:
            self.pause()
            return
        if self.board.paused:
            return
        if event.keysym == "Left":
            self.try_move(self.board.this_piece, -1)
        elif event.keysym == "Right":
            self.try_move(self.board.this_piece, +1)
        elif event.keysym == "Down":
            self.try_move(self.board.this_piece.rotate_ccw(), 0)
        elif event.keysym == "Up":
            self.try_move(self.board.this_piece.rotate_cw(), 0)
        elif event.char == " ":
            self.drop_down()
        elif event.char in ["D", "d"]:
            self.move_down()
```

Obviously, we see some differences between the way wx and Tk should be used.
For example, wx provide key code on a key event but Tk gives key symbol names
as a string, in case of non-alphanumeric keys are pressed. As expected, all
widgets have a different interface to update (e.g.
`self.message.config(text="")` in Tk vs `self.message.SetLabel("")` in wx). But
the most crucial difference between them is the way timer is handled. In
wxPython, a timer is continuously firing at regular interval until it is
stopped. But tkinter's timer is fired once only and you have to set it again
after each fire. Therefore we see in the above code we frequently cancel a
timer and set it again:

```python
if self.timer:
    self.parent.after_cancel(self.timer)
self.timer = self.parent.after(self.speed, self.OnTimer)
```
