import collections
import re

from chartparse.enums import Note
from chartparse.event import SustainedEvent
from chartparse.exceptions import RegexFatalNotMatchError
from chartparse.track import EventTrack
from chartparse.util import DictPropertiesEqMixin, DictReprMixin


class InstrumentTrack(EventTrack, DictPropertiesEqMixin):
    _min_note_instrument_track_index = 0
    _max_note_instrument_track_index = 4
    _open_instrument_track_index = 7
    _forced_instrument_track_index = 5
    _tap_instrument_track_index = 6

    def __init__(self, instrument, difficulty, iterator_getter):
        self.instrument = instrument
        self.difficulty = difficulty
        self.note_events = self._parse_note_events_from_iterable(iterator_getter())
        self.star_power_events = self._parse_events_from_iterable(
            iterator_getter(), StarPowerEvent.from_chart_line
        )
        self._populate_star_power_data()

    def __str__(self):  # pragma: no cover
        return (
            f"Instrument: {self.instrument}\n"
            f"Difficulty: {self.difficulty}\n"
            f"Note count: {len(self.note_events)}\n"
            f"Star power phrase count: {len(self.star_power_events)}"
        )

    @staticmethod
    def _parse_note_events_from_iterable(iterable):
        tick_to_note_array = collections.defaultdict(lambda: bytearray(5))
        tick_to_sustain_list = collections.defaultdict(lambda: [None] * 5)
        tick_to_is_tap = collections.defaultdict(bool)
        tick_to_is_forced = collections.defaultdict(bool)
        for line in iterable:
            m = NoteEvent._regex_prog.match(line)
            if not m:
                continue
            tick, note_index, sustain = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if (
                InstrumentTrack._min_note_instrument_track_index
                <= note_index
                <= InstrumentTrack._max_note_instrument_track_index
            ):
                tick_to_note_array[tick][note_index] = 1
                tick_to_sustain_list[tick][note_index] = sustain
            elif note_index == InstrumentTrack._open_instrument_track_index:
                # Because `tick_to_note_array` is a defaultdict, simply accessing it at `tick` is
                # sufficient to conjure a bytearray representing an open note.
                tick_to_note_array[tick]
                tick_to_sustain_list[tick]
            elif note_index == InstrumentTrack._tap_instrument_track_index:
                tick_to_is_tap[tick] = True
            elif note_index == InstrumentTrack._forced_instrument_track_index:
                tick_to_is_forced[tick] = True
            else:  # pragma: no cover
                # TODO: Log unhandled instrument track note index.
                pass

        events = []
        for tick in tick_to_note_array.keys():
            note = Note(tick_to_note_array[tick])
            event = NoteEvent(
                tick,
                note,
                sustain=tick_to_sustain_list[tick],
                is_forced=tick_to_is_forced[tick],
                is_tap=tick_to_is_tap[tick],
            )
            events.append(event)
        events.sort(key=lambda e: e.tick)

        return events

    def _populate_star_power_data(self):
        num_notes = len(self.note_events)

        note_idx_to_star_power_idx = dict()
        note_idx = 0
        for star_power_idx, star_power_event in enumerate(self.star_power_events):
            start_tick = star_power_event.tick
            end_tick = start_tick + star_power_event.sustain

            # Seek until the first note after this star power phrase.
            while note_idx < num_notes and self.note_events[note_idx].tick < end_tick:
                note = self.note_events[note_idx]
                if start_tick <= note.tick:
                    note_idx_to_star_power_idx[note_idx] = star_power_idx
                note_idx += 1

        for note_idx, note_event in enumerate(self.note_events):
            current_star_power_idx = note_idx_to_star_power_idx.get(note_idx, None)
            if current_star_power_idx is None:
                continue
            next_star_power_idx = note_idx_to_star_power_idx.get(note_idx + 1, None)
            current_note_is_end_of_phrase = current_star_power_idx != next_star_power_idx
            note_event.star_power_data = NoteEvent.StarPowerData(
                current_star_power_idx, current_note_is_end_of_phrase
            )


