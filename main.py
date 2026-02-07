from dataclasses import dataclass, field
from random import choice, choices
from typing import Union, Iterable
from enum import IntEnum
from tomllib import load
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
import sys

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class Axis(IntEnum):
    Y = 0
    X = 1

@dataclass(frozen=True)
class ChoiceSet:
    title: str
    data: Union[list, tuple, dict] = field(repr=False)
    eps: float = 1e-9

    def get_title(self):
        return self.title

    def get_option(self, index: int):
        if index < 0 or index > len(self.data) - 1:
            raise IndexError(f"Индекс {index} находится за гранью значений [{self.title}]")

        options = self.data if isinstance(self.data, (list, tuple)) else list(self.data.values())
        result = options[index]

        return result

    def get_index(self, option: str):
        options = self.data if isinstance(self.data, (list, tuple)) else list(self.data.values())
        try:
            result = options.index(option)
        except ValueError:
            result = -1

        return result

    def choose(self, exclude: Iterable[str] = None):
        if exclude:
            exclude_set = set(exclude)
            filter_needed = True
        else:
            exclude_set = set()
            filter_needed = False

        # Равновероятный выбор
        if isinstance(self.data, (list, tuple)):
            options = self.data if not filter_needed else [item for item in self.data if item not in exclude_set]
            if not options:
                raise ValueError(f"Нет доступных вариантов [{self.title}] после исключения")
            return choice(options)

        # Взвешенный выбор
        if isinstance(self.data, dict):
            options = self.data if not filter_needed else {k: v for k, v in self.data.items() if k not in exclude_set}
            if not options:
                raise ValueError(f"Нет доступных вариантов [{self.title}] после исключения")
            return choices(
                list(options.keys()),
                weights=list(options.values()),
                k=1
            )[0]

        raise TypeError(f"Неподдерживаемый тип данных [{self.title}]")

def read_config():
    config_name = "config.toml"
    with open(config_name, "rb") as f:
        config = load(f)

        length = config["field"]["length"]
        width = config["field"]["width"]

        if length <= 0 or width <= 0:
            raise ValueError(f"Размеры поля не соответствуют требованиям! (length = {length}, width = {width})")

        directions_data = {
            "Вперёд": config["direction_probabilities"]["forward"],
            "Назад": config["direction_probabilities"]["backward"],
            "Влево": config["direction_probabilities"]["leftward"],
            "Вправо": config["direction_probabilities"]["rightward"],
            "Вверх": config["direction_probabilities"]["upward"],
            "Вниз": config["direction_probabilities"]["downward"]
        }

        useful_title = config["useful_trait"]["title"]
        useful_data = [
            config["useful_trait"]["truth"],
            config["useful_trait"]["lies"],
            config["useful_trait"]["repeat"]
        ]

        useless_titles = config["useless_traits"]["titles"]
        useless_data = config["useless_traits"]["data"]

        if len(useless_titles) != len(useless_data):
            raise ValueError(f"Кол-во заголовков и наборов данных для бесполезных признаков не одинаково! "
                             f"({len(useless_titles)} в заголовках и {len(useless_data)} в признаках)")

    return length, width, directions_data, useful_title, useful_data, useless_titles, useless_data

def determine_honesty(current_head: str, previous_head: str):
    head_type = previous_head if current_head == "Повтор" else current_head
    return True if head_type == "Ложь" else False

def flip_direction(right_direction: str):
    wrong_direction = "Что-то пошло не так..."
    
    if right_direction == "Вперёд": wrong_direction = "Назад"
    if right_direction == "Назад": wrong_direction = "Вперёд"
    if right_direction == "Влево": wrong_direction = "Вправо"
    if right_direction == "Вправо": wrong_direction = "Влево"
    if right_direction == "Вниз": wrong_direction = "Вверх"
    if right_direction == "Вверх": wrong_direction = "Вниз"
    
    return wrong_direction

def get_head_text(head_type: str, previous_head_type: str, straight_direction: str, heads: ChoiceSet, useful_trait: ChoiceSet, useless_traits: list[ChoiceSet]):
    head_text = ""

    head_type_text = "Что-то пошло не так..."
    if head_type == "Правда":
        head_type_text = "правды"
    if head_type == "Ложь":
        head_type_text = "лжи"
    if head_type == "Повтор":
        head_type_text = "повтора"

    is_lying = determine_honesty(head_type, previous_head_type)
    direction_text = flip_direction(straight_direction) if is_lying else straight_direction

    head_text += f"Голова ({head_type_text}) говорит: \"{direction_text}!\"\n\n"
    head_text += f"Описание:\n"
    head_text += f"{useful_trait.get_title()} - {useful_trait.get_option(heads.get_index(head_type))}\n"

    for trait in useless_traits:
        head_text += f"{trait.get_title()} - {trait.choose()}\n"

    return head_text

@dataclass
class GameState:
    pos: list[int]
    next_pos: list[int]
    head: str | None
    width: int
    length: int

def translate_direction(dir_eng:str):
    dirs = {
        "shift+up": "Вверх",
        "shift+down": "Вниз",
        "left": "Влево",
        "right": "Вправо",
        "up": "Вперёд",
        "down": "Назад"
    }
    return dirs[dir_eng]

def merge_columns(left: str, right: str, gap: int = 4) -> str:
    left_lines = left.splitlines()
    right_lines = right.splitlines()

    max_left = max(len(line) for line in left_lines) if left_lines else 0
    height = max(len(left_lines), len(right_lines))

    left_lines += [""] * (height - len(left_lines))
    right_lines += [""] * (height - len(right_lines))

    result = []
    for l, r in zip(left_lines, right_lines):
        result.append(l.ljust(max_left) + " " * gap + r)

    return "\n".join(result)


