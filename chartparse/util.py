from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import Enum
from typing import Any, Generator, TypeVar

from chartparse.hints import T


# TODO: Move to enums.py.
class AllValuesGettableEnum(Enum):
    """A wrapper for ``Enum`` that adds a method for returning all enum values."""

    # TODO: Return an ImmutableList instead. This is an abuse of tuples.
    @classmethod
    def all_values(cls) -> tuple[Any, ...]:
        """Returns a tuple containing all Enum values.

        Returns:
            A tuple containing all Enum values.
        """
        return tuple(c.value for c in cls)


class DictPropertiesEqMixin(object):
    """A mixin that implements ``__eq__`` via ``__dict__().__eq__``."""

    def __eq__(self, other: object) -> bool:
        if not issubclass(other.__class__, DictPropertiesEqMixin):
            return NotImplemented
        return self.__dict__ == other.__dict__


class DictReprMixin(object):
    """A mixin that implements ``__repr__`` by dumping ``__dict__()``."""

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({self.__dict__})"


# TODO: Move this to chart.py and make it private.
def iterate_from_second_elem(xs: Sequence[T]) -> Iterator[T]:
    """Given an iterable xs, return an iterator that skips xs[0].

    Args:
        xs: Any non-exhausted iterable.

    Returns:
        A iterator that iterates over xs, ignoring the first element.
    """
    it = iter(xs)
    next(it)
    yield from it
