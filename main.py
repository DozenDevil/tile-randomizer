from dataclasses import dataclass, field
from random import choice, choices
from typing import Union, Iterable
from enum import IntEnum


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

def print_head_text(head_type: str, previous_head_type: str, straight_direction: str, heads: ChoiceSet, useful_trait: ChoiceSet, useless_traits: list[ChoiceSet]):
    head_type_text = "Что-то пошло не так..."
    if head_type == "Правда":
        head_type_text = "правды"
    if head_type == "Ложь":
        head_type_text = "лжи"
    if head_type == "Повтор":
        head_type_text = "повтора"

    is_lying = determine_honesty(head_type, previous_head_type)
    direction_text = flip_direction(straight_direction) if is_lying else straight_direction

    print(f"Голова ({head_type_text}) говорит: \"{direction_text}!\"\n"
          f"Описание:\n"
          f"{useful_trait.get_title()} - {useful_trait.get_option(heads.get_index(head_type))}")

    for trait in useless_traits:
        print(f"{trait.get_title()} - {trait.choose()}")

    print()

if __name__ == '__main__':
    directions = ChoiceSet(
        title="Направление движения",
        data={
            "Вперёд": 0.3,
            "Назад": 0.1,
            "Влево": 0.15,
            "Вправо": 0.15,
            "Вверх": 0.15,
            "Вниз": 0.15}
    )

    heads = ChoiceSet(
        title="Головы",
        data=["Правда", "Ложь", "Повтор"]
    )

    useful_trait = ChoiceSet(
        title="Рога",
        data=["прямые", "закрученные", "короткие"]
    )

    useless_traits = [
        ChoiceSet(
            title="Цвет шерсти",
            data=["коричневый", "белый", "серый", "чёрный"]
        ),
        ChoiceSet(
            title="Цвет глаз",
            data=["жёлтый", "красный", "белый"]
        ),
        ChoiceSet(
            title="Бородка",
            data=["есть", "нет"]
        )
    ]

    length: int = 8
    width: int = 5
    pos = [0, int(width / 2)]

    head = ""

    while True :
        print(f"Координаты: Y = {pos[Axis.Y]}, X = {pos[Axis.X]}")

        if pos[Axis.Y] == length - 1 :
            print("Ты победил!")
            break

        banned_directions = []
        if pos[Axis.Y] - 1 < 0 : banned_directions.append("Назад")
        if pos[Axis.X] - 1 < 0 : banned_directions.append("Влево")
        if pos[Axis.X] + 1 > width - 1 : banned_directions.append("Вправо")

        print("Выберите действие (Enter - продолжить, 0 - пойти вперёд, 1 - заново, 2 - завершить)")
        action = input()

        if action == "0" :
            print(f"Направление: Вперёд")
            pos[Axis.Y] += 1
            continue

        if action == "1" :
            pos = [0, int(width / 2)]
            head = ""
            print("Начинаем сначала...")
            print()
            continue

        if action == "2" :
            print("Завершаем программу...")
            exit()

        direction = directions.choose(banned_directions)
        print(f"Направление: {direction}")

        if direction == "Вперёд" : pos[Axis.Y] += 1
        if direction == "Назад": pos[Axis.Y] -= 1
        if direction == "Влево": pos[Axis.X] -= 1
        if direction == "Вправо": pos[Axis.X] += 1

        last_head = head
        if last_head == "" :
            head = heads.choose(exclude="Повтор")
        else :
            head = heads.choose()
        
        print_head_text(head, last_head, direction, heads, useful_trait, useless_traits)