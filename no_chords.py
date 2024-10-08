import math
from typing import Annotated
from midi_processor import MidiRepresentation, Note, process_and_save_midi
from midi_processor.utils import create_argparse_from_function


def group_by_custom_equals(lst: list[Note]) -> list[list[Note]]:
    groups: list[list[Note]] = []
    for item in lst:
        for group in groups:
            if ci(item, group[0]):
                group.append(item)
                break
        else:  # no break
            groups.append([item])
    return groups


def ci(first: Note, other: Note) -> bool:
    """Equals variant, only sensitive to beat start time and channel."""
    return math.isclose(first.beat, other.beat) and first.channel == other.channel


def no_chords(m: MidiRepresentation) -> None:
    """Remove all but one note from chords.
    Only applies to the same channel and track.
    Keep the highest one.
    """
    for track in m.tracks:
        notes = track.notes
        safe_notes: list[Note] = []
        equals_group = group_by_custom_equals(notes)
        for note_set in equals_group:
            safe_notes.append(max(note_set, key=lambda ns: ns.key))
        track.notes = safe_notes


def run(source: Annotated[str, "Path to MIDI file to modify"],
        destination: Annotated[str, "Path to output MIDI file"]) -> None:
    """Remove all but one note from chords.
    Only applies to the same channel and track.
    Keep the highest one."""
    process_and_save_midi(source, destination, no_chords)


if __name__ == '__main__':
    create_argparse_from_function(run)
