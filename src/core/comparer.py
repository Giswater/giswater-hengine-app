"""
comparer.py
"""

from __future__ import annotations

from typing import List
from epanet import toolkit as tk

# Map EPANET element types to toolkit variables
VARIABLE_MAP: dict[str, dict[str, int]] = {
    'JUNCTIONS': {
        'demand': tk.DEMAND,
        'head': tk.HEAD,
        'pressure': tk.PRESSURE,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'RESERVOIRS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'TANKS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        'tank_level': tk.TANKLEVEL,
        'tank_volume' : tk.TANKVOLUME,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'PIPES': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'headloss': tk.HEADLOSS,
        'status': tk.STATUS,
        # Link status can be:
        # CLOSED = 0
        # OPEN = 1
        'quality' : tk.LINKQUAL
    },
    'VALVES': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'headloss': tk.HEADLOSS,
        'status': tk.STATUS
        # See PIPES
    },
    'PUMPS': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'head': tk.HEADLOSS,
        'energy': tk.ENERGY,
        'pump_efficiency' : tk.PUMP_EFFIC,
        'pump_state': tk.PUMP_STATE
        # Pump state can be:
        # PUMP_XHEAD   = 0,  //!< Pump closed - cannot supply head
        # PUMP_CLOSED  = 2,  //!< Pump closed
        # PUMP_OPEN    = 3,  //!< Pump open
        # PUMP_XFLOW   = 5   //!< Pump open - cannot supply flow
    },
}


class Comparer:
    """
    Compare EPANET simulation outputs between two network input files.
    """

    def __init__(
        self,
        inp1: str,
        inp2: str,
        element_filter: List| None = None,
        id_filter: List| None = None,
        method: str = None
    ):
        """
        Initialize the Comparer with two network input paths and optional
        report/binary file names.

        Args:
            inp1: Path to first EPANET .inp file.
            inp2: Path to second EPANET .inp file.
            rpt: Optional report file name for both runs.
            out: Optional binary output file name for both runs.
        """
        self.inp1 = inp1
        self.inp2 = inp2
        self._handle1: int | None = None
        self._handle2: int | None = None

    def _open(self, inp: str) -> int:
        """
        Create and open an EPANET project file.

        Returns:
            handle: Integer project handle for EPANET toolkit operations.
        """
        handle = tk.createproject()
        tk.open(handle, inp, inp.replace('.inp', '.rep'), '')
        return handle

    def _close(self, handle: int) -> None:
        """
        Close a previously opened EPANET project handle.
        """
        tk.close(handle)

    def compare(self):
        # Open proyect handles
        self._open(self.inp1)
        self._open(self.inp2)

        #

        # Close project handles
        self._close(self._handle1)
        self._close(self._handle2)


if __name__ == '__main__':
    pass
