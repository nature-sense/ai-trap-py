from dataclasses import dataclass

@dataclass
class DetectionMetadata:
    session: str
    detection: int
    created: int
    updated: int
    score: float
    clazz: int
    width: int
    height: int
