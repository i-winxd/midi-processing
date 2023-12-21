from __future__ import annotations

from typing import Callable
from collections import Counter
from pydantic import BaseModel
import mido

_MD_FILE_PATH = "midfiles/input.mid"
_MD_OUT_PATH = "midfiles/output.mid"
_DEFAULT_TICKS_PER_BEAT = 96
_DEFAULT_BPM = 120


class Note(BaseModel):
    channel: int  # counts from 0. FL counts from 1.
    note: int  # 60: C5, 61: C#5
    velocity: int  # 0 to 100
    beat: float  # beat count where this plays from the start of the file
    duration: float  # in beats


class Track(BaseModel):
    notes: list[Note]
    track_name: str

    def most_used_channel(self) -> int:
        """Return the most common channel in the notes
        of this track, or -1 if there is none."""
        if len(self.notes) == 0:
            return -1
        channels = [n.channel for n in self.notes]
        most_common, _ = Counter(channels).most_common(1)[0]
        return most_common


class TempoChange(BaseModel):
    beat: float
    new_bpm: float


class MidiEvent(BaseModel):
    note: Note
    event_time: float
    on: bool


class MidiRepresentation(BaseModel):
    """track_names maps track numbers to track names.
    """
    tracks: dict[int, Track]
    channel_instrument_map: dict[int, int]
    bpm_changes: list[TempoChange]

    def get_starting_bpm(self) -> float:
        if len(self.bpm_changes) == 0:
            return _DEFAULT_BPM
        return self.bpm_changes[0].new_bpm


def string_empty_fallback(text: str, fallback: str) -> str:
    return text if text != "" else fallback


def representation_to_midi_file(midi_representation: MidiRepresentation) -> mido.MidiFile:
    """Convert a MidiRepresentation instance to a mido.MidiFile instance that can be
    exported to a new Midi file.
    NOTHING IN midi_representation NEEDS TO BE SORTED
    """
    midi_file = mido.MidiFile()
    ticks_per_beat = _DEFAULT_TICKS_PER_BEAT
    midi_file.ticks_per_beat = ticks_per_beat

    # TEMPO TRACK START
    tempo_track = mido.MidiTrack()
    tempo_track_name_message = mido.MetaMessage('track_name', name="Tempo changes")
    tempo_track.append(tempo_track_name_message)

    accumulated_ticks = 0
    for bpm_change in sorted(midi_representation.bpm_changes, key=lambda s: s.beat):
        tempo_in_microseconds = int(60000000 / bpm_change.new_bpm)
        accumulated_ticks += int(bpm_change.beat * ticks_per_beat)
        tempo_message = mido.MetaMessage('set_tempo', tempo=tempo_in_microseconds, time=accumulated_ticks)
        tempo_track.append(tempo_message)
    midi_file.tracks.append(tempo_track)
    # TEMPO TRACK END

    for track_no, track in midi_representation.tracks.items():
        midi_events: list[MidiEvent] = []
        midi_track = mido.MidiTrack()

        track_name_message = mido.MetaMessage('track_name',
                                              name=string_empty_fallback(track.track_name, f"Unknown Track {track_no}"))
        midi_track.append(track_name_message)

        track_channel = track.most_used_channel()
        if track_channel >= 0:
            track_instrument = midi_representation.channel_instrument_map.get(track_channel, 0)
            if track_instrument >= 0:
                track_channel_message = mido.Message('program_change', channel=track_channel,
                                                     program=track_instrument)
                midi_track.append(track_channel_message)

        for note in track.notes:
            midi_events.append(MidiEvent(note=note, event_time=note.beat, on=True))
            midi_events.append(MidiEvent(note=note, event_time=note.beat + note.duration, on=False))
        midi_events.sort(key=lambda t: t.event_time)

        previous_beat: int = 0
        for event in midi_events:
            beat = event.event_time
            time: int = int(beat * ticks_per_beat)
            delta_time = time - previous_beat
            previous_beat = time
            message = mido.Message('note_on' if event.on else 'note_off', channel=event.note.channel,
                                   note=event.note.note, velocity=event.note.velocity, time=delta_time)
            midi_track.append(message)
        midi_file.tracks.append(midi_track)

    return midi_file


