"""For functionality relating to tick arithmetic.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from enum import Enum


class NoteDuration(Enum):
    """The note durations supported by Moonscraper.

    The enum values are the number of that type of note in a number of ticks equal to
    :attr:`~chartparse.metadata.Metadata.resolution`.
    """

    WHOLE = 2 ** (-2)
    HALF = 2 ** (-1)
    QUARTER = 2**0
    EIGHTH = 2**1
    SIXTEENTH = 2**2
    THIRTY_SECOND = 2**3
    SIXTY_FOURTH = 2**4
    HUNDRED_TWENTY_EIGHTH = 2**5
    TWO_HUNDRED_FIFTH_SIXTH = 2**6
    FIVE_HUNDRED_TWELFTH = 2**7

    THIRD = (HALF + QUARTER) / 2
    SIXTH = (QUARTER + EIGHTH) / 2
    TWELFTH = (EIGHTH + SIXTEENTH) / 2
    TWENTY_FOURTH = (SIXTEENTH + THIRTY_SECOND) / 2
    FOURTY_EIGHTH = (THIRTY_SECOND + SIXTY_FOURTH) / 2
    NINETY_SIXTH = (SIXTY_FOURTH + HUNDRED_TWENTY_EIGHTH) / 2
    HUNDRED_NINETY_SECOND = (HUNDRED_TWENTY_EIGHTH + TWO_HUNDRED_FIFTH_SIXTH) / 2
    THREE_HUNDRED_EIGHTY_FOURTH = (TWO_HUNDRED_FIFTH_SIXTH + FIVE_HUNDRED_TWELFTH) / 2
    SEVEN_HUNDRED_SIXTY_EIGHTH = (FIVE_HUNDRED_TWELFTH + FIVE_HUNDRED_TWELFTH * 2) / 2

    # Aliases

    HALF_TRIPLET = THIRD
    QUARTER_TRIPLET = SIXTH
    EIGHTH_TRIPLET = TWELFTH
    SIXTEENTH_TRIPLET = TWENTY_FOURTH
    THIRTY_SECOND_TRIPLET = FOURTY_EIGHTH
    SIXTY_FOURTH_TRIPLET = NINETY_SIXTH
    HUNDRED_TWENTY_EIGHTH_TRIPLET = HUNDRED_NINETY_SECOND
    TWO_HUNDRED_FIFTH_SIXTH_TRIPLET = THREE_HUNDRED_EIGHTY_FOURTH
    FIVE_HUNDRED_TWELFTH_TRIPLET = SEVEN_HUNDRED_SIXTY_EIGHTH


def calculate_ticks_between_notes(resolution: int, note_duration: NoteDuration) -> int:
    """Returns the number of ticks between two notes of a particular note value.

    It is unknown whether Moonscraper rounds or truncates when ``resolution`` does not divide
    evenly. The vast majority of charts have a ``resolution`` of ``192``, so this is mostly a
    nonissue.

    Args:
        resolution: The number of ticks in a quarter note.
        note_duration: The number of notes in a quarter note.

    Returns: The number of ticks between two notes of a particular note value.

    """
    return round(resolution / note_duration.value)
