import pytest
import re
import unittest.mock

import chartparse.tick
from chartparse.exceptions import RegexNotMatchError
from chartparse.instrument import (
    InstrumentTrack,
    StarPowerEvent,
    NoteEvent,
    StarPowerData,
    HOPOState,
    SpecialEvent,
    Note,
    NoteTrackIndex,
)
from chartparse.tick import NoteDuration

from tests.conftest import (
    generate_valid_note_line_fn,
    generate_valid_star_power_line_fn,
)


class TestInstrumentTrack(object):
    def test_init(self, mocker, basic_instrument_track):
        mock_populate_star_power_data = mocker.patch.object(
            InstrumentTrack, "_populate_star_power_data"
        )
        _ = InstrumentTrack(
            pytest.default_instrument,
            pytest.default_difficulty,
            pytest.default_note_event_list,
            pytest.default_star_power_event_list,
        )
        assert basic_instrument_track.instrument == pytest.default_instrument
        assert basic_instrument_track.difficulty == pytest.default_difficulty
        assert basic_instrument_track.note_events == pytest.default_note_event_list
        assert basic_instrument_track.star_power_events == pytest.default_star_power_event_list
        assert basic_instrument_track.section_name == pytest.default_section_name
        mock_populate_star_power_data.assert_called_once()

    def test_from_chart_lines(self, mocker, placeholder_string_iterator_getter):
        mock_parse_events = mocker.patch(
            "chartparse.instrument.InstrumentTrack._parse_events_from_chart_lines",
            return_value=pytest.default_star_power_event_list,
        )
        mock_parse_note_events = mocker.patch(
            "chartparse.instrument.InstrumentTrack._parse_note_events_from_chart_lines",
            return_value=pytest.default_note_event_list,
        )
        init_spy = mocker.spy(InstrumentTrack, "__init__")
        _ = InstrumentTrack.from_chart_lines(
            pytest.default_instrument,
            pytest.default_difficulty,
            placeholder_string_iterator_getter,
        )
        mock_parse_events.assert_called_once_with(
            placeholder_string_iterator_getter(), StarPowerEvent.from_chart_line
        )
        mock_parse_note_events.assert_called_once_with(placeholder_string_iterator_getter())
        init_spy.assert_called_once_with(
            unittest.mock.ANY,
            pytest.default_instrument,
            pytest.default_difficulty,
            pytest.default_note_event_list,
            pytest.default_star_power_event_list,
        )

    @pytest.mark.parametrize(
        "lines, want_note_events, want_star_power_events",
        [
            pytest.param([pytest.invalid_chart_line], [], [], id="skip_invalid_line"),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.OPEN.value)],
                [NoteEvent(0, Note.OPEN)],
                [],
                id="open_note",
            ),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.G.value)],
                [NoteEvent(0, Note.G)],
                [],
                id="green_note",
            ),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.R.value)],
                [NoteEvent(0, Note.R)],
                [],
                id="red_note",
            ),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.Y.value)],
                [NoteEvent(0, Note.Y)],
                [],
                id="yellow_note",
            ),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.B.value)],
                [NoteEvent(0, Note.B)],
                [],
                id="blue_note",
            ),
            pytest.param(
                [generate_valid_note_line_fn(0, NoteTrackIndex.O.value)],
                [NoteEvent(0, Note.O)],
                [],
                id="orange_note",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value),
                    generate_valid_note_line_fn(0, NoteTrackIndex.TAP.value),
                ],
                [NoteEvent(0, Note.G, is_tap=True)],
                [],
                id="tap_green_note",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value),
                    generate_valid_note_line_fn(0, NoteTrackIndex.FORCED.value),
                ],
                [NoteEvent(0, Note.G, is_forced=True)],
                [],
                id="forced_green_note",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value, sustain=100),
                ],
                [NoteEvent(0, Note.G, sustain=100)],
                [],
                id="green_with_sustain",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value),
                    generate_valid_note_line_fn(0, NoteTrackIndex.R.value),
                ],
                [NoteEvent(0, Note.GR)],
                [],
                id="chord",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value, sustain=100),
                    generate_valid_note_line_fn(0, NoteTrackIndex.R.value),
                ],
                [NoteEvent(0, Note.GR, sustain=[100, 0, None, None, None])],
                [],
                id="nonuniform_sustains",
            ),
            pytest.param(
                [generate_valid_star_power_line_fn(0, 100)],
                [],
                [StarPowerEvent(0, 100)],
                id="single_star_power_phrase",
            ),
            pytest.param(
                [
                    generate_valid_note_line_fn(0, NoteTrackIndex.G.value, sustain=100),
                    generate_valid_star_power_line_fn(0, 100),
                    generate_valid_note_line_fn(2000, NoteTrackIndex.R.value, sustain=50),
                    generate_valid_note_line_fn(2075, NoteTrackIndex.Y.value),
                    generate_valid_note_line_fn(2075, NoteTrackIndex.B.value),
                    generate_valid_star_power_line_fn(2000, 80),
                    generate_valid_note_line_fn(2100, NoteTrackIndex.O.value),
                    generate_valid_note_line_fn(2100, NoteTrackIndex.FORCED.value),
                    generate_valid_note_line_fn(2200, NoteTrackIndex.B.value),
                    generate_valid_note_line_fn(2200, NoteTrackIndex.TAP.value),
                    generate_valid_note_line_fn(2300, NoteTrackIndex.OPEN.value),
                ],
                [
                    NoteEvent(
                        0,
                        Note.G,
                        sustain=100,
                        star_power_data=StarPowerData(0, True),
                    ),
                    NoteEvent(
                        2000,
                        Note.R,
                        sustain=50,
                        star_power_data=StarPowerData(1, False),
                    ),
                    NoteEvent(
                        2075,
                        Note.YB,
                        star_power_data=StarPowerData(1, True),
                    ),
                    NoteEvent(2100, Note.O, is_forced=True),
                    NoteEvent(2200, Note.B, is_tap=True),
                    NoteEvent(2300, Note.OPEN),
                ],
                [StarPowerEvent(0, 100), StarPowerEvent(2000, 80)],
                id="everything_together",
            ),
        ],
    )
    def test_from_chart_lines_integration(self, lines, want_note_events, want_star_power_events):
        lines_iterator_getter = lambda: iter(lines)
        instrument_track = InstrumentTrack.from_chart_lines(
            pytest.default_instrument, pytest.default_difficulty, lines_iterator_getter
        )
        assert instrument_track.instrument == pytest.default_instrument
        assert instrument_track.difficulty == pytest.default_difficulty
        assert instrument_track.note_events == want_note_events
        assert instrument_track.star_power_events == want_star_power_events

    @pytest.mark.parametrize(
        "note_events,star_power_events,want_note_events",
        [
            pytest.param(
                [
                    NoteEvent(0, Note.G, sustain=100),
                    NoteEvent(2000, Note.R, sustain=50),
                    NoteEvent(2075, Note.YB),
                ],
                [
                    StarPowerEvent(0, 100),
                    StarPowerEvent(2000, 80),
                ],
                [
                    NoteEvent(
                        0,
                        Note.G,
                        sustain=100,
                        star_power_data=StarPowerData(0, True),
                    ),
                    NoteEvent(
                        2000,
                        Note.R,
                        sustain=50,
                        star_power_data=StarPowerData(1, False),
                    ),
                    NoteEvent(
                        2075,
                        Note.YB,
                        star_power_data=StarPowerData(1, True),
                    ),
                ],
                id="basic",
            ),
        ],
    )
    def test_populate_star_power_data(
        self, bare_instrument_track, note_events, star_power_events, want_note_events
    ):
        bare_instrument_track.note_events = note_events
        bare_instrument_track.star_power_events = star_power_events
        bare_instrument_track._populate_star_power_data()
        assert bare_instrument_track.note_events == want_note_events


class TestNoteEvent(object):
    def test_init(self, note_event_with_all_optionals_set):
        assert note_event_with_all_optionals_set.note == pytest.default_note
        assert note_event_with_all_optionals_set.sustain == pytest.default_sustain
        assert note_event_with_all_optionals_set._is_forced is True
        assert note_event_with_all_optionals_set._is_tap is True

    def test_validate_sustain(self):
        NoteEvent._validate_sustain(0, Note.G)
        NoteEvent._validate_sustain([100, None, None, None, None], Note.G)
        with pytest.raises(TypeError):
            NoteEvent._validate_sustain((100, None, None, None, None), Note.G)

    def test_validate_int_sustain_negative(self):
        with pytest.raises(ValueError):
            NoteEvent._validate_int_sustain(-1)

    @pytest.mark.parametrize(
        "sustain, note",
        [
            pytest.param(
                [None, None, None, None], pytest.default_note, id="incorrect_length_list"
            ),
            pytest.param([100, 100, None, None, None], Note.G, id="mismatched_set_lanes"),
        ],
    )
    def test_validate_list_sustain_raises(self, sustain, note):
        with pytest.raises(ValueError):
            NoteEvent._validate_list_sustain(sustain, note)

    @pytest.mark.parametrize(
        "sustain, want",
        [
            pytest.param([None, None, None, None, None], 0, id="all_none"),
            pytest.param([100, None, None, 100, None], 100, id="all_the_same"),
            pytest.param(100, 100, id="int_pass_through"),
            pytest.param(
                [100, 0, None, None, None], [100, 0, None, None, None], id="list_pass_through"
            ),
        ],
    )
    def test_refine_sustain(self, sustain, want):
        assert NoteEvent._refine_sustain(sustain) == want

    @pytest.mark.parametrize(
        "current,previous,want",
        [
            pytest.param(
                NoteEvent(0, Note.G, is_tap=True, is_forced=True),
                None,
                HOPOState.TAP,
                id="tap_notes_are_taps",
            ),
            pytest.param(
                NoteEvent(0, Note.G),
                None,
                HOPOState.STRUM,
                id="first_note_is_strum",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.SIXTEENTH,
                    ),
                    Note.R,
                ),
                NoteEvent(0, Note.G),
                HOPOState.HOPO,
                id="16th_notes_are_hopos",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.R,
                ),
                NoteEvent(0, Note.G),
                HOPOState.HOPO,
                id="12th_notes_are_hopos",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.EIGHTH,
                    ),
                    Note.R,
                ),
                NoteEvent(0, Note.G),
                HOPOState.STRUM,
                id="8th_notes_are_strums",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.SIXTEENTH,
                    ),
                    Note.G,
                ),
                NoteEvent(0, Note.G),
                HOPOState.STRUM,
                id="consecutive_16th_notes_are_strums",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.G,
                ),
                NoteEvent(0, Note.G),
                HOPOState.STRUM,
                id="consecutive_12th_notes_are_strums",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.EIGHTH,
                    ),
                    Note.G,
                ),
                NoteEvent(0, Note.G),
                HOPOState.STRUM,
                id="consecutive_8th_notes_are_strums",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.G,
                ),
                NoteEvent(0, Note.RY),
                HOPOState.HOPO,
                id="pull_off_from_chord_is_hopo",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.RY,
                ),
                NoteEvent(0, Note.G),
                HOPOState.STRUM,
                id="hammer_on_to_chord_is_not_hopo",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.OPEN,
                ),
                NoteEvent(0, Note.G),
                HOPOState.HOPO,
                id="hammer_on_to_open_is_hopo",
            ),
            pytest.param(
                NoteEvent(
                    chartparse.tick.calculate_ticks_between_notes(
                        pytest.default_resolution,
                        NoteDuration.TWELFTH,
                    ),
                    Note.G,
                ),
                NoteEvent(0, Note.OPEN),
                HOPOState.HOPO,
                id="pull_off_to_open_is_hopo",
            ),
        ],
    )
    def test_compute_hopo_state(self, current, previous, want):
        state = NoteEvent._compute_hopo_state(pytest.default_resolution, current, previous)
        assert state == want

    @pytest.mark.parametrize(
        "sustain,want",
        [
            pytest.param(100, 100),
            pytest.param([50, 100, None, 200, None], 200),
        ],
    )
    def test_longest_sustain(self, bare_note_event, sustain, want):
        bare_note_event.sustain = sustain
        assert bare_note_event.longest_sustain == want

    def test_longest_sustain_raises(self, bare_note_event):
        bare_note_event.sustain = [None, None, None, None, None]
        with pytest.raises(ValueError):
            _ = bare_note_event.longest_sustain


class TestSpecialEvent(object):
    test_regex = r"^T (\d+?) V (.*?)$"

    def teardown_method(self):
        try:
            del SpecialEvent._regex
            del SpecialEvent._regex_prog
        except AttributeError:
            pass

    def test_init(self, star_power_event):
        assert star_power_event.sustain == pytest.default_sustain

    def test_from_chart_line(self, bare_special_event):
        SpecialEvent._regex = self.test_regex
        SpecialEvent._regex_prog = re.compile(SpecialEvent._regex)

        bare_special_event.tick = pytest.default_tick
        bare_special_event.timestamp = pytest.default_timestamp
        bare_special_event.sustain = str(pytest.default_sustain)
        line = f"T {pytest.default_tick} V {pytest.default_sustain}"
        e = SpecialEvent.from_chart_line(line)
        assert e.sustain == pytest.default_sustain

    def test_from_chart_line_no_match(self, invalid_chart_line):
        SpecialEvent._regex = self.test_regex
        SpecialEvent._regex_prog = re.compile(SpecialEvent._regex)

        with pytest.raises(RegexNotMatchError):
            _ = SpecialEvent.from_chart_line(invalid_chart_line)


# TODO: Test regex?
class TestStarPowerEvent(object):
    pass