def midi_to_representation(midi_file: mido.MidiFile) -> MidiRepresentation:
    """Create a MidiRepresentation instance from midi_file.
    """
    tracks = {}
    channel_ins_mapping = _get_channel_to_instrument_mapping(midi_file)
    track_names: dict[int, str] = _get_track_names(midi_file)
    for i, track in enumerate(midi_file.tracks):
        notes = []
        accumulated_time = 0
        for msg in track:
            accumulated_time += msg.time

            if msg.type == 'note_on':
                beat = accumulated_time / midi_file.ticks_per_beat
                note = Note(
                    channel=msg.channel,
                    note=msg.note,
                    velocity=msg.velocity,
                    beat=beat,
                    duration=0
                )
                notes.append(note)
            elif msg.type == 'note_off':
                for note in notes[::-1]:
                    if note.note == msg.note and note.duration == 0:
                        beat = -1
                        for j in range(len(notes) - 1, -1, -1):
                            if notes[j].note == msg.note and notes[j].duration == 0 and notes[j].channel == msg.channel:
                                beat = accumulated_time / midi_file.ticks_per_beat
                                duration = beat - notes[j].beat
                                notes[j].duration = max(0, duration)
                                break
                        assert (beat >= 0)
                        duration = beat - note.beat
                        note.duration = max(0, duration)
                        break
        track_name = track_names.get(i, "")
        tracks[i] = Track(notes=notes, track_name=track_name)

    midi_representation = MidiRepresentation(
        tracks=tracks,
        channel_instrument_map=channel_ins_mapping,
        bpm_changes=_get_tempo_changes(midi_file),
    )

    return midi_representation


def _get_tempo_changes(midi: mido.MidiFile) -> list[TempoChange]:
    """Return a list of tempo changes in this midi.
    """
    tempo_changes: list[TempoChange] = []
    total_time = 0
    for track in midi.tracks:
        for msg in track:
            total_time += msg.time
            if msg.type == 'set_tempo':
                bpm = mido.tempo2bpm(msg.tempo)
                beats = total_time / midi.ticks_per_beat
                tempo_changes.append(TempoChange(new_bpm=bpm, beat=beats))
    return tempo_changes


def _get_track_names(midi: mido.MidiFile) -> dict[int, str]:
    """Return a mapping from track index to track name."""
    track_names = {}
    for i, track in enumerate(midi.tracks):
        for msg in track:
            if msg.type == 'track_name':
                track_names[i] = msg.name
    return track_names


def _get_channel_to_instrument_mapping(midi: mido.MidiFile) -> dict[int, int]:
    """The key of the returned dict is the channel number; the value is the instrument number."""
    channel_to_instrument = {}
    for ti, track in enumerate(midi.tracks):
        for i, msg in enumerate(track):
            if msg.type == 'program_change':
                print(f"Program change in track {ti} message count {i}: {msg.channel} -> {msg.program}")
                channel_to_instrument[msg.channel] = msg.program
    return channel_to_instrument


def process_and_save_midi(md_path: str, md_opt: str, fn: Callable[[MidiRepresentation], None]) -> None:
    """Process the midi file with md_path using fn, then exports it with name md_out"""
    midi_file = mido.MidiFile(md_path)
    midi_representation = midi_to_representation(midi_file)
    fn(midi_representation)
    midi_file_2 = representation_to_midi_file(midi_representation)
    midi_file_2.save(md_opt)


# FOR DEBUGGING PURPOSES
def _main() -> None:
    midi_file = mido.MidiFile(_MD_FILE_PATH)
    midi_representation = midi_to_representation(midi_file)
    print(midi_representation.get_starting_bpm())
    print(midi_representation.channel_instrument_map)
    print(midi_representation.bpm_changes)
    midi_file_2 = representation_to_midi_file(midi_representation)
    midi_file_2.save(_MD_OUT_PATH)


if __name__ == '__main__':
    _main()