class PuzzleApp(App):
    def on_mount(self) -> None:
        self.heads = ChoiceSet(
            title="Головы",
            data=["Правда", "Ложь", "Повтор"]
        )

        length, width, directions_data, useful_title, useful_data, useless_titles, useless_data = read_config()

        self.directions = ChoiceSet(
            title="Направление движения",
            data=directions_data
        )

        self.useful_trait = ChoiceSet(
            title=useful_title,
            data=useful_data
        )

        self.useless_traits = [
            ChoiceSet(title=t, data=d) for t, d in zip(useless_titles, useless_data)
        ]

        self.state = GameState(
            pos=[0, width // 2],
            next_pos=[0, width // 2],
            head=None,
            width=width,
            length=length,
        )

        self.text = self.get_coords()
        self.field_text = self.get_field(self.state)

        text = merge_columns(self.field_text, self.text)
        self.status.update(text)
        self.query_one("#random_step", Button).focus()

    def get_coords(self):
        return f"Координаты: ({self.state.pos[Axis.Y]},{self.state.pos[Axis.X]})\n"

    def get_next_coords(self):
        return f"Следующие координаты: ({self.state.next_pos[Axis.Y]},{self.state.next_pos[Axis.X]})\n\n"

    def get_field(self, field_state: GameState):
        empty_cell = "□"
        current_cell = "■"
        future_cell = "▣"

        result = ""

        for i in range(field_state.length - 1, -1, -1):
            for j in range(field_state.width):
                current_symbol = empty_cell
                if i == field_state.next_pos[Axis.Y] and j == field_state.next_pos[Axis.X]:
                    current_symbol = future_cell
                if i == field_state.pos[Axis.Y] and j == field_state.pos[Axis.X]:
                    current_symbol = current_cell

                result += current_symbol

                if j != field_state.width - 1: result += " "
            if i != 0: result += "\n"

        return result

    def make_step(self, forced: str | None = None) -> None:
        state = self.state
        heads = self.heads
        directions = self.directions
        useful_trait = self.useful_trait
        useless_traits = self.useless_traits

        self.text = self.get_coords()
        state.pos = state.next_pos.copy()
        self.check_victory()
        if getattr(self, "waiting_for_exit", False): return

        banned = []
        if state.pos[Axis.Y] - 1 < 0: banned.append("Назад")
        if state.pos[Axis.Y] + 1 > state.length: banned.append("Вперёд")
        if state.pos[Axis.X] - 1 < 0: banned.append("Влево")
        if state.pos[Axis.X] + 1 > state.width - 1: banned.append("Вправо")

        if forced not in banned:
            direction = forced if forced is not None else directions.choose(banned)

            moves = {"Вперёд": (1, 0), "Назад": (-1, 0), "Влево": (0, -1), "Вправо": (0, 1)}
            dy, dx = moves.get(direction, (0, 0))
            state.next_pos[Axis.Y] += dy
            state.next_pos[Axis.X] += dx

            state.head = heads.choose(exclude=["Повтор"]) if state.head is None else heads.choose()
            last_head = state.head

            self.text += self.get_next_coords()
            self.text += f"Направление: {direction}\n"
            self.text += get_head_text(
                state.head, last_head, direction,
                heads, useful_trait, useless_traits
            )
            self.status.update(self.text)

        self.field_text = self.get_field(self.state)
        text = merge_columns(self.field_text, self.text)
        self.status.update(text)

    def check_victory(self):
        state = self.state
        if state.pos[Axis.Y] == state.length - 1:
            self.status.update("[bold green]Победа![/bold green]\nНажми любую клавишу для выхода")
            self.waiting_for_exit = True

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                self.status = Static("")
                yield self.status
            with Vertical():
                with Horizontal():
                    yield Button("Вверх\nShift + ↑", id="step_shift_plus_up")
                    yield Button("Вперёд\n↑", id="step_up")
                    yield Button("Перезапуск\nR", id="restart")
                with Horizontal():
                    yield Button("Влево\n←", id="step_left")
                    yield Button("Случайный шаг\nПробел", id="random_step")
                    yield Button("Вправо\n→", id="step_right")
                with Horizontal():
                    yield Button("Вниз\nShift + ↓", id="step_shift_plus_down")
                    yield Button("Назад\n↓", id="step_down")
                    yield Button("Выход\nQ", id="quit")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if getattr(self, "waiting_for_exit", False):
            self.exit()
        else :
            if event.button.id == "random_step":
                self.make_step()
            elif event.button.id.startswith("step_"):
                dir = event.button.id.replace("step_", "")
                dir = dir.replace("_plus_", "+")
                self.make_step(forced=translate_direction(dir_eng=dir))
            elif event.button.id == "restart":
                self.on_mount()
            elif event.button.id == "quit":
                self.exit()

    def on_key(self, event: Key) -> None:
        if getattr(self, "waiting_for_exit", False):
            self.exit()
            return
        elif event.key == "space":
            self.make_step()
        elif event.key in {"left", "up", "down", "right", "shift+up", "shift+down"}:
            self.make_step(forced=translate_direction(dir_eng=event.key))
        elif event.key.lower() in {"r","к"}:
            self.on_mount()
        elif event.key.lower() in {"q", "й"}:
            self.exit()


if __name__ == '__main__':
    PuzzleApp().run()