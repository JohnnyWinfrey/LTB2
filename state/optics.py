
# ─── Component-level optic types ────────────────────────────────────────────
# arm: 'generation' (before sample) or 'analysis' (after sample)

class LinPol:
    """State of a linear polarizer."""
    __slots__ = ('name', 'generator', 'analyzer', 'angle')

    def __init__(self, name='', generator=False, analyzer=False, angle=0.0):
        self.name = name
        self.generator = generator
        self.analyzer = analyzer
        self.angle = angle

    def snapshot(self):
        return LinPol(self.name, self.generator, self.analyzer, self.angle)


class Retarder:
    """State of a waveplate / retarder."""
    __slots__ = ('name', 'generator', 'analyzer', 'angle')

    def __init__(self, name='', generator=False, analyzer=False, angle=0.0):
        self.name = name
        self.generator = generator
        self.analyzer = analyzer
        self.angle = angle

    def snapshot(self):
        return Retarder(self.name, self.generator, self.analyzer, self.angle)

