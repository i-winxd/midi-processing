import logging
import math
from collections import Counter
from copy import copy, deepcopy
from dataclasses import dataclass
from typing import Callable, Any, Optional, TypeVar

import mido  # type: ignore
from mido import MetaMessage

EPSILON = 1e-7


def float_lt(a: float, b: float) -> bool:
    return a < b and not math.isclose(a, b, abs_tol=EPSILON)


def float_gt(a: float, b: float) -> bool:
    return a > b and not math.isclose(a, b, abs_tol=EPSILON)


def float_lte(a: float, b: float) -> bool:
    return a <= b or math.isclose(a, b, abs_tol=EPSILON)


def float_gte(a: float, b: float) -> bool:
    return a >= b or math.isclose(a, b, abs_tol=EPSILON)


def sandwiched(a: float, b: float, c: float) -> bool:
    """a <= b < c"""
    return float_lte(a, b) and float_lt(b, c)


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    )

_DEFAULT_TICKS_PER_BEAT = 96
_DEFAULT_BPM = 120
_CO = TypeVar("_CO", bound="Copyable")


class Copyable:
    def copy(self: _CO, update: Optional[dict[str, Any]] = None, deep: bool = False) -> _CO:
        copy_of = deepcopy(self) if deep else copy(self)
        if update:
            for attr, value in update.items():
                setattr(copy_of, attr, value)
        return copy_of


@dataclass
class Note(Copyable):
    """FIELDS:

    - channel: int  # counts from 0. FL counts from 1.
    - note: int  # 60: C5, 61: C#5
    - velocity: int  # 0 to 100
    - beat: float  # beat count where this plays from the start of the file
    - duration: float  # in beats
    """
    channel: int  # counts from 0. FL counts from 1.
    key: int  # 60: C5, 61: C#5
    vel: int  # 0 to 100
    beat: float  # beat count where this plays from the start of the file
    duration: float  # in beats


@dataclass
class TimeSignature(Copyable):
    """FIELDS:

    - numerator: int
    - denominator_log2: int
    - beat: float
    """
    numerator: int
    denominator_log2: int
    beat: float

    def get_absolute_bar_length(self) -> float:
        """How many unit beats (assuming 4/4) are in a bar?"""
        # Stretch factor of the denominator is 4/d
        return self.numerator * (4 / (2 ** self.denominator_log2))

    def get_absolute_tempo_squish_factor(self) -> float:
        """Multiply this to the tempo.
        quarter gets one beat
        eighth gets one beat -> a beat lasts half as long -> twice the speed, *2
        """
        return (2 ** self.denominator_log2) / 4


@dataclass
class Track(Copyable):
    """Fields:

    - notes: list[Note]
    - track_name: str
    """

    notes: list[Note]
    track_name: str

    def clamp_notes(self) -> None:
        self.notes.sort(key=lambda s: s.beat)
        previous_note_dict: dict[int, Note] = {}
        for i in range(len(self.notes)):
            cur_note = self.notes[i]
            if cur_note.key in previous_note_dict:
                prev_note = previous_note_dict[cur_note.key]
                required_duration = min(prev_note.duration, max(cur_note.beat - prev_note.beat - 0.1, 0))
                prev_note.duration = required_duration
            previous_note_dict[cur_note.key] = cur_note

    def slice(self, b: float, e: float) -> "Track":
        """Return a copy of self with only notes that start in [b, e).
        All notes in the returned list will have their beat start subtracted by b"""
        notes_list = [
            note.copy(update={"beat": max(0.0, note.beat - b)})
            for note in self.notes if
            # b <= note.beat < e
            sandwiched(b, note.beat, e)]
        return self.copy(update={"notes": notes_list})

    def offset(self, beats: float) -> None:
        """ -> """
        for note in self.notes:
            note.beat += beats

    def scale(self, factor: float) -> None:
        for note in self.notes:
            note.beat *= factor

    def slice_with_time_signature(self, b: float, e: float, time_sig: TimeSignature) -> "Track":
        """Return a copy of self with only notes that start in [b, e), and adjust according to time signature.
        All notes in the returned list will have their beat start subtracted by b"""
        notes_list = [
            note.copy(update={"beat": max(0.0, note.beat - b) * time_sig.get_absolute_tempo_squish_factor()})
            for note in self.notes if
            # b <= note.beat < e
            sandwiched(b, note.beat, e)]
        return self.copy(update={"notes": notes_list})

    def most_used_channel(self) -> int:
        """Return the most common channel in the notes
        of this track, or -1 if there is none."""
        if len(self.notes) == 0:
            return -1
        channels = [n.channel for n in self.notes]
        most_common, _ = Counter(channels).most_common(1)[0]
        return most_common


