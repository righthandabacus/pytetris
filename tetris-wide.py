#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Tetris implementation in wxPython with one wide panel contain both the game and the dashboard
#
from __future__ import annotations

from enum import IntEnum, unique
from typing import Tuple, List, Callable
import random
import logging

import wx

logging.basicConfig(level=logging.DEBUG, format="%(asctime)-15s|%(levelname)s|%(filename)s:%(lineno)d:%(name)s|%(message)s")

#
# Helper classes that are independent of the GUI library
#

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

class Shape(object):
    """7 tetrominoes shapes + dummy. We make x axis the top edge each shape, hence max y for shape
    coordinates should be 0
    """
    shapeCoords = (
        (( 0,  0), (0,  0), ( 0,  0), ( 0, 0)),  # 0 = NoShape
        (( 0, -3), (0, -2), ( 0, -1), ( 0, 0)),  # 1 = I
        ((-1, -2), (0, -2), ( 0, -1), ( 0, 0)),  # 2 = J
        (( 1, -2), (0, -2), ( 0, -1), ( 0, 0)),  # 3 = L
        (( 0, -1), (1, -1), ( 0,  0), ( 1, 0)),  # 4 = O
        (( 0, -2), (0, -1), (-1, -1), (-1, 0)),  # 5 = S
        (( 0, -1), (1,  0), ( 0,  0), (-1, 0)),  # 6 = T
        (( 0, -2), (0, -1), ( 1, -1), ( 1, 0)),  # 7 = Z
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

    @property
    def x(self) -> List[int]:
        return [coord[0] for coord in self.coords]

    @property
    def y(self) -> List[int]:
        return [coord[1] for coord in self.coords]

    def min_y(self) -> int:
        "Tell the min y-coordinate of this shape"
        return min(coords[1] for coords in self.coords)

    def _transform(self, transform: Callable) -> Shape:
        """Transform this shape with a callable function, used by self.rotateLeft() and
        self.rotateRight() only"""
        result = Shape(self.shape) # same piece
        result.coords = [transform(x, y) for x, y in self.coords]
        return result

    def rotate_cw(self) -> Shape:
        "Produce a piece of this shape rotate about origin for 90 deg cw"
        if self.shape == Tetrominoes.OShape:
            return self # no rotate for "O"
        cw = lambda x, y: [y, -x]
        return self._transform(cw)

    def rotate_ccw(self) -> Shape:
        "Produce a piece of this shape rotate about origin for 90 deg ccw"
        if self.shape == Tetrominoes.OShape:
            return self # no rotate for "O"
        ccw = lambda x, y: [-y, x]
        return self._transform(ccw)

class TetrisBoard(object):
    """A python class overriding __setitem__ and __getitem__ to hold the state of a Tetris board
    The coordinate system has x going positive toward right and y going positive upward
    """
    def __init__(self, width: int = 10, height: int = 18):
        """Set the tiles dimension in the game board. Gameboy Tetris is 10x18"""
        self.nTilesH = width  # i.e., row size in num of square tiles
        self.nTilesV = height # i.e., col size in num of square tiles
        # row major array to hold tiles, from the tile we can look up the shape
        self.tiles = []
        self.clear()

    def __setitem__(self, key: Tuple[int, int], value: Shape):
        """Setter to allow board[x,y] = shape syntax"""
        col, row = key # board[x,y] -> key will be a tuple
        self.tiles[row*self.nTilesH + col] = value

    def __getitem__(self, key: Tuple[int, int]) -> Shape:
        """Setter to allow board[x,y] syntax"""
        col, row = key # board[x,y] -> key will be a tuple
        return self.tiles[row*self.nTilesH + col]

    def clear(self):
        """Fill the board with "no shape" pieces"""
        self.tiles[:] = [Tetrominoes.NoShape] * (self.nTilesV * self.nTilesH)

    def check_pos(self, piece: Shape, x: int, y: int) -> bool:
        """Check the validity of placing the a piece at position (x,y)

        Returns:
            boolean for whether it is valid to place the piece at (x,y)
        """
        logging.debug("check_pos %s shape on (%d, %d)", piece.shape, x, y)
        coords = [[px+x, py+y] for px, py in piece.coords]
        if not all(0 <= cx < self.nTilesH and 0 <= cy < self.nTilesV for cx, cy in coords):
            logging.debug("fail for not fully within the board: %s -> %s", piece.coords, coords)
            return False    # the piece is not fully within the board
            # TODO relax cy < self.nTilesV condition to allow shape go over the top edge of the board
        if any(self[cx, cy] != Tetrominoes.NoShape for cx, cy in coords):
            logging.debug("fail for collision")
            return False    # the piece collide with something on the board
        return True         # all other cases is OK

    def fix_pos(self, piece: Shape, x: int, y: int) -> None:
        """Fix a piece at position (x, y), assumed corresponding check_pos() returns
        True. The board is updated after this function called.
        """
        coords = [[px+x, py+y] for px, py in piece.coords]
        for cx, cy in coords:
            self[cx, cy] = piece.shape

    def removefull(self) -> int:
        """Remove any full rows in the board. Move rows down and refill the top rows with
        NoShape. This board will be updated after this function call if any full rows are removed

        Returns:
            The number of rows removed
        """
        # Check each rows for what is not full
        notfull = [y for y in range(self.nTilesV) if any(self[x, y] == Tetrominoes.NoShape for x in range(self.nTilesH))]
        logging.debug("not full rows: %s", notfull)
        if self.nTilesV == len(notfull):
            return 0
        # Remove anything that is full
        move = [(i, j) for i, j in enumerate(notfull) if i != j]
        for j, k in move:
            logging.debug("Moving row %d to row %d", k, j)
            for i in range(self.nTilesH):
                self[i, j] = self[i, k]
        # Fill in any new rows at top with NoShape
        toprow = max(i for i, _ in move) + 1
        for j in range(toprow, self.nTilesV):
            logging.debug("filling empty row: %d", j)
            for i in range(self.nTilesH):
                self[i, j] = Tetrominoes.NoShape
        return self.nTilesV - len(notfull)

#
# GUI classes
#

class Tetris(wx.Frame):
    """The tetris game implemented in wxPython. Dummy class with logic reside in the board class
    """
    def __init__(self, parent, id=-1, title="Tetris"):
        """Inheriting from wx frame
        """
        super().__init__(parent, id, title=title, size=(180*2, 380),
                         style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        # create game board which this frame as parent
        self.gameboard = GameBoard(self)
        self.gameboard.SetFocus()
        self.gameboard.start()

class GameBoard(wx.Panel):
    """Tetris game board, all tetris logic are here. The board is operated in terms of tiles, which
    each tetris piece is four tiles. The drawing functions will be shared with the Dashboard panel.
    """
    speed = 300
    ID_TIMER = 1

    def __init__(self, *args, **kwargs):
        """constructor. This creates a lot of components and initializes parameters"""
        super().__init__(*args, **kwargs)
        self.SetBackgroundColour((255,255,255))
        nTilesH, nTilesV = 10, 18
        self.timer = wx.Timer(self, self.ID_TIMER)
        self.board = TetrisBoard(nTilesH, nTilesV)
        # This and next piece of tetrominoes
        self.this_piece = Shape()
        self.next_piece = Shape.randomize()
        logging.debug("next piece: %s", self.next_piece.shape)
        # State variable of the current piece: Current position
        self.cur_x = 0
        self.cur_y = 0
        # State variable of the game
        self.neednewpiece = False   # Old piece dropped. New piece to be created
        self.paused = False     # The game is paused, timer is suspended
        self.started = False    # The game is started, hence timer is on
        self.score = 0
        self.level = 1
        self.rows_completed = 0
        # dashboard components
        textfont = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False)
        wx.StaticText(self, -1, "SCORE", pos=(200, 15)).SetFont(textfont)
        wx.StaticText(self, -1, "LEVEL", pos=(200, 85)).SetFont(textfont)
        wx.StaticText(self, -1, "ROWS", pos=(200, 155)).SetFont(textfont)
        dashfont = wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False)
        self.scoretxt = wx.StaticText(self, -1, "0", pos=(220, 30), size=(100,30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.leveltxt = wx.StaticText(self, -1, "1", pos=(220, 100), size=(100,30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.rowstxt = wx.StaticText(self, -1, "0", pos=(220, 170), size=(100,30), style=wx.ALIGN_CENTRE_HORIZONTAL)
        for txt in [self.scoretxt, self.leveltxt, self.rowstxt]:
            txt.SetFont(dashfont)
        self.message = wx.StaticText(self, -1, "", pos=(185, 250), size=(170,50), style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.message.SetForegroundColour((255, 0, 0))
        self.message.SetFont(wx.Font(28, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        # bind events on panel
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_TIMER, self.OnTimer, id=self.ID_TIMER)
        # initialize: fill the board with NoShape pieces
        self.board.clear()

    @property
    def tile_width(self) -> int:
        "Width of a square tile in number of pixels"
        return self.GetClientSize().GetWidth() // 2 // self.board.nTilesH

    @property
    def tile_height(self) -> int:
        "Height of a square tile in number of pixels"
        return self.GetClientSize().GetHeight() // self.board.nTilesV

    def start(self) -> None:
        """Trigger start of the game. The important thing here is to start the timer for a regular
        interval of self.speed after initializing all state variables
        """
        if self.paused:
            return
        self.started = True
        self.neednewpiece = False
        self.score = 0
        self.level = 1
        self.rows_completed = 0
        self.message.SetLabel("")
        self.board.clear()
        self.make_new_piece()
        self.timer.Start(self.speed) # timer fire regularly in pulses
        logging.debug("started")

    def make_new_piece(self) -> None:
        """Generate a new piece of tetromino. If we can't place the tetromino, the game is finished
        and timer is turned off.
        """
        logging.debug("Make new piece")
        # generate a new piece
        self.this_piece = self.next_piece
        self.next_piece = Shape.randomize()
        self.neednewpiece = False
        logging.debug("This piece: %s; next piece: %s", self.this_piece.shape, self.next_piece.shape)
        # place the piece at top middle of the board
        self.cur_x = self.board.nTilesH // 2
        self.cur_y = self.board.nTilesV - 1
        if not self.board.check_pos(self.this_piece, self.cur_x, self.cur_y):
            # cannot even place the shape at top middle of the board, finish the game
            self.this_piece.shape = Tetrominoes.NoShape
            self.timer.Stop()
            self.started = False
            self.message.SetLabel("Game Over")
            self.SetBackgroundColour((225,225,225))

    def pause(self) -> None:
        """Toggle pause state: update status bar message and set/stop timers"""
        if not self.started:
            return
        self.paused = not self.paused
        if self.paused:
            self.message.SetLabel("Paused")
            self.SetBackgroundColour((225,225,225))
            self.timer.Stop()
        else:
            self.message.SetLabel("")
            self.SetBackgroundColour((255,255,255))
            self.timer.Start(self.speed)
        self.Refresh()

    def try_pos(self, piece, ref_x, ref_y):
        """Attempt to place a piece such that the piece's origin is at position (ref_x, ref_y). The
        piece is not registered on the board but check against the board for collision.
        """
        xs = [ref_x + x for x in piece.x]
        ys = [ref_y + y for y in piece.y]
        for x, y in zip(xs, ys):
            if not (0 <= x < self.board.nTilesH and 0 <= y < self.board.nTilesV):
                return False    # the piece is not within the board
            if self.board[x, y] != Tetrominoes.NoShape:
                return False    # the piece is collide with something on the board
        # all else: this is good, remember the position
        self.this_piece = piece
        self.cur_x = ref_x
        self.cur_y = ref_y
        self.Refresh() # wx function: redraw the board
        return True

    def one_row_down(self):
        """Move one row down, if we cannot, trigger the on_dropped() function to check for completed rows
        """
        if not self.try_pos(self.this_piece, self.cur_x, self.cur_y - 1):
            self.on_dropped()

    def drop_piece(self):
        """Move the piece down one row at a time until we are at the bottom row or we cannot move further
        down, then trigger the on_dropped() function to check for completed rows
        """
        for new_y in range(self.cur_y-1, -1, -1):
            if not self.try_pos(self.this_piece, self.cur_x, new_y):
                logging.debug("drop piece to curr_y = %d", self.cur_y)
                break
        self.on_dropped()

    def draw_tile(self, canvas: wx.PaintDC, x: int, y: int, shape: Shape):
        """On canvas dc, at pixel coordinate (x,y), draw shape. Color depends on shape.
        """
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

    def removefull(self):
        """Hide piece, remove full rows, and refresh the board display.
        This is the only place the flag self.neednewpiece is asserted
        """
        # hide piece
        self.neednewpiece = True
        self.this_piece.shape = Tetrominoes.NoShape
        # find all rows that are full and remove them
        rows_removed = self.board.removefull()
        logging.debug("%d rows removed", rows_removed)
        # then update status bar and redraw screen
        if rows_removed:
            self.rows_completed += rows_removed
            self.score += rows_removed * rows_removed
        # TODO update self.level
        self.Refresh()

    def OnPaint(self, event: wx.Event):
        """Paint event handler. Triggered when window's contents need to be repainted.
        Canvas coordinate is x going positive toward right and y going positive downwards
        """
        # update text component
        self.scoretxt.SetLabel(str(self.score))
        self.leveltxt.SetLabel(str(self.level))
        self.rowstxt.SetLabel(str(self.rows_completed))
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
        if self.this_piece.shape != Tetrominoes.NoShape:
            xs = [(self.cur_x + x) * self.tile_width for x in self.this_piece.x]
            ys = [(self.board.nTilesV - (self.cur_y + y) - 1) * self.tile_height for y in self.this_piece.y]
            for x, y in zip(xs, ys):
                self.draw_tile(canvas, x, topmargin+y, self.this_piece.shape)
        # draw the square to hold the next piece
        center_x, center_y = size.GetWidth()*3//4, 270
        rec_x = center_x - 2.5*self.tile_width
        rec_y = center_y - 2.5*self.tile_height
        canvas.SetPen(wx.Pen("#000000"))
        canvas.SetBrush(wx.Brush("#FFFFFF", style=wx.TRANSPARENT))
        canvas.DrawRectangle(rec_x, rec_y, 5*self.tile_width, 5*self.tile_height)
        logging.debug("dashboard rectangle (%s,%s)x(%s,%s)", rec_x, rec_y, 5*self.tile_width, 5*self.tile_height)
        # position the piece at center
        min_x, min_y = min(self.next_piece.x), min(self.next_piece.y)
        shape_width = (max(self.next_piece.x) + 1 - min_x) * self.tile_width
        shape_height = (max(self.next_piece.y) + 1 - min_y) * self.tile_height
        offset_x = center_x - shape_width // 2 - min_x * self.tile_width
        offset_y = center_y + shape_height // 2 + (min_y-1) * self.tile_height
        xs = [offset_x+x * self.tile_width for x in self.next_piece.x]
        ys = [offset_y-y * self.tile_height for y in self.next_piece.y]
        for x, y in zip(xs, ys):
            logging.debug("dashboard draw (%s,%s) shape %s", x, y, self.next_piece.shape)
            self.draw_tile(canvas, x, y, self.next_piece.shape)

    def OnKeyDown(self, event: wx.Event):
        """Left/right/up/down key for move and rotate, space for drop, d for one
        line down, p for pause, all other ignore (pass on to next handler)
        """
        logging.debug("OnKeyDown")
        if not self.started or self.this_piece.shape == Tetrominoes.NoShape:
            event.Skip()
            return
        keycode = event.GetKeyCode()
        logging.debug("OnKeyDown: keycode=%d", keycode)
        if keycode in [ord("P"), ord("p")]:
            self.pause()
            return
        if self.paused:
            return
        if keycode == wx.WXK_LEFT:
            self.try_pos(self.this_piece, self.cur_x - 1, self.cur_y)
        elif keycode == wx.WXK_RIGHT:
            self.try_pos(self.this_piece, self.cur_x + 1, self.cur_y)
        elif keycode == wx.WXK_DOWN:
            self.try_pos(self.this_piece.rotate_ccw(), self.cur_x, self.cur_y)
        elif keycode == wx.WXK_UP:
            self.try_pos(self.this_piece.rotate_cw(), self.cur_x, self.cur_y)
        elif keycode == wx.WXK_SPACE:
            self.drop_piece()
        elif keycode == ord("D") or keycode == ord("d"):
            self.one_row_down()
        else:
            event.Skip()

    def OnTimer(self, event: wx.Event):
        """Timer fire: normally move one line down (like D key event), otherwise
        produce new shape
        """
        if event.GetId() != self.ID_TIMER:
            event.Skip() # we don"t process this event
        elif self.neednewpiece:
            # first timer after full row is removed, generate new piece instead of moving down
            self.make_new_piece()
        else:
            # normal: move the current piece down for one row
            logging.debug("moving piece down, curr_y = %d", self.cur_y)
            self.one_row_down()

    def on_dropped(self):
        """The shape is fixed at the current position to the board, then check for full rows. Set
        self.neednewpiece flag is we scored a row. Otherwise start a new piece at top
        """
        logging.debug("on_dropped")
        xs = [self.cur_x + x for x in self.this_piece.x]
        ys = [self.cur_y + y for y in self.this_piece.y]
        for x, y in zip(xs, ys):
            logging.debug("fixing piece at (%d,%d): was %s now %s", x, y, self.board[x, y], self.this_piece.shape)
            self.board[x, y] = self.this_piece.shape
        self.removefull()
        if self.neednewpiece:
            self.make_new_piece()

def main():
    """main function to launch the game"""
    # Boilerplate style wx app launcher
    app = wx.App()
    win = Tetris(None, title="Tetris")
    win.Centre() # center the window on screen
    win.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()

# vim:set fdm=indent tw=100 et ts=4 sw=4:
