from enum import Enum


class BaseEnum(Enum):

    @classmethod
    def items(cls) -> list:
        return [e for e in cls]


class StatusEnum(str, BaseEnum):
    SUCCESS = 'Success'
    UNSUCCESS = 'Unsuccess'


class StatusApplicationEnum(str, BaseEnum):
    OUT = 'Исходящая'
    IN = 'Входящая'
    FRI = 'Уже друзья'
    NONE = 'Нет ничего'
    REJ = 'Не стали друзьями'