@dataclass
class TempoChange(Copyable):
    """Fields:

    - beat: float
    - new_bpm: float
    """
    beat: float
    new_bpm: float


@dataclass
class MidiEvent(Copyable):
    """Field:

    - note: Note
    - event_time: float
    - on: bool
    """

    note: Note
    event_time: float
    on: bool


def generate_4_4_time_sig() -> TimeSignature:
    return TimeSignature(numerator=4, denominator_log2=2, beat=0)


@dataclass
class MidiRepresentation(Copyable):
    """FIELDS:

    - tracks: dict[int, Track]  # maps track numbers to track names
    - channel_instrument_map: dict[int, int]
    - bpm_changes: list[TempoChange]
    - time_signature_changes: list[TimeSignature]
    """
    tracks: list[Track]  # maps track numbers to track names
    channel_instrument_map: dict[int, int]
    bpm_changes: list[TempoChange]
    time_signature_changes: list[TimeSignature]

    def clear_empty_tracks(self) -> None:
        to_pop: list[int] = []
        for i, track in enumerate(self.tracks):
            if len(track.notes) == 0:
                to_pop.append(i)
        for i in reversed(to_pop):
            self.tracks.pop(i)

    def get_song_length(self) -> int:
        """Get the length of the track in beats, rounded up."""
        highest_beat = 0
        for v in self.tracks:
            for n in v.notes:
                highest_beat = max(highest_beat, math.ceil(n.beat + n.duration))
        return highest_beat

    def get_starting_bpm(self) -> float:
        if len(self.bpm_changes) == 0:
            return _DEFAULT_BPM
        return self.bpm_changes[0].new_bpm

    def get_starting_time_signature(self) -> TimeSignature:
        for time_sig in self.time_signature_changes:
            if time_sig.beat == 0.0:
                return time_sig
        else:
            return generate_4_4_time_sig()


def string_empty_fallback(text: str, fallback: str) -> str:
    return text if text != "" else fallback


def clamp_sorted(li: list[float], a: float, b: float) -> tuple[int, int]:
    """li must be sorted!
    Return indices p and q such that everything at and right of p is >= a and everything to the left of q is < b
    """
    assert (a <= b)
    assert sorted(li) == li
    p_set = False
    q_set = False
    p = 0
    q = 0
    for i, val in enumerate(li):
        if not p_set:
            if float_lte(a, val):
                p_set = True
                p = i
                q = len(li)
        if not q_set:
            if float_lte(b, val):
                q_set = True
                q = i
        if p_set and q_set:
            break
    return p, q


def representation_to_midi_file(midi_representation: MidiRepresentation) -> mido.MidiFile:
    """Convert a MidiRepresentation instance to a mido.MidiFile instance that can be
    exported to a new Midi file.
    NOTHING IN midi_representation NEEDS TO BE SORTED
    midi_representaton may be mutated!
    """
    # for _, t in midi_representation.tracks.items():
    #     t.clamp_notes()

    # end_of_track = MetaMessage("end_of_track", time=0)

    midi_file = mido.MidiFile()
    ticks_per_beat = _DEFAULT_TICKS_PER_BEAT
    midi_file.ticks_per_beat = ticks_per_beat

    # TEMPO TRACK START
    tempo_track = mido.MidiTrack()
    tempo_track_name_message = mido.MetaMessage('track_name', name="Tempo changes")
    tempo_track.append(tempo_track_name_message)

    # this is a bug fix. whatever this is, you should probably push it
    previous_tc = 0
    for bpm_change in sorted(midi_representation.bpm_changes, key=lambda s: s.beat):
        tempo_in_microseconds = int(60000000 / bpm_change.new_bpm)
        # accumulated_ticks += int(bpm_change.beat * ticks_per_beat)
        tc_time_now = int(bpm_change.beat * ticks_per_beat)
        time_delta = tc_time_now - previous_tc
        previous_tc = tc_time_now
        tempo_message = mido.MetaMessage('set_tempo', tempo=tempo_in_microseconds, time=time_delta)
        tempo_track.append(tempo_message)
    tempo_track.append(MetaMessage("end_of_track", time=0))
    midi_file.tracks.append(tempo_track)
    # TEMPO TRACK END

    midi_tracks_pack = midi_representation.tracks

    for track_no, track in enumerate(midi_tracks_pack):
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

        sorted_notes = sorted(track.notes, key=lambda s: s.beat)
        for note in sorted_notes:
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
                                   note=event.note.key, velocity=event.note.vel, time=delta_time)
            midi_track.append(message)
        midi_track.append(MetaMessage("end_of_track", time=0))
        midi_file.tracks.append(midi_track)

    return midi_file


