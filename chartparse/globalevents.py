"""For representing the data related to lyrics, sections, and more.

You will rarely need to create any of this module's objects manually; please instead create a
:class:`~chartparse.chart.Chart` and inspect its attributes via that object.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

import datetime
import re
from collections.abc import Callable, Iterable, Sequence
from typing import ClassVar, Optional, Pattern, Type, TypeVar

from chartparse.event import Event
from chartparse.exceptions import RegexNotMatchError
from chartparse.track import EventTrack, HasSectionNameMixin
from chartparse.util import DictPropertiesEqMixin, DictReprTruncatedSequencesMixin

GlobalEventsTrackT = TypeVar("GlobalEventsTrackT", bound="GlobalEventsTrack")


class GlobalEventsTrack(
    EventTrack, HasSectionNameMixin, DictPropertiesEqMixin, DictReprTruncatedSequencesMixin
):
    """A :class:`~chartparse.chart.Chart`'s :class:`~chartparse.globalevents.GlobalEvent`\\ s."""

    text_events: Sequence[TextEvent]
    """A ``GlobalEventTrack``'s ``TextEvent``\\ s."""

    section_events: Sequence[SectionEvent]
    """A ``GlobalEventTrack``'s ``SectionEvent``\\ s."""

    lyric_events: Sequence[LyricEvent]
    """A ``GlobalEventTrack``'s ``LyricEvent``\\ s."""

    section_name = "Events"

    def __init__(
        self,
        text_events: Sequence[TextEvent],
        section_events: Sequence[SectionEvent],
        lyric_events: Sequence[LyricEvent],
    ) -> None:
        """Instantiates all instance attributes."""

        self.text_events = text_events
        self.section_events = section_events
        self.lyric_events = lyric_events

    @classmethod
    def from_chart_lines(
        cls: Type[GlobalEventsTrackT], iterator_getter: Callable[[], Iterable[str]]
    ) -> GlobalEventsTrackT:
        """Initializes instance attributes by parsing an iterable of strings.

        Args:
            iterator_getter: The iterable of strings returned by this is most likely from a
                Moonscraper ``.chart``. Must be a function so the strings can be iterated over
                multiple times, if necessary.

        Returns:
            A ``GlobalEventsTrack`` parsed from the strings returned by ``iterator_getter``.
        """

        text_events = cls._parse_events_from_chart_lines(
            iterator_getter(), TextEvent.from_chart_line
        )
        section_events = cls._parse_events_from_chart_lines(
            iterator_getter(), SectionEvent.from_chart_line
        )
        lyric_events = cls._parse_events_from_chart_lines(
            iterator_getter(), LyricEvent.from_chart_line
        )
        return cls(text_events, section_events, lyric_events)


GlobalEventT = TypeVar("GlobalEventT", bound="GlobalEvent")


class GlobalEvent(Event):
    """An event in a :class:`~chartparse.globalevents.GlobalEventsTrack`.

    This is typically used only as a base class for more specialized subclasses. It implements an
    attractive ``__str__`` representation and supplies a regular expression template for subclasses
    to fill in.

    Subclasses should define ``_regex_prog`` and can be instantiated with their ``from_chart_line``
    method.
    """

    value: str
    """The data that this event stores."""

    _regex: ClassVar[str]
    _regex_prog: ClassVar[Pattern[str]]

    # Match 1: Tick
    # Match 2: Event value (to be added by subclass via template hole)
    _regex_template: ClassVar[str] = r"^\s*?(\d+?) = E \"{}\"\s*?$"

    def __init__(
        self, tick: int, value: str, timestamp: Optional[datetime.timedelta] = None
    ) -> None:
        super().__init__(tick, timestamp=timestamp)
        self.value = value

    @classmethod
    def from_chart_line(cls: Type[GlobalEventT], line: str) -> GlobalEventT:
        """Attempt to obtain an instance of this object from a string.

        Args:
            line: Most likely a line from a Moonscraper ``.chart``.

        Returns:
            An an instance of this object parsed from ``line``.

        Raises:
            RegexNotMatchError: If the mixed-into class' ``_regex`` does not match ``line``.
        """

        m = cls._regex_prog.match(line)
        if not m:
            raise RegexNotMatchError(cls._regex, line)
        tick, value = int(m.group(1)), m.group(2)
        return cls(tick, value)

    def __str__(self) -> str:  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f': "{self.value}"')
        return "".join(to_join)


class TextEvent(GlobalEvent):
    """A :class:`~chartparse.globalevents.GlobalEvent` that stores freeform text event data."""

    _regex = GlobalEvent._regex_template.format("([^ ]*?)")
    _regex_prog = re.compile(_regex)


class SectionEvent(GlobalEvent):
    """A :class:`~chartparse.globalevents.GlobalEvent` that signifies a new section.

    The event's ``value`` attribute contains the section's name.
    """

    _regex = GlobalEvent._regex_template.format("section (.*?)")
    _regex_prog = re.compile(_regex)


class LyricEvent(GlobalEvent):
    """A :class:`~chartparse.globalevents.GlobalEvent` that signifies a new section.

    The event's ``value`` attribute contains the lyric's text, typically a single syllable's worth.
    """

    _regex = GlobalEvent._regex_template.format("lyric (.*?)")
    _regex_prog = re.compile(_regex)