class _SpecialEvent(SustainedEvent):
    # Match 1: Tick
    # Match 2: Sustain (ticks)
    _regex_template = r"^\s*?(\d+?) = S {} (\d+?)\s*?$"

    def __init__(self, tick, sustain, timestamp=None):
        super().__init__(tick, sustain, timestamp=timestamp)

    @classmethod
    def from_chart_line(cls, line):
        if not hasattr(cls, "_regex_prog"):
            raise NotImplementedError(
                f"{cls.__name__} does not have a _regex_prog value. Perhaps you are trying to "
                "instantiate a {cls.__bases__[0].__name__} value, rather than one of its "
                "implementing subclasses?"
            )

        m = cls._regex_prog.match(line)
        if not m:
            raise RegexFatalNotMatchError(cls._regex, line)
        tick, sustain = int(m.group(1)), int(m.group(2))
        return cls(tick, sustain)


class StarPowerEvent(_SpecialEvent):
    _regex = _SpecialEvent._regex_template.format(r"2")
    _regex_prog = re.compile(_regex)


# TODO: Support S 0 ## and S 1 ## (GH1/2 Co-op)


# TODO: Support S 64 ## (Rock Band drum fills)


class NoteEvent(SustainedEvent):
    # This regex matches a single "N" line within a instrument track section,
    # but this class should be used to represent all of the notes at a
    # particular tick. This means that you might need to consolidate multiple
    # "N" lines into a single NoteEvent, e.g. for chords.
    # Match 1: Tick
    # Match 2: Note index
    # Match 3: Sustain (ticks)
    _regex = r"^\s*?(\d+?) = N ([0-7]) (\d+?)\s*?$"
    _regex_prog = re.compile(_regex)

    class StarPowerData(DictPropertiesEqMixin, DictReprMixin):
        def __init__(self, event_idx, is_end_of_phrase):
            self.event_idx = event_idx
            self.is_end_of_phrase = is_end_of_phrase

    def __init__(
        self,
        tick,
        note,
        timestamp=None,
        sustain=0,
        is_forced=False,
        is_tap=False,
        star_power_data=None,
    ):
        self._validate_sustain(sustain, note)
        refined_sustain = self._refine_sustain(sustain)
        super().__init__(tick, refined_sustain, timestamp=timestamp)
        self.note = note
        self.is_forced = is_forced
        self.is_tap = is_tap
        self.star_power_data = star_power_data

    @staticmethod
    def _validate_sustain(sustain, note):
        if isinstance(sustain, int):
            NoteEvent._validate_int_sustain(sustain)
        elif isinstance(sustain, list):
            NoteEvent._validate_list_sustain(sustain, note)
        else:
            raise TypeError(f"sustain {sustain} must be type list, or int.")

    @staticmethod
    def _validate_int_sustain(sustain):
        if sustain < 0:
            raise ValueError(f"int sustain {sustain} must be positive.")

    @staticmethod
    def _validate_list_sustain(sustain, note):
        if len(sustain) != len(note.value):
            raise ValueError(f"list sustain {sustain} must have length {len(note.value)}")
        for note_lane_value, sustain_lane_value in zip(note.value, sustain):
            lane_is_active = note_lane_value == 1
            sustain_is_set = sustain_lane_value is not None
            if lane_is_active != sustain_is_set:
                raise ValueError(
                    f"list sustain {sustain} must have "
                    "values for exactly the active note lanes."
                )

    @staticmethod
    def _refine_sustain(sustain):
        if isinstance(sustain, list):
            if all(d is None for d in sustain):
                return 0
            first_non_none_sustain = next(d for d in sustain if d is not None)
            if all(d is None or d == first_non_none_sustain for d in sustain):
                return first_non_none_sustain
        return sustain

    def __str__(self):  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f": {self.note}")

        if self.star_power_data:
            to_join.append("*")

        flags = []
        if self.is_forced:
            flags.append("F")
        if self.is_tap:
            flags.append("T")
        if flags:
            to_join.extend([" [flags=", "".join(flags), "]"])

        return "".join(to_join)