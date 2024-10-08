import math
from typing import Annotated, Optional
from midi_processor import MidiRepresentation, TempoChange, Note, process_and_save_midi
from midi_processor.utils import create_argparse_from_function


def spb(tempo: float) -> float:
    return 60.0 / tempo


def arg_first(__start: int, __list: list[Note], cur_note: Note) -> int:
    for i in range(__start, len(__list)):
        loop_note = __list[i]
        if all([
            loop_note.key == cur_note.key,
            loop_note.channel == cur_note.channel,
        ]):
            return i
    return -1


def prevent_overlapping_notes(__notes_argument: list[Note]) -> list[Note]:
    """Same pitch, same channel => Ensure no overlaps by
    trimming duration"""
    notes = sorted(__notes_argument, key=lambda s: s.beat)
    new_notes: list[Note] = []

    for i, note in enumerate(notes):
        # if not the last index, we do not need to do anything
        if i < len(notes) - 1:
            next_note_idx = arg_first(i + 1, notes, note)
            if next_note_idx != -1:
                new_notes.append(note.copy(update={
                    "duration": min(note.duration, notes[next_note_idx].beat - note.beat - 0.00001)
                }))
            else:
                new_notes.append(note.copy())
        else:
            new_notes.append(note.copy())

    return new_notes


def augment_note_list(__tempo_change_argument: list[TempoChange], __notes_argument: list[Note]) -> list[Note]:
    """Ensure all beat values are based on a 60BPM."""
    count_from_this_beat = 0.0
    offset_this_many_seconds = 0.0
    tempo_changes = sorted(__tempo_change_argument, key=lambda s: s.beat)
    notes = sorted(__notes_argument, key=lambda s: s.beat)
    j = 0
    export_notes: list[Note] = []
    if not tempo_changes:
        tempo_changes.append(TempoChange(beat=0.0, new_bpm=120))
    tempo_changes.append(TempoChange(beat=math.inf, new_bpm=120))
    previous_bpm = 120.0
    for i, tempo_change in enumerate(tempo_changes):
        #    last tempo change|    # beat_loc
        #   previous_bpm  beat_loc    cur_tempo_change
        while j < len(notes) and notes[j].beat < tempo_change.beat:
            export_notes.append(
                notes[j].copy(update={"beat": offset_this_many_seconds +
                                              (notes[j].beat - count_from_this_beat) *
                                              spb(previous_bpm),
                                            "duration": notes[j].duration * spb(previous_bpm)})
            )
            j += 1
        if j == len(notes):
            break
        beat_of_last_section_ended = 0.0
        if i >= 1:
            beat_of_last_section_ended = tempo_changes[i - 1].beat
        count_from_this_beat = tempo_change.beat
        if i >= 1:
            offset_this_many_seconds += (tempo_change.beat - beat_of_last_section_ended) * spb(
                tempo_changes[i - 1].new_bpm)
        previous_bpm = tempo_change.new_bpm
    return prevent_overlapping_notes(export_notes)


def naive_tempo_change_to_seconds(__tempo_change_argument: list[TempoChange], beat: float) -> float:
    """Return the second the beat plays from the beat."""
    count_from_this_beat = 0.0
    offset_this_many_seconds = 0.0
    tempo_changes = sorted(__tempo_change_argument, key=lambda s: s.beat)
    if not tempo_changes:
        tempo_changes.append(TempoChange(beat=0.0, new_bpm=120))
    tempo_change: Optional[TempoChange] = None
    for i, tempo_change in enumerate(tempo_changes):
        #    last tempo change|    # beat_loc
        #  beat_loc    cur_tempo_change
        if beat < tempo_change.beat:
            break
        beat_of_last_section_ended = 0.0
        if i >= 1:
            beat_of_last_section_ended = tempo_changes[i - 1].beat
        count_from_this_beat = tempo_change.beat
        if i >= 1:
            offset_this_many_seconds += (tempo_change.beat - beat_of_last_section_ended) * spb(
                tempo_changes[i - 1].new_bpm)

    return offset_this_many_seconds + (beat - count_from_this_beat) * spb(tempo_change.new_bpm)


def tempo_integrator(m: MidiRepresentation) -> None:
    """Remove all tempo changes. Forces the tempo to 60.
    Adjust note duration and beat durations to accommodate the removal of tempo."""
    for track in m.tracks:
        track.notes = augment_note_list(m.bpm_changes, track.notes)
    m.bpm_changes = [
        TempoChange(beat=0, new_bpm=60)
    ]


def check_this() -> None:
    tc = [
        TempoChange(beat=0, new_bpm=60),
        TempoChange(beat=1, new_bpm=44),
        TempoChange(beat=2, new_bpm=60),
        TempoChange(beat=3, new_bpm=32),
    ]
    # 0 1 (2->1.5) (3->2.5)
    tl = [naive_tempo_change_to_seconds(tc, 0),
          naive_tempo_change_to_seconds(tc, 1),
          naive_tempo_change_to_seconds(tc, 2),
          naive_tempo_change_to_seconds(tc, 3),
          naive_tempo_change_to_seconds(tc, 4),
          naive_tempo_change_to_seconds(tc, 5),
          ]
    print(tl)


# TEST THIS MODULE
# if __name__ == '__main__':
#     check_this()

def run(source: Annotated[str, "Path to MIDI file to modify"],
        destination: Annotated[str, "Path to output MIDI file"]) -> None:
    """Remove all tempo changes. Forces the tempo to 60.
    Adjust note duration and beat durations to accommodate the removal of tempo.
    """
    process_and_save_midi(source, destination, tempo_integrator)


if __name__ == '__main__':
    create_argparse_from_function(run)
