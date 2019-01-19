#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tetris implementation in Tkinter with one wide panel contain both the game and the dashboard
"""
from __future__ import annotations

from enum import IntEnum, unique
from typing import Tuple, List, Callable
import random
import logging
import tkinter

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)-15s|%(levelname)s|%(filename)s:%(lineno)d:%(name)s|%(message)s")

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

    def __init__(self, shape: Tetrominoes = Tetrominoes.NoShape):
        """Construct a new shape. The variable self.coords is pre-created and later on modified
        in-place. It should not be a reference to Shape.shapeCoords as it will be modified when
        the shape is moved.
        """
        self.coords = [list(x) for x in Shape.shapeCoords[shape]]
        self._shape = shape

    @property
    def shape(self) -> Tetrominoes:
        """return shape of this piece"""
        return self._shape

    @shape.setter
    def shape(self, shape: Tetrominoes) -> None:
        """Reset this piece to another shape, with self.coords updated
        """
        self.coords[:] = [list(x) for x in self.shapeCoords[shape]]
        self._shape = shape

    @staticmethod
    def randomize() -> Shape:
        """Give a random piece"""
        shape = Tetrominoes(random.randint(1, len(Shape.shapeCoords)-1))
        return Shape(shape)

    @property
    def x(self) -> List[int]:
        "All x-coordinate of a shape's tiles"
        return [coord[0] for coord in self.coords]

    @property
    def y(self) -> List[int]:
        "All y-coordinate of a shape's tiles"
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

class TetrisBoard:
    """A python class overriding __setitem__ and __getitem__ to hold the state of a Tetris board
    The coordinate system has x going positive toward right and y going positive upward
    """
    def __init__(self, width: int = 10, height: int = 18):
        """Set the tiles dimension in the game board. Gameboy Tetris is 10x18"""
        self.nTilesH = width  # i.e., row size in num of square tiles
        self.nTilesV = height # i.e., col size in num of square tiles
        # row major array to hold tiles, from the tile we can look up the shape
        self.tiles : List[Tetrominoes] = []
        self.clear()

    def __setitem__(self, key: Tuple[int, int], value: Tetrominoes) -> None:
        """Setter to allow board[x,y] = shape syntax"""
        col, row = key # board[x,y] -> key will be a tuple
        self.tiles[row*self.nTilesH + col] = value

    def __getitem__(self, key: Tuple[int, int]) -> Tetrominoes:
        """Setter to allow board[x,y] syntax"""
        col, row = key # board[x,y] -> key will be a tuple
        return self.tiles[row*self.nTilesH + col]

    def clear(self) -> None:
        """Fill the board with "no shape" pieces"""
        self.tiles[:] = [Tetrominoes.NoShape] * (self.nTilesV * self.nTilesH)

    def check_pos(self, piece: Shape, x: int, y: int) -> bool:
        """Check the validity of placing the a piece at position (x,y)

        Returns:
            boolean for whether it is valid to place the piece at (x,y)
        """
        logging.debug("check_pos %s shape on (%d, %d)", piece.shape, x, y)
        coords = [[px+x, py+y] for px, py in piece.coords if py+y < self.nTilesV]
        if not coords:
            logging.debug("fail for fully above the board: %s -> %s", piece.coords, coords)
            return False
        if not all(0 <= cx < self.nTilesH and cy >= 0 for cx, cy in coords):
            logging.debug("fail for crossing board boundary: %s -> %s", piece.coords, coords)
            return False
        if any(self[cx, cy] != Tetrominoes.NoShape for cx, cy in coords):
            logging.debug("fail for collision")
            return False
        return True # all other cases is OK

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
        notfull = [y for y in range(self.nTilesV)
                   if any(self[x, y] == Tetrominoes.NoShape for x in range(self.nTilesH))]
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

class TetrisGame(TetrisBoard):
    """Tetris game with logic. Implement all interface-independent logic here"""
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
        self.score = 0              # Track score
        self.level = 0              # Track level

    def start(self) -> bool:
        """Trigger start of the game. Initialize everything.

        Returns:
            Boolean to indicate the game started successfully. It failed to start only if the game
            has been paused.
        """
        if self.paused:
            return False
        self.started = True
        self.neednewpiece = False
        self.rows_completed = 0
        self.score = 0
        self.level = 1
        self.next_piece = Shape.randomize()
        self.make_new_piece()
        self.clear()
        return True

    def make_new_piece(self) -> bool:
        """Generate a new piece of tetromino. If we cannot place it in the default position, the
        game is finished.

        Returns:
            Boolean to indicate we can still generate a new piece and place it on the board
        """
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
        """Toggle pause state

        Returns:
            Whether the game is paused. If the game is not started, always True
        """
        if not self.started:
            return True
        self.paused = not self.paused
        return self.paused

    def try_pos(self, piece: Shape, x: int, y: int) -> bool:
        """Attempt to place a piece onto the game board such that its origin is at position (x, y).
        The piece is not registered on the board but will check against the board for collision. If
        the position is valid, such positions are remembered as self.cur_x and self.cur_y and the
        piece is replacing self.this_piece

        Returns:
            Boolean to indicate whether this piece and position is valid
        """
        if self.check_pos(piece, x, y):
            # this position is good, remember it
            self.this_piece = piece
            self.cur_x = x
            self.cur_y = y
            return True
        return False # the piece cannot be placed at this position

    def piece_dropped(self) -> None:
        """Call this only if try_pos() failed on the lowest position self.cur_y-1. This merge in
        self.this_piece into the board, remove all existing full rows, and move down all the rows
        above them. It also hint for generating a new piece in the next step.  This is the only
        place the flag self.neednewpiece is asserted.
        """
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
        """Move self.this_piece one row down, i.e., to self.cur_y-1. If we cannot move down, call
        self.piece_dropped() to update the game state

        Returns:
            Boolean to indicate if we can successfully move the current piece to one row down
        """
        if self.try_pos(self.this_piece, self.cur_x, self.cur_y - 1):
            return True
        self.piece_dropped()
        return False

#
# GUI classes
#

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
        "Width of a square tile in number of pixels"
        return self.gamecanvas.winfo_width() // self.board.nTilesH

    @property
    def tile_height(self) -> int:
        "Height of a square tile in number of pixels"
        return self.gamecanvas.winfo_height() // self.board.nTilesV

    def start(self) -> None:
        """Trigger start of the game. The important thing here is to start the timer for a regular
        interval of self.speed after initializing all state variables
        """
        if self.board.start():
            self.message.config(text="")
            if self.timer:
                self.parent.after_cancel(self.timer) # in case after already set up
            self.timer = self.parent.after(self.speed, self.OnTimer) # timer fire regularly in pulses
            logging.debug("game started: %s", self.board.started)

    def pause(self) -> None:
        """Toggle pause state: update status bar message and set/stop timers"""
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
        """Move one row down, if we cannot, trigger the on_dropped() function to check for completed
        rows

        Returns:
            Whether we have successfully moved the piece to one row down
        """
        moved = self.board.one_row_down()
        self.Refresh()
        return moved

    def drop_down(self) -> None:
        """Move the piece down one row at a time until we are at the bottom row or we cannot move
        further down, then trigger the on_dropped() function to check for completed rows
        """
        while self.move_down():
            pass
        logging.debug("drop piece to curr_y = %d", self.board.cur_y)

    def try_move(self, piece, x_delta) -> None:
        """Attempt to place a piece such that the piece's origin is at position (ref_x, ref_y). The
        piece is not registered on the board but check against the board for collision.
        """
        if self.board.try_pos(piece, self.board.cur_x + x_delta, self.board.cur_y):
            logging.debug("Moved %s to (%s,%s)", piece.shape, self.board.cur_x, self.board.cur_y)
            self.Refresh()
        else:
            logging.debug("Cannot move %s to (%s,%s)", piece.shape, self.board.cur_x+x_delta, self.board.cur_y)

    def draw_tile(self, canvas, x: int, y: int, shape: Tetrominoes) -> None:
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
        canvas.create_line(x, y+H-1, x, y, fill=light[shape])
        canvas.create_line(x, y, x+W-1, y, fill=light[shape])
        # draw top and right edge, with dark color
        canvas.create_line(x+1, y+H-1, x+W-1, y+H-1, fill=dark[shape])
        canvas.create_line(x+W-1, y+H-1, x+W-1, y+1, fill=dark[shape])
        # fill square
        canvas.create_rectangle(x+1, y+1, x+W-1, y+H-1, fill=colors[shape])

    def Refresh(self):
        """Paint event handler. Triggered when window's contents need to be repainted. Canvas
        coordinate is x going positive toward right and y going positive downwards
        """
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
        """Timer fire: normally move one line down (like D key event), otherwise
        produce new shape
        """
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
        """Left/right/up/down key for move and rotate, space for drop, d for one
        line down, p for pause, all other ignore (pass on to next handler)
        """
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

def main():
    root = tkinter.Tk()
    game = Tetris(root)
    game.start()
    root.mainloop()

if __name__ == "__main__":
    main()

# vim:set fdm=indent tw=100 et ts=4 sw=4:
