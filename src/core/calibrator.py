"""
calibrator.py

Module for calibrating water networks with EPANET.

This module defines a thin optimization wrapper around EPANET's hydraulic
simulation loop to calibrate a single parameter (e.g., pipe roughness) by
minimizing an objective based on observed time series.

Key concepts
------------
- Observed data are provided per (variable, element_id) pair and loaded from
  simple text files (typically EPANET .dat-like lists).
- During each simulation, the model is advanced with EPANET and the desired
  variables are sampled only at time instants that match the observed data.
- The objective (fitness) computes an error metric between observed and
  computed series. Here, the metric is the worst-case RMSE across series.
- A 1-D bounded search (scipy.optimize.minimize_scalar, method="bounded")
  is used to find the parameter value that minimizes the objective.

Assumptions & caveats
---------------------
- Time matching is exact: a simulated time 't' contributes only if it is
  exactly present in the observed set for that series.
- The code expects the observation files to follow a simple format:
  either "element_id time value" lines, optionally followed by "time value"
  continuation lines for the same element (see _read_calibration_file).
- This implementation calibrates a single scalar parameter (self.dim = 1).
  Extending to vectors will require adapting _update() and the optimizer.
"""

from __future__ import annotations

from typing import Dict, Set, Tuple
from epanet import toolkit as tk
from scipy.optimize import minimize_scalar
# import pygmo as pg

# Note: Consider moving TimeSeries to utils.py and removing data_container.py
from src.core.data_container import TimeSeries


# -----------------------------------------------------------------------------
# Variable map
# -----------------------------------------------------------------------------
# These dictionaries map textual variable names used in observation files
# to the corresponding EPANET toolkit codes for nodes and links. Only
# variables listed here are accepted by this module.
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
    Convert a time string to seconds.

    Accepted formats
    ----------------
    - Decimal hours: e.g., "1.5" -> 5400 seconds.
    - Clock style "HH:MM:SS": e.g., "01:30:00" -> 5400 seconds.
      Shorter forms like "HH:MM" are allowed; missing fields default to 0.

    Notes
    -----
    - The function is intentionally strict: non-numeric tokens will raise
      ValueError through int/float casting.
    """
    # Detected HH:MM:SS (or HH:MM) format.
    if ":" in time_str:
        parts = time_str.split(":")
        # Pad missing parts if needed.
        h, m, s = (parts + ["0", "0", "0"])[:3]
        return int(h) * 3600 + int(m) * 60 + int(s)

    # Assume decimal hours.
    return int(float(time_str) * 3600)


class OptimizationProblem:
    """
    Define an optimization problem for calibrating an EPANET model.

    Parameters
    ----------
    inp_fname : str
        Path to the EPANET input file (.inp).
    observed_data : dict[str, str]
        Dictionary that maps a variable name (e.g., "pressure", "flow") to the
        path of its observation file. Supported variables must exist in
        NODE_VARIABLE_MAP or LINK_VARIABLE_MAP.

    State
    -----
    self._handle : int
        EPANET project handle.
    self.observed_values : Dict[(str, str), TimeSeries]
        Observed series keyed by (variable, element_id).
    self._data_series_key_cache : Set[(str, str)]
        Convenience set of the same keys to iterate deterministically.
    self._times_cache : Dict[(str, str), Set[int]]
        For each (variable, element_id), the set of observed times (seconds) for
        O(1) membership tests during sampling.
    self.dim : int
        Problem dimension; here fixed to 1 (single scalar parameter).
    """

    def __init__(self, inp_fname, observed_data):
        # ---------------------------------------------------------------------
        # EPANET project lifecycle: create project and open the model files.
        # The report file is automatically named after the input file.
        # ---------------------------------------------------------------------
        self._handle: int = tk.createproject()

        # Open EPANET model.
        rpt_fname = inp_fname.replace(".inp", ".rpt")
        tk.open(self._handle, inp_fname, rpt_fname, "")
        print(f"Inp file open: {inp_fname}")

        # ---------------------------------------------------------------------
        # Observed dataset containers.
        # observed_values: (variable, element_id) -> TimeSeries
        # The key tuple is referred to as a "data series key" below.
        # ---------------------------------------------------------------------
        self.observed_values: Dict[Tuple[str, str], TimeSeries] = {}

        # Precomputed convenience collections:
        # - _data_series_key_cache: keys we will iterate during compute/fitness.
        # - _times_cache: fast membership test for observed time instants.
        self._data_series_key_cache: Set[Tuple[str, str]] = set()
        self._times_cache: Dict[Tuple[str, str], Set[int]] = {}

        # ---------------------------------------------------------------------
        # Load observations from files, grouping rows by element_id to build
        # one TimeSeries per element, for each variable provided.
        # ---------------------------------------------------------------------
        for variable, fname in observed_data.items():
            elements = self._read_calibration_file(fname)
            print(f"Loaded {variable} from: {fname}")
            for element_id, time_series in elements.items():
                self.observed_values[(variable, element_id)] = time_series
                self._data_series_key_cache.add((variable, element_id))
                print(f"Added {(variable, element_id)} "
                      "to the data series key cache.")

                # Create a set of observed times for exact-time sampling.
                self._times_cache[(variable, element_id)] = set()
                for time in time_series.times():
                    self._times_cache[(variable, element_id)].add(time)
            # Informative message: for the last (variable, element_id) seen
            # in this file, report the number of unique time instants.
            # This helps checking alignment with EPANET's reporting times.
            print(
                "Time series cache contains "
                f"{len(self._times_cache[(variable, element_id)])} times."
            )

        # Only one scalar decision variable (e.g., global roughness).
        self.dim = 1

    def fitness(self, x):
        """
        Objective function to minimize.

        The metric used is the worst-case RMSE across all series present in
        self.observed_values. For each (variable, element_id) key we:
          1) Run the model with parameter x (via _compute).
          2) Retrieve the computed TimeSeries for that key.
          3) Ask the observed series to 'calibrate' against the computed one.
          4) Extract 'rmse' from the returned metrics dict.
        The maximum RMSE across keys is returned, implementing a minimax
        strategy that focuses on the most poorly fitted series.

        Parameters
        ----------
        x : float
            Candidate parameter value (e.g., pipe roughness).

        Returns
        -------
        float
            Worst-case RMSE across all observed series.
        """
        max_rmse : float = 0
        computed_values = self._compute(x)

        # For each computed time series, get the RMSE and track the maximum.
        for data_series_key in self._data_series_key_cache:
            observed_y = self.observed_values[data_series_key]
            computed_y = computed_values[data_series_key]
            rmse = observed_y.calibrate(computed_y)["rmse"]
            max_rmse = max(max_rmse, rmse)

        return max_rmse

    def get_bounds(self):
        """
        Return the (lower, upper) bounds of the decision variable.

        Notes
        -----
        - Bounds must be provided by the caller via set_bounds() before
          optimization starts. This method expects those attributes to
          exist when called.
        """
        if self._lower_bounds is None or self._upper_bounds is None:
            raise RuntimeError(
                "Bounds not set. Call set_bounds(lower, upper) first."
            )
        return self._lower_bounds, self._upper_bounds

    def set_bounds(self, lower_bounds, upper_bounds):
        """
        Define the admissible interval for the decision variable.
        
        Parameters
        ----------
        lower_bounds : float
            Lower bound for the scalar parameter.
        upper_bounds : float
            Upper bound for the scalar parameter.
        
        Notes
        -----
        - No validation is performed here (e.g., lower < upper). Provide
          consistent values to avoid optimizer errors.
        """
        self._lower_bounds = lower_bounds
        self._upper_bounds = upper_bounds

    def _read_calibration_file(self, fname: str,) -> Dict[str, TimeSeries]:
        """
        Parse an observation file and build one TimeSeries per element_id.

        Expected file layout
        --------------------
        - Comment marker: ';' (anything after ';' on a line is ignored).
        - Whitespace: values are separated by spaces; multiple spaces are
          accepted (but see 'Implementation notes' below).
        - Two kinds of lines are supported:

          1) Header lines (start a new element block):
             element_id<space>time<space>value
             Example:  J08  01:00:00  52.3

          2) Continuation lines (belong to the most recent element_id):
             time<space>value
             Example:  02:00:00  51.8

        Returns
        -------
        Dict[str, TimeSeries]
            Mapping element_id -> TimeSeries loaded with (time, value) pairs.

        Implementation notes
        --------------------
        - This function uses a simple 'split' with a single-space separator
          to honor the original implementation. If your files include tabs
          or irregular spacing, consider switching to 'line.split()' (no
          explicit separator) for extra robustness.
        - Lines with fewer than 2 tokens (after trimming comments) are ignored.
        - A continuation line requires that a header line appeared before, as
        - it reuses 'current_element' to append more times for the same id.
        """
        sep = " "
        comment_char = ";"
        variable_observations: Dict[str, TimeSeries] = {}
        current_element = None

        with open(fname, "r") as f:
            for line in f:
                # Trim trailing newline/whitespace and split by fixed separator.
                line = line.strip()
                parts = line.split(sep, maxsplit=3)

                # Remove comments in-place: truncate at first token containing ';'
                # Example: "J08  01:00:00  52.3  ; note" -> ["J08","01:00:00","52.3"]
                for i, v in enumerate(parts):
                    if comment_char in v:
                        del parts[i:]
                        break

                # Header line: new element block with (element_id, time, value)
                if len(parts) > 2:
                    current_element = parts[0]
                    time = time_to_seconds(parts[1])
                    value = float(parts[2])
                    variable_observations[current_element] = TimeSeries()
                    variable_observations[current_element].add(time, value)

                # Continuation line: (time, value) for the last current_element
                elif len(parts) == 2:
                    time = time_to_seconds(parts[0])
                    value = float(parts[1])
                    # Assumes at least one header line appeared previously.
                    variable_observations[current_element].add(time, value)

                # Lines with < 2 tokens (after comment stripping) are ignored.

        return variable_observations

    def _update(self, x):
        """
        Apply parameter updates to the EPANET model.

        Current behavior
        ----------------
        - Set ROUGHNESS = x for every link whose type is PIPE.
        - Other link types remain unchanged.

        Notes
        -----
        - This function is intentionally simple and global. To calibrate per
          material or per-subset of pipes, filter by link properties here.
        """

        # Pipe parameter: ROUGHNESS = x
        link_count = tk.getcount(self._handle, tk.LINKCOUNT)
        for index in range(1, link_count + 1):
            if tk.getlinktype(self._handle, index) == tk.PIPE:
                tk.setlinkvalue(self._handle, index, tk.ROUGHNESS, x)

    def _compute(self, x):
        """
        Update the model with parameter 'x' and run a single hydraulic period.

        Workflow
        --------
        1) Call _update(x) to set pipe roughness prior to opening hydraulics.
        2) Open hydraulics (openH) and initialize (initH).
        3) Advance the hydraulic clock with runH()/nextH() until completion.
        4) At each time step, sample the requested variables only if the current
           time matches one of the observed time instants for that series.
        5) Close hydraulics (closeH) and return the computed series.

        Returns
        -------
        Dict[(str, str), TimeSeries]
            A dictionary keyed by (variable, element_id) with simulated values
            at observed times only.

        Important
        ---------
        - Time matching is exact (no tolerance/interpolation).
        - EPANET node/link indices are resolved on-the-fly at each match to
          stay faithful to the original code path.
        """

        # Storage of computed values per (variable, element_id).
        computed_values: Dict[Tuple[str, str], TimeSeries] = {}

        # Prepare the containers for all observed keys.
        for data_series_key in self._data_series_key_cache:
            computed_values[data_series_key] = TimeSeries()

        # Apply parameter updates before hydraulic initialization.
        self._update(x)

        # Open and initialize the hydraulic solver.
        tk.openH(self._handle)
        tk.initH(self._handle, 00)

        # Main hydraulic loop.
        while True:
            # Current simulation time (seconds since t0).
            time_h = tk.runH(self._handle)

            # Sample each requested series if the time matches exactly.
            for data_series_key in self._data_series_key_cache:
                if time_h in self._times_cache[data_series_key]:
                    variable, element_id = data_series_key

                    # Resolve EPANET code and element index, then read value.
                    if variable in NODE_VARIABLE_MAP:
                        code = NODE_VARIABLE_MAP[variable]
                        index = tk.getnodeindex(self._handle, element_id)
                        value = tk.getnodevalue(self._handle, index, code)
                    elif variable in LINK_VARIABLE_MAP:
                        code = LINK_VARIABLE_MAP[variable]
                        index = tk.getlinkindex(self._handle, element_id)
                        value = tk.getlinkvalue(self._handle, index, code)
                    else:
                        # Defensive programming: should never happen if inputs
                        # are validated against the maps above.
                        raise ValueError(f"Unknown variable '{variable}'.")

                    # Append computed (time, value) to the corresponding series.
                    computed_values[data_series_key].add(time_h, value)

            # Advance to the next hydraulic time; '0' signals the end.
            next_h = tk.nextH(self._handle)
            # End of loop check; hydraulics will be closed after the loop.
            if next_h == 0:
                break

        # Always close hydraulics after the loop.
        tk.closeH(self._handle)

        return computed_values

    def _close(self) -> None:
        """
        Release EPANET resources associated with this problem.

        Notes
        -----
        - This method attempts to close and delete the project handle and then
          null it out, ignoring any exceptions to keep shutdown robust.
        """
        try:
            tk.close(self._handle)
            tk.deleteproject(self._handle)
        except Exception:
            pass
        finally:
            self._handle = None

    def __enter__(self):
        """
        Context manager entry: return self so the instance can be used in a
        'with' block.

        Returns
        -------
        OptimizationProblem
            The current instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensure EPANET resources are released on explicit shutdown.

        Returns
        -------
        bool
            Always False to propagate exceptions raised by callers.
        """
        self._close()
        return False


def calibrate(problem):
    """
    Run the 1-D bounded optimization against `problem.fitness`.
    
    Parameters
    ----------
    problem : OptimizationProblem
        The calibration problem exposing `fitness(x)` and `get_bounds()`.
    
    Returns
    -------
    scipy.optimize.OptimizeResult
        Result structure with at least the following fields:
        - x        : float, the best parameter value found.
        - fun      : float, objective function value at x.
        - success  : bool, whether the optimizer succeeded.
        - status   : int, status code (0 indicates success for this method).
        - message  : str, human-readable status message.
        - nit      : int, number of iterations performed.
        - nfev     : int, number of function evaluations.
    
    Notes
    -----
    - Uses `method="bounded"` (Golden-section / Brent derivative-free
      routine) suitable for unimodal objectives on a closed interval.
    - Tolerance `xatol` controls the absolute error in x upon termination.
    """
    res = minimize_scalar(problem.fitness,
                          bounds=problem.get_bounds(),
                          method="bounded",
                          options={"xatol": 1e-9}
                          )
    return res
