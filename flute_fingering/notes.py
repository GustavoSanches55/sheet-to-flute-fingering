"""Representation of a note (or rest) in the score."""

SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DIATONIC_INDEX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
ACCIDENTAL_SYMBOL = {-2: "𝄫", -1: "♭", 0: "", 1: "♯", 2: "𝄪"}


class Note:
    """A written note (step + accidental + octave). ``step=None`` represents a rest."""

    __slots__ = ("step", "alter", "octave")

    def __init__(self, step=None, alter=0, octave=4):
        self.step = step        # "C".."B", or None for a rest
        self.alter = alter      # -2..+2 (double flat .. double sharp)
        self.octave = octave    # C4 = middle C

    def __repr__(self):
        return "Note(rest)" if self.is_rest else f"Note({self.name()})"

    def __eq__(self, other):
        return isinstance(other, Note) and (self.step, self.alter, self.octave) == \
            (other.step, other.alter, other.octave)

    @property
    def is_rest(self):
        return self.step is None

    @property
    def midi(self):
        """MIDI number (C4 = 60); enharmonic notes (D♯ / E♭) share the same number."""
        return (self.octave + 1) * 12 + SEMITONE[self.step] + self.alter

    @property
    def diatonic(self):
        """Position on the staff, in diatonic steps (ignoring accidentals)."""
        return self.octave * 7 + DIATONIC_INDEX[self.step]

    def accidental(self):
        return ACCIDENTAL_SYMBOL.get(self.alter, "?")

    def name(self):
        return f"{self.step}{self.accidental()}{self.octave}"
