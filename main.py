from dataclasses import dataclass, field
from random import choice, choices
from typing import Union, Iterable
from enum import IntEnum
from tomllib import load

from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal


class Axis(IntEnum):
    """Оси координат игрового поля."""
    Y = 0
    X = 1


@dataclass(frozen=True)
class ChoiceSet:
    """
    Универсальный контейнер вариантов выбора.

    Поддерживает:
    - равновероятный выбор из списка / кортежа;
    - взвешенный выбор из словаря.

    Используется для голов, направлений и признаков.
    """

    title: str
    data: Union[list, tuple, dict] = field(repr=False)
    eps: float = 1e-9

    def get_title(self) -> str:
        """Вернуть заголовок набора."""
        return self.title

    def get_option(self, index: int):
        """
        Получить вариант по индексу.

        :param index: Индекс варианта
        :raises IndexError: если индекс вне диапазона
        """
        if index < 0 or index > len(self.data) - 1:
            raise IndexError(
                f"Индекс {index} находится за гранью значений [{self.title}]"
            )

        options = self.data if isinstance(self.data, (list, tuple)) else list(self.data.values())
        return options[index]

    def get_index(self, option: str) -> int:
        """
        Получить индекс варианта.

        :param option: Значение варианта
        :return: индекс или -1, если не найден
        """
        options = self.data if isinstance(self.data, (list, tuple)) else list(self.data.values())
        try:
            return options.index(option)
        except ValueError:
            return -1

    def choose(self, exclude: Iterable[str] | None = None):
        """
        Выбрать вариант случайным образом.

        :param exclude: Набор исключаемых значений
        :raises ValueError: если вариантов не осталось
        """
        exclude_set = set(exclude) if exclude else set()

        if isinstance(self.data, (list, tuple)):
            options = [v for v in self.data if v not in exclude_set]
            if not options:
                raise ValueError(f"Нет доступных вариантов [{self.title}] после исключения")
            return choice(options)

        if isinstance(self.data, dict):
            options = {k: v for k, v in self.data.items() if k not in exclude_set}
            if not options:
                raise ValueError(f"Нет доступных вариантов [{self.title}] после исключения")
            return choices(
                list(options.keys()),
                weights=list(options.values()),
                k=1
            )[0]

        raise TypeError(f"Неподдерживаемый тип данных [{self.title}]")


def read_config():
    """
    Прочитать конфигурацию из файла config.toml.

    :return: Параметры игрового поля, направлений и признаков
    :raises ValueError: при некорректных данных
    """
    with open("config.toml", "rb") as f:
        config = load(f)

    length = config["field"]["length"]
    width = config["field"]["width"]

    if length <= 0 or width <= 0:
        raise ValueError(
            f"Размеры поля не соответствуют требованиям! "
            f"(length = {length}, width = {width})"
        )

    directions_data = {
        "Вперёд": config["direction_probabilities"]["forward"],
        "Назад": config["direction_probabilities"]["backward"],
        "Влево": config["direction_probabilities"]["leftward"],
        "Вправо": config["direction_probabilities"]["rightward"],
        "Вверх": config["direction_probabilities"]["upward"],
        "Вниз": config["direction_probabilities"]["downward"],
    }

    useful_title = config["useful_trait"]["title"]
    useful_data = [
        config["useful_trait"]["truth"],
        config["useful_trait"]["lies"],
        config["useful_trait"]["repeat"],
    ]

    useless_titles = config["useless_traits"]["titles"]
    useless_data = config["useless_traits"]["data"]

    if len(useless_titles) != len(useless_data):
        raise ValueError(
            "Кол-во заголовков и наборов данных для бесполезных признаков не одинаково!"
        )

    return (
        length,
        width,
        directions_data,
        useful_title,
        useful_data,
        useless_titles,
        useless_data,
    )


def determine_honesty(current_head: str, previous_head: str) -> bool:
    """
    Определить, говорит ли голова правду.

    :return: True — ложь, False — правда
    """
    head_type = previous_head if current_head == "Повтор" else current_head
    return head_type == "Ложь"


def flip_direction(right_direction: str) -> str:
    """
    Инвертировать направление движения.

    :param right_direction: Исходное направление
    """
    mapping = {
        "Вперёд": "Назад",
        "Назад": "Вперёд",
        "Влево": "Вправо",
        "Вправо": "Влево",
        "Вверх": "Вниз",
        "Вниз": "Вверх",
    }
    return mapping.get(right_direction, "Что-то пошло не так...")


def get_head_text(
    head_type: str,
    previous_head_type: str,
    straight_direction: str,
    banned: list[str],
    heads: ChoiceSet,
    useful_trait: ChoiceSet,
    useless_traits: list[ChoiceSet],
) -> str:
    """
    Сформировать текст реплики головы.

    :return: Многострочный текст описания
    """
    head_type_text = {
        "Правда": "правды",
        "Ложь": "лжи",
        "Повтор": "повтора",
    }.get(head_type, "неизвестно")

    is_lying = determine_honesty(head_type, previous_head_type)

    if is_lying:
        candidate = flip_direction(straight_direction)
        direction_text = (
            candidate if candidate not in banned else "Выйди за поле"
        )
    else:
        direction_text = straight_direction

    text = (
        f"Голова ({head_type_text}) говорит: "
        f"\"{direction_text}!\"\n\n"
        f"Описание:\n"
        f"{useful_trait.get_title()} - "
        f"{useful_trait.get_option(heads.get_index(head_type))}\n"
    )

    for trait in useless_traits:
        text += f"{trait.get_title()} - {trait.choose()}\n"

    return text


@dataclass
class GameState:
    """Текущее состояние игры."""
    pos: list[int]
    next_pos: list[int]
    head: str | None
    width: int
    length: int


def translate_direction(dir_eng: str) -> str:
    """
    Перевести клавиатурное направление в игровое.
    """
    return {
        "shift+up": "Вверх",
        "shift+down": "Вниз",
        "left": "Влево",
        "right": "Вправо",
        "up": "Вперёд",
        "down": "Назад",
    }[dir_eng]


def merge_columns(left: str, right: str, gap: int = 4) -> str:
    """
    Объединить два текстовых блока в колонки.

    :param gap: Количество пробелов между колонками
    """
    left_lines = left.splitlines()
    right_lines = right.splitlines()

    max_left = max((len(line) for line in left_lines), default=0)
    height = max(len(left_lines), len(right_lines))

    left_lines += [""] * (height - len(left_lines))
    right_lines += [""] * (height - len(right_lines))

    return "\n".join(
        l.ljust(max_left) + " " * gap + r
        for l, r in zip(left_lines, right_lines)
    )


class PuzzleApp(App):
    """Основное приложение Textual."""

    def on_mount(self) -> None:
        """Инициализация игры и интерфейса."""
        self.heads = ChoiceSet("Головы", ["Правда", "Ложь", "Повтор"])

        (
            length,
            width,
            directions_data,
            useful_title,
            useful_data,
            useless_titles,
            useless_data,
        ) = read_config()

        self.directions = ChoiceSet("Направление движения", directions_data)
        self.useful_trait = ChoiceSet(useful_title, useful_data)
        self.useless_traits = [
            ChoiceSet(t, d) for t, d in zip(useless_titles, useless_data)
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

        self.status.update(merge_columns(self.field_text, self.text))
        self.query_one("#random_step", Button).focus()

    def get_coords(self) -> str:
        """Текущие координаты игрока."""
        return f"Координаты: ({self.state.pos[Axis.Y]},{self.state.pos[Axis.X]})\n"

    def get_next_coords(self) -> str:
        """Следующие координаты игрока."""
        return (
            f"Следующие координаты: "
            f"({self.state.next_pos[Axis.Y]},{self.state.next_pos[Axis.X]})\n\n"
        )

    def get_field(self, field_state: GameState) -> str:
        """Сформировать текстовое представление поля."""
        empty_cell = "□"
        current_cell = "■"
        future_cell = "▣"

        result = ""

        for i in range(field_state.length - 1, -1, -1):
            for j in range(field_state.width):
                symbol = empty_cell
                if [i, j] == field_state.next_pos:
                    symbol = future_cell
                if [i, j] == field_state.pos:
                    symbol = current_cell
                result += symbol
                if j != field_state.width - 1:
                    result += " "
            if i != 0:
                result += "\n"

        return result

    def make_step(self, forced: str | None = None) -> None:
        """Сделать ход."""
        state = self.state
        self.text = self.get_coords()

        state.pos = state.next_pos.copy()
        self.check_victory()
        if getattr(self, "waiting_for_exit", False):
            return

        banned = []
        if state.pos[Axis.Y] - 1 < 0:
            banned.append("Назад")
        if state.pos[Axis.Y] + 1 > state.length - 1:
            banned.append("Вперёд")
        if state.pos[Axis.X] - 1 < 0:
            banned.append("Влево")
        if state.pos[Axis.X] + 1 > state.width - 1:
            banned.append("Вправо")

        if forced not in banned:
            previous_head = state.head

            state.head = (
                self.heads.choose(exclude=["Повтор"])
                if state.head is None
                else self.heads.choose()
            )

            if state.head == "Ложь" or (state.head == "Повтор" and previous_head == "Ложь") :
                if state.pos[Axis.Y] - 1 < 0:
                    banned.append("Вперёд")
                if state.pos[Axis.Y] + 1 > state.length - 1:
                    banned.append("Назад")
                if state.pos[Axis.X] - 1 < 0:
                    banned.append("Вправо")
                if state.pos[Axis.X] + 1 > state.width - 1:
                    banned.append("Влево")

            direction = forced or self.directions.choose(banned)
            dy, dx = {
                "Вперёд": (1, 0),
                "Назад": (-1, 0),
                "Влево": (0, -1),
                "Вправо": (0, 1),
            }.get(direction, (0, 0))

            state.next_pos[Axis.Y] += dy
            state.next_pos[Axis.X] += dx

            self.text += self.get_next_coords()
            self.text += f"Направление: {direction}\n"
            self.text += get_head_text(
                state.head,
                previous_head,
                direction,
                banned,
                self.heads,
                self.useful_trait,
                self.useless_traits,
            )

        self.field_text = self.get_field(self.state)
        self.status.update(merge_columns(self.field_text, self.text))

    def check_victory(self) -> None:
        """Проверка условия победы."""
        if self.state.pos[Axis.Y] == self.state.length - 1:
            self.status.update(
                "[bold green]Победа![/bold green]\n"
                "Нажми любую клавишу для выхода"
            )
            self.waiting_for_exit = True

    def compose(self) -> ComposeResult:
        """Построение интерфейса."""
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
        """Обработка нажатий кнопок."""
        if getattr(self, "waiting_for_exit", False):
            self.exit()
            return

        match event.button.id:
            case "random_step":
                self.make_step()
            case id if id.startswith("step_"):
                direction = (
                    id.replace("step_", "")
                    .replace("_plus_", "+")
                )
                self.make_step(translate_direction(direction))
            case "restart":
                self.on_mount()
            case "quit":
                self.exit()

    def on_key(self, event: Key) -> None:
        """Обработка клавиатуры."""
        if getattr(self, "waiting_for_exit", False):
            self.exit()
            return

        if event.key == "space":
            self.make_step()
        elif event.key in {
            "left", "up", "down", "right",
            "shift+up", "shift+down",
        }:
            self.make_step(translate_direction(event.key))
        elif event.key.lower() in {"r", "к"}:
            self.on_mount()
        elif event.key.lower() in {"q", "й"}:
            self.exit()


if __name__ == "__main__":
    PuzzleApp().run()
