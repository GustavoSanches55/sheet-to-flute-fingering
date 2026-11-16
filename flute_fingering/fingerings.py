"""Fingering chart for the concert flute (Boehm system).

Key names used in each note's set of "closed keys":

    T  = left thumb (B key)            L1, L2, L3 = left hand fingers
    Gs = G♯ key (left pinky)           R1, R2, R3 = right hand fingers
    Eb = E♭ key (right pinky)          Cs, C, B   = foot keys (C♯, C, B)
"""

KEYS = ("T", "L1", "L2", "L3", "Gs", "R1", "R2", "R3", "Eb", "Cs", "C", "B")

MIDI_MIN, MIDI_MAX = 59, 93  # B3 .. A6


def _f(text):
    """Turn 'T 1 2 3 G# | 1 2 3 Eb' into the set of closed keys."""
    left, _, right = text.partition("|")
    left_map = {"T": "T", "1": "L1", "2": "L2", "3": "L3", "G#": "Gs"}
    right_map = {"1": "R1", "2": "R2", "3": "R3", "Eb": "Eb", "C#": "Cs", "C": "C", "B": "B"}
    return frozenset([left_map[t] for t in left.split()] + [right_map[t] for t in right.split()])


# Keyed by MIDI number (C4 = 60), so D♯ and E♭ share the same fingering.
FINGERINGS = {
    59: _f("T 1 2 3 | 1 2 3 B"),     # B3 (B foot joint only)
    60: _f("T 1 2 3 | 1 2 3 C"),     # C4
    61: _f("T 1 2 3 | 1 2 3 C#"),    # C♯4
    62: _f("T 1 2 3 | 1 2 3"),       # D4
    63: _f("T 1 2 3 | 1 2 3 Eb"),    # D♯4 / E♭4
    64: _f("T 1 2 3 | 1 2 Eb"),      # E4
    65: _f("T 1 2 3 | 1 Eb"),        # F4
    66: _f("T 1 2 3 | 3 Eb"),        # F♯4
    67: _f("T 1 2 3 | Eb"),          # G4
    68: _f("T 1 2 3 G# | Eb"),       # G♯4 / A♭4
    69: _f("T 1 2 | Eb"),            # A4
    70: _f("T 1 | 1 Eb"),            # A♯4 / B♭4
    71: _f("T 1 | Eb"),              # B4
    72: _f("1 | Eb"),                # C5
    73: _f("| Eb"),                  # C♯5
    74: _f("T 2 3 | 1 2 3"),         # D5
    75: _f("T 2 3 | 1 2 3 Eb"),      # D♯5 / E♭5
    86: _f("T 1 2 | Eb"),            # D6
    87: _f("T 1 2 3 G# | 1 2 3 Eb"), # D♯6 / E♭6
    88: _f("T 1 2 | 1 2 Eb"),        # E6
    89: _f("T 1 3 | 1 Eb"),          # F6
    90: _f("T 1 3 | 3 Eb"),          # F♯6
    91: _f("1 2 3 | Eb"),            # G6
    92: _f("2 3 G# | Eb"),           # G♯6 / A♭6
    93: _f("T 2 | 1 Eb"),            # A6
}
# E5 to C♯6: same fingering as the first octave (only the airstream changes)
for _m in range(64, 74):
    FINGERINGS[_m + 12] = FINGERINGS[_m]
del _m


def fingering(note):
    """Set of closed keys for the note, or None if it is out of range."""
    return FINGERINGS.get(note.midi)
