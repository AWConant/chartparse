"""For abstract data structures.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Union, overload

from chartparse.hints import ComparableT, T


class ImmutableList(Sequence[T]):
    """A ``list`` equivalent that cannot be mutated."""

    _seq: Sequence[T]

    def __init__(self, xs: Iterable[T]):
        if isinstance(xs, Sequence):
            self._seq = xs
        else:
            self._seq = list(xs)

    @overload
    def __getitem__(self, index: int) -> T:
        ...  # pragma: no cover

    @overload
    def __getitem__(self, index: slice) -> Sequence[T]:
        ...  # pragma: no cover

    def __getitem__(self, index: Union[int, slice]) -> Union[T, Sequence[T]]:
        return self._seq[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self._seq)

    def __repr__(self) -> str:
        return repr(self._seq)  # pragma: no cover

    def __len__(self) -> int:
        return len(self._seq)

    def __contains__(self, obj: object) -> bool:
        return obj in self._seq

    def __reversed__(self) -> Iterator[T]:
        return reversed(self._seq)

    def __eq__(self, other: object) -> bool:
        if type(other) is list:
            return self._seq == other
        elif isinstance(other, ImmutableList):
            return self._seq == other._seq
        return NotImplemented


class ImmutableSortedList(ImmutableList[T]):
    """A ``list`` equivalent that cannot be mutated and is sorted during initialization."""

    @overload
    def __init__(self, xs: Iterable[ComparableT]) -> None:
        ...  # pragma: no cover

    @overload
    def __init__(self, xs: Iterable[T], key: Callable[[T], ComparableT]) -> None:
        ...  # pragma: no cover

    def __init__(self, xs, key=None) -> None:
        if key is None:
            super().__init__(sorted(xs))
        elif key is not None:
            super().__init__(sorted(xs, key=key))
        else:  # pragma: no cover
            raise TypeError
