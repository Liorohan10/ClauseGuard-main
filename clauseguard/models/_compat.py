from enum import Enum

try:
    from enum import StrEnum as _StrEnum
except ImportError:  # Python < 3.11
    class _StrEnum(str, Enum):
        pass


StrEnum = _StrEnum
