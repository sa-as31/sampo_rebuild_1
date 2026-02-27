import numpy as np
from gym.spaces import Discrete


class Discretized(Discrete):
    """
    Discrete wrapper for continuous actions.
    This lightweight implementation is sufficient for Sample Factory's
    type checks and simple discrete-to-continuous value mapping.
    """

    def __init__(self, n, min_action=-1.0, max_action=1.0, dtype=np.float32):
        n = int(n)
        if n < 2:
            raise ValueError("n must be >= 2 for discretization")
        super().__init__(n)
        self.min_action = float(min_action)
        self.max_action = float(max_action)
        self.dtype = dtype
        self._bins = np.linspace(self.min_action, self.max_action, n, dtype=dtype)

    def to_continuous(self, action):
        return float(self._bins[int(action)])
