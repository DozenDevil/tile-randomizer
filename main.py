from dataclasses import dataclass, field
from random import choice, choices
from typing import Union, Iterable

@dataclass(frozen=True)
class ChoiceSet:
    title: str
    data: Union[list, tuple, dict] = field(repr=False)
    eps: float = 1e-9

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

    print(directions.choose(exclude=["Вперёд", "Вправо", "Влево", "Вниз", "Вверх"]))
