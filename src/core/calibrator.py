"""
calibrator.py

Module for calibrating water networks.
"""
from __future__ import annotations

from typing import Dict, Set, Tuple
from epanet import toolkit as tk
from scipy.optimize import minimize_scalar
# import pygmo as pg
from src.core.data_container import TimeSeries


# Variable map.
NODE_VARIABLE_MAP: dict[str, int] = {
        'demand': tk.DEMAND,
        'head': tk.HEAD,
        'pressure': tk.PRESSURE,
        'quality': tk.QUALITY,
    }
LINK_VARIABLE_MAP: dict[str, int] = {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY
    }


def time_to_seconds(time_str: str) -> int:
    """
    Convert a time string, either decimal hours or "HH:MM:SS", into seconds.
    """
    # Detected hh: format.
    if ":" in time_str:
        parts = time_str.split(":")
        # pad missing parts if needed
        h, m, s = (parts + ["0", "0", "0"])[:3]
        return int(h) * 3600 + int(m) * 60 + int(s)

    # Assume decimal hours.
    return int(float(time_str) * 3600)


class OptimizationProblem:
    """
    Define an optimization problem for calibrating an EPANET model.

    Parameters:
        inp (str): Path to the EPANET input file (.inp).

        observed_data (dict): Dictionary mapping variable names to data files.
            Keys are variable names (e.g., "pressure", "flow").
            Values are paths to observation files in EPANET format.
            Supported variables must be in
            NODE_VARIABLE_MAP or LINK_VARIABLE_MAP.
    """

    def __init__(self, inp_fname, observed_data):
        # Create a project epanet toolkit handle.
        self._handle: int = tk.createproject()

        # Open epanet model.
        rpt_fname = inp_fname.replace(".inp", ".rpt")
        tk.open(self._handle, inp_fname, rpt_fname, "")
        print(f"Inp file open: {inp_fname}")

        # Load bbserved data and store as a dictionary [data_key timeseries].
        # data_key : (variable, elemente_id)
        self.observed_values: Dict[Tuple[str, str], TimeSeries] = {}

        # Read obseved values from calibtarion files.
        # Generate data_series_index and times cache.
        self._data_series_index_cache: Set(Tuple[str, str]) = set()
        self._times_cache: Dict[Tuple[str, str], int] = {}
        for variable, fname in observed_data.items():
            elements = self._read_calibration_file(fname)
            print(f"Loaded {variable} from: {fname}")
            for element_id, time_series in elements.items():
                self.observed_values[(variable, element_id)] = time_series
                self._data_series_index_cache.add((variable, element_id))
                print(f"Added {(variable, element_id)} to the data series cache.")
                self._times_cache[(variable, element_id)] = set()
                for time in time_series.times():
                    self._times_cache[(variable, element_id)].add(time)
            print(f"Time series cache contains {len(self._times_cache[(variable, element_id)])} times.")

        # Trabajamos con una sola dimension.
        self.dim = 1

    def fitness(self, x):
        """
        Specify the objective function to minimize.
        We consider the RMSE of the set of time series.
        """
        max_rmse : float = 0
        computed_values = self._compute(x)

        for data_series_index in self._data_series_index_cache:
            observed_y = self.observed_values[data_series_index]
            computed_y = computed_values[data_series_index]
            rmse = observed_y.calibrate(computed_y)["rmse"]
            max_rmse = max(max_rmse, rmse)

        return max_rmse

    def get_bounds(self):
        """Return the lower and upper bound of x variable."""
        return self._lower_bound, self._lower_bound

    def set_bounds(self, lower_bound, upper_bound):
        self._lower_bound, self._upper_bound = lower_bound, upper_bound

    def _read_calibration_file(self, fname: str,) -> Dict[str, TimeSeries]:
        """
        Read an EPANET .dat file with columns:
        element_id, time (h or HH:MM:SS), value.
        Return dict mapping element_id to list of (time_s, value).
        """
        sep = " "
        comment_char = ";"
        data = {}
        current_element = None

        with open(fname, "r") as f:
            for line in f:
                line = line.strip()
                parts = line.split(sep, maxsplit=3)

                # Remove coments.
                for i, v in enumerate(parts):
                    if comment_char in v:
                        del parts[i:]
                        break

                # Detect new element.
                if len(parts) > 2:
                    current_element = parts[0]
                    time = time_to_seconds(parts[1])
                    value = float(parts[2])
                    data[current_element] = TimeSeries()
                    data[current_element].add(time, value)

                # Add new times.
                elif len(parts) == 2:
                    time = time_to_seconds(parts[0])
                    value = float(parts[1])
                    data[current_element].add(time, value)

        return data

    def _update(self, x):
        """ Update model."""

        # pipe parameter.Roughness = x.
        link_count = tk.getcount(self._handle, tk.LINKCOUNT)
        # print(f"Link count {link_count}")
        for index in range(1, link_count + 1):
            if tk.getlinktype(self._handle, index) == tk.PIPE:
                tk.setlinkvalue(self._handle, index, tk.ROUGHNESS, x)
                # print(f"Updated link {index} roughness = {x}")

    def _compute(self, x):
        """Update and run simulation."""
        computed_values = {}
        for data_key in self._data_series_index_cache:
            computed_values[data_key] = TimeSeries()

        # Init hydraulic model
        tk.openH(self._handle)
        tk.initH(self._handle, 00)
        # print("Open and init hydraulics")

        # Update model.
        self._update(x)

        # Run loop
        while True:
            # Compute present time.
            time_h = tk.runH(self._handle)
            # Get results
            for data_series_index in self._data_series_index_cache:
                if time_h in self._times_cache[data_series_index]:
                    variable, element_id = data_series_index
                    if variable in NODE_VARIABLE_MAP:
                        code = NODE_VARIABLE_MAP[variable]
                        index = tk.getnodeindex(self._handle, element_id)
                        value = tk.getnodevalue(self._handle, index, code)
                    elif variable in LINK_VARIABLE_MAP:
                        code = LINK_VARIABLE_MAP[variable]
                        index = tk.getlinkindex(self._handle, element_id)
                        value = tk.getlinkvalue(self._handle, index, code)
                    else:
                        raise ValueError(f"Unknown variable '{variable}'")

                    # Store data series computed values.
                    computed_values[data_series_index].add(time_h, value)

            # Next time
            next_h = tk.nextH(self._handle)

            # End of loop.
            if next_h == 0:
                break

        return computed_values

    def _close(self) -> None:
        """Release EPANET resources."""
        try:
            tk.close(self._handle)
            tk.deleteproject(self._handle)
        except Exception:
            pass
        finally:
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False


def calibrate(problem):
    return minimize_scalar(problem.fitness, bounds=problem.get_bounds())