def midi_to_representation(midi_file: mido.MidiFile) -> MidiRepresentation:
    """Create a MidiRepresentation instance from midi_file.
    """
    tracks = {}
    channel_ins_mapping = _get_channel_to_instrument_mapping(midi_file)
    track_names: dict[int, str] = _get_track_names(midi_file)
    for i, track in enumerate(midi_file.tracks):
        notes: list[Note] = []
        accumulated_time = 0
        # [PITCH, CHANNEL]
        note_look_behind: dict[tuple[int, int], Note] = {}
        for msg in track:

            accumulated_time += msg.time

            if msg.type == 'note_on':
                beat = accumulated_time / midi_file.ticks_per_beat
                note = Note(
                    channel=msg.channel,
                    key=msg.note,
                    vel=msg.velocity,
                    beat=beat,
                    duration=0
                )
                notes.append(note)

                behind_note = note_look_behind.pop((msg.note, msg.channel), None)
                if behind_note is not None:
                    logging.debug("Correcting behind note")
                    behind_note_dur = beat - behind_note.beat
                    if behind_note_dur <= 0:
                        for k, cur_note in enumerate(notes):
                            if cur_note is behind_note:
                                notes.pop(k)
                                break
                        else:  # no break
                            logging.error("Should never get here.")
                            assert False
                    else:
                        behind_note.duration = behind_note_dur
                note_look_behind[(msg.note, msg.channel)] = note

            elif msg.type == 'note_off':
                fetched_note = note_look_behind.pop((msg.note, msg.channel), None)
                if fetched_note is not None:
                    assert (fetched_note.duration == 0)
                    beat = accumulated_time / midi_file.ticks_per_beat
                    duration = beat - fetched_note.beat
                    fetched_note.duration = max(0, duration)
                else:
                    logging.debug("note_off has no corresponding note_on; ignoring.")
        track_name = track_names.get(i, "")
        tracks[i] = Track(notes=notes, track_name=track_name)

    # why did I start doing this as a dictionary
    tracks_enumerated = [v for _, v in sorted(list(tracks.items()), key=lambda s: s[0])]

    midi_representation = MidiRepresentation(
        tracks=tracks_enumerated,
        channel_instrument_map=channel_ins_mapping,
        bpm_changes=_get_tempo_changes(midi_file),
        time_signature_changes=_get_time_signature(midi_file)
    )

    midi_representation.clear_empty_tracks()

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
                beats = augment_total_time(total_time) / midi.ticks_per_beat
                if not any(c.beat == beats and c.new_bpm == bpm for c in tempo_changes):
                    tempo_changes.append(TempoChange(new_bpm=bpm, beat=beats))
    tempo_changes.sort(key=lambda s: s.beat)

    # duplicate remover
    new_tempo_changes: list[TempoChange] = []
    tempo_slider = -1.0
    for i, tc in enumerate(tempo_changes):
        if tempo_slider != tc.new_bpm:
            tempo_slider = tc.new_bpm
            new_tempo_changes.append(tc)
    return new_tempo_changes


def augment_total_time(tt: int) -> int:
    if tt == 0:
        return tt
    else:
        return tt + 1


def _get_time_signature(midi: mido.MidiFile) -> list[TimeSignature]:
    time_signature_changes: list[TimeSignature] = []
    total_time = 0
    for track in midi.tracks:
        for msg in track:
            total_time += msg.time
            if msg.type == 'time_signature':
                beats = total_time / midi.ticks_per_beat
                time_signature_changes.append(TimeSignature(numerator=msg.numerator, denominator_log2=msg.denominator,
                                                            beat=beats))
    return time_signature_changes


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
                logging.debug(f"Program change in track {ti} message count {i}: {msg.channel} -> {msg.program}")
                channel_to_instrument[msg.channel] = msg.program
    return channel_to_instrument


def process_and_save_midi(md_path: str, md_opt: str, fn: Callable[[MidiRepresentation], None]) -> None:
    """Process the midi file with md_path using fn, then exports it with name md_out"""
    midi_file = mido.MidiFile(md_path)
    midi_representation = midi_to_representation(midi_file)
    fn(midi_representation)
    midi_file_2 = representation_to_midi_file(midi_representation)
    midi_file_2.save(md_opt)


def process_and_save_midi_mut(md_path: str, md_opt: str,
                              fn: Callable[[MidiRepresentation], MidiRepresentation]) -> None:
    """Process the midi file with md_path using fn, then exports it with name md_out"""
    midi_file = mido.MidiFile(md_path)
    midi_representation = midi_to_representation(midi_file)
    midi_representation_2 = fn(midi_representation)
    midi_file_2 = representation_to_midi_file(midi_representation_2)
    midi_file_2.save(md_opt)
