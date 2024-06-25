from dataclasses import dataclass

@dataclass
class Hit:
    frame_id: int
    wb_timestamp: int
    tdcword: int

@dataclass
class SPEHit(Hit):
    chatge: float
    t_ext: float #FIXME: Should it be a float?

@dataclass
class MPEHit(Hit):
    n_samples: int
    adc0_data: list[int]
    adc1_data: list[int]