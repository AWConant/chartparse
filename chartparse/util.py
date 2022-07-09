"""For various utilities useful throughout ``chartparse``.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

import enum
from collections.abc import Sequence

from chartparse.datastructures import ImmutableList
from chartparse.hints import T


class DictPropertiesEqMixin(object):
    """A mixin that implements ``__eq__`` via ``__dict__().__eq__``."""

    def __eq__(self, other: object) -> bool:
        if not issubclass(other.__class__, DictPropertiesEqMixin):
            return NotImplemented
        return self.__dict__ == other.__dict__


class DictReprMixin(object):
    """A mixin implementing ``__repr__`` by dumping ``__dict__()``."""

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({str(self.__dict__)[1:-1]})"


class DictReprTruncatedSequencesMixin(object):
    """A mixin implementing ``__repr__`` by dumping ``__dict__()`` with truncated sequences."""

    def __repr__(self) -> str:  # pragma: no cover
        items = []
        for k, v in self.__dict__.items():
            item = f"'{k}': "
            if isinstance(v, Sequence) and len(v) > 1:
                item += f"[{v[0]}, ... {len(v)-1} more elements]"
            else:
                item += f"{v}"
            items.append(item)

        item_string = ", ".join(items)
        return f"{type(self).__name__}({item_string})"


class AllValuesGettableEnum(enum.Enum):
    """A wrapper for ``Enum`` that adds a method for returning all enum values."""

    @classmethod
    def all_values(cls) -> ImmutableList[T]:
        """Returns all Enum values.

        Returns:
            An :class:`~chartparse.datastructures.ImmutableList` containing all Enum values.
        """
        return ImmutableList([c.value for c in cls])
