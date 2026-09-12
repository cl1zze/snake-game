#!/usr/bin/env python3
"""Классическая Змейка для терминала на curses."""
import curses
import random
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from typing import Deque, Tuple

Point = Tuple[int, int]


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def opposite(self) -> "Direction":
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]


@dataclass
class GameState:
    width: int
    height: int
    snake: Deque[Point] = field(default_factory=deque)
    direction: Direction = Direction.RIGHT
    next_direction: Direction = Direction.RIGHT
    food: Point = (0, 0)
    score: int = 0
    best: int = 0
    game_over: bool = False
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        cx, cy = self.width // 2, self.height // 2
        self.snake = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.food = self._spawn_food()

    # ---------- логика ----------
    def _spawn_food(self) -> Point:
        empty = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) not in self.snake
        ]
        return self.rng.choice(empty) if empty else (0, 0)

    def change_direction(self, new: Direction) -> None:
        # нельзя развернуться на 180°
        if new != self.direction.opposite:
            self.next_direction = new

    def step(self) -> None:
        if self.game_over:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction.value
        new_head = (head_x + dx, head_y + dy)

        # столкновение со стеной
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self._end()
            return

        # столкновение с собой (хвост освободится, если не едим)
        body = set(self.snake)
        if new_head == self.snake[-1]:
            body.discard(self.snake[-1])
        if new_head in body:
            self._end()
            return

        self.snake.appendleft(new_head)

        if new_head == self.food:
            self.score += 1
            self.best = max(self.best, self.score)
            self.food = self._spawn_food()
        else:
            self.snake.pop()

    def _end(self) -> None:
        self.game_over = True


# ---------- отрисовка ----------
def draw(stdscr, state: GameState, paused: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # рамка
    top = "+" + "-" * state.width + "+"
    bottom = top
    try:
        stdscr.addstr(0, 0, top)
        for y in range(state.height):
            stdscr.addstr(y + 1, 0, "|")
            stdscr.addstr(y + 1, state.width + 1, "|")
        stdscr.addstr(state.height + 1, 0, bottom)
    except curses.error:
        pass

    # еда
    fx, fy = state.food
    try:
        stdscr.addstr(fy + 1, fx + 1, "●", curses.color_pair(2))
    except curses.error:
        pass

    # змейка
    for i, (x, y) in enumerate(state.snake):
        ch = "@" if i == 0 else "o"
        attr = curses.color_pair(3) if i == 0 else curses.color_pair(1)
        try:
            stdscr.addstr(y + 1, x + 1, ch, attr)
        except curses.error:
            pass

    # HUD
    hud_y = state.height + 3
    info = f" Счёт: {state.score}   Рекорд: {state.best} "
    if paused:
        info += "  [ПАУЗА] "
    try:
        stdscr.addstr(hud_y, 0, info[: w - 1])
        stdscr.addstr(
            hud_y + 1, 0,
            " Управление: WASD/стрелки · P — пауза · Q — выход "[: w - 1],
        )
    except curses.error:
        pass

    if state.game_over:
        msg = " GAME OVER! Нажми R для рестарта или Q для выхода "
        y = state.height // 2 + 1
        x = max(0, (state.width + 2 - len(msg)) // 2)
        try:
            stdscr.addstr(y, x, msg, curses.A_BOLD | curses.color_pair(4))
        except curses.error:
            pass

    stdscr.refresh()


# ---------- главный цикл ----------
KEY_MAP = {
    curses.KEY_UP: Direction.UP,
    curses.KEY_DOWN: Direction.DOWN,
    curses.KEY_LEFT: Direction.LEFT,
    curses.KEY_RIGHT: Direction.RIGHT,
    ord("w"): Direction.UP,
    ord("s"): Direction.DOWN,
    ord("a"): Direction.LEFT,
    ord("d"): Direction.RIGHT,
}


def run(stdscr) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # тело
    curses.init_pair(2, curses.COLOR_RED, -1)     # еда
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  # голова
    curses.init_pair(4, curses.COLOR_MAGENTA, -1) # надписи

    def make_state() -> GameState:
        h, w = stdscr.getmaxyx()
        # оставляем место для рамки и HUD
        return GameState(width=max(10, w - 4), height=max(10, h - 6))

    state = make_state()
    paused = False
    tick = 0
    speed = 6  # обновлений в секунду

    while True:
        ch = stdscr.getch()

        if ch == ord("q"):
            return

        if ch == ord("p") and not state.game_over:
            paused = not paused

        if ch == ord("r") and state.game_over:
            best = state.best
            state = make_state()
            state.best = best
            paused = False
            tick = 0

        if ch in KEY_MAP and not paused and not state.game_over:
            state.change_direction(KEY_MAP[ch])

        if not paused and not state.game_over:
            tick += 1
            if tick >= max(1, 30 // speed):
                state.step()
                tick = 0

        draw(stdscr, state, paused)
        curses.napms(30)


def main() -> None:
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    print("Спасибо за игру! 🐍")


if __name__ == "__main__":
    main()