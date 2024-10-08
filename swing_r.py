import math
from typing import Annotated
from midi_processor import MidiRepresentation, process_and_save_midi
from midi_processor.utils import create_argparse_from_function


def from_swing(beat_count: float, mult: float) -> float:
    """Return the non-swing variant of the beat count.

    """
    beat_count = beat_count * mult
    beat_decimal = beat_count % 1
    beat_whole_num = math.floor(beat_count)
    if beat_decimal <= 0.667:
        new_beat_decimal = beat_decimal * (3 / 4)
    else:
        new_beat_decimal = (3 * beat_decimal - 1) / 2
    new_beat = beat_whole_num + new_beat_decimal
    return new_beat / mult


def from_swing_duration(beat: float, duration: float, mult: float) -> float:
    # run the swing algorithm on the finish time
    finish_time = beat + duration
    finish_time_swing = from_swing(finish_time, mult)  # this is a monotonic transformation
    start_time_swing = from_swing(beat, mult)
    # assert finish_time_swing - start_time_swing >= 0.0
    return finish_time_swing - start_time_swing


def swing_midi(midi_representation: MidiRepresentation, mult: float) -> None:
    for track in midi_representation.tracks:
        for i in range(len(track.notes)):
            track.notes[i].beat, track.notes[i].duration = (from_swing(track.notes[i].beat, mult),
                                                            from_swing_duration(track.notes[i].beat,
                                                                                track.notes[i].duration, mult))


multiplicative_factor_str = """Adjusts what's considered a beat. 
When set to 1, one beat is considered one beat.
When set to 2, beats are half as long. Same effect as setting the time sig denominator to 8.
When set to n, beats are 1/n as long for the purposes of swinging.
Decimal values are acceptable.
Defaults to 1."""


def run(source: Annotated[str, "Path to MIDI file to modify"],
        destination: Annotated[str, "Path to output MIDI file"],
        mult: Annotated[float, multiplicative_factor_str] = 1) -> None:
    """Reverses a swing midi. This module is the inverse of swing. We assume that the midi's time sig
    denominator is 4."""
    process_and_save_midi(source, destination, lambda sw: swing_midi(sw, mult))


if __name__ == '__main__':
    create_argparse_from_function(run)
