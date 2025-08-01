"""
calibrator.py

Module for calibrating water networks.
"""
from __future__ import annotations
import math
import statistics
from typing import Dict, List, Tuple
from enum import Enum
from epanet import toolkit as tk
# import pygmo as pg


# Variable map.
class ElementType(Enum):
    NODE = "node"
    LINK = "link"

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

class DataSeries:
    """Store time, observed_value, computed_value series."""
    def __init__(self, filename) ->None:
        self.elements: Dict[str, List[int, float, float]]
        self.elements = self.read_calibration_file(filename)

    def _time_to_seconds(self, time_str: str) -> int:
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

    def read_calibration_file(self, filename: str,) -> Dict[str, List[Tuple[float, float]]]:
        """
        Read an EPANET .dat file with columns:
        element_id, time (h or HH:MM:SS), value.
        Return dict mapping element_id to list of (time_s, value).
        """
        sep = " "
        comment_char = ";"
        data: Dict[str, List[Tuple[float, float]]] = {}
        current_element = None
        
        with open(filename, "r") as f:
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
                    time = self._time_to_seconds(parts[1])
                    value = float(parts[2])
                    data[current_element] = [(time, value,)]
                
                # Add new times.
                elif len(parts) == 2:
                    time = self._time_to_seconds(parts[0])
                    value = float(parts[1])
                    data[current_element].append((time, value,))
                  
        return data

class Calibration:
    """
    Perform calibration by comparing observed DataSeries
    against EPANET simulation outputs.
    """

    def __init__(self, inp_filename: str, **observations: str) -> None:
        """
        Args:
            inp_filename: path to EPANET .inp file.
            observations: mapping variable_name -> .dat filename
        """
        self.inp_filename = inp_filename
        self._handle: int | None = None
        self.variables: Dict[str, DataSeries] = {}

        # open EPANET project.
        self._handle = self._open(inp_filename)

        # load observed data.
        for var_name, fname in observations.items():
            ds = DataSeries(fname)
            self.variables[var_name] = ds

        # Add computed values.
        self._handle = self._open(self.inp_filename)
        self._add_computed_values()
        self._close(self._handle)
        
    def _open(self, inp: str) -> int:
        handle = tk.createproject()
        rep = inp.replace(".inp", ".rep")
        tk.open(handle, inp, rep, "")
        return handle

    def _close(self, handle: int) -> None:
        tk.close(handle)
        tk.deleteproject(handle)

    def __enter__(self) -> Calibration:
        if self._handle is None:
            self._handle = self._open(self.inp_filename)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._handle is not None:
            self._close(self._handle)
            self._handle = None
        
    def _add_computed_values(self):
        # Get results
        duration = tk.gettimeparam(self._handle, tk.DURATION)
        print("Model duration =", duration)
        quality_analysis_type, _ = tk.getqualtype(self._handle)
        print("Quality Analysis =", quality_analysis_type != tk.NONE)
        
     
        # Start Hydraulic analysis.
        tk.openH(self._handle)
        tk.initH(self._handle, 00)
       
        # Start quality analysisis.
        if quality_analysis_type != tk.NONE: 
            tk.openQ(self._handle)
            tk.initQ(self._handle, 00)
        
        # Solve loop.
        loop_count = 0
        print("*"*30)
        while True:
            loop_count += 1
            print("Loop count =", loop_count)
            
            # Run hydraulic step.
            time_h = tk.runH(self._handle)
            print("Time hydraulic =", time_h)
                
            # Computes qality models.
            if quality_analysis_type != tk.NONE:
                while True:
                    time_q = tk.runQ(self._handlee)
                    tk.nextQ(self._handle)
                    if time_q == time_h:
                        break
                print("Time quality =", time_q)
            
            # Store results.
            for variable_name, elements in self.variables.items():
                for element_id, data_series in elements.elements.items():
                    for i, data in enumerate(data_series):
                        if time_h == data[0] and len(data) == 2:
                            if variable_name in NODE_VARIABLE_MAP:
                                index = tk.getnodeindex(self._handle, element_id)
                                value = tk.getnodevalue(self._handle, index, NODE_VARIABLE_MAP[variable_name])
                            else:
                                index = tk.getlinkindex(self._handle, element_id)
                                value = tk.getlinkvalue(self._handle, index, LINK_VARIABLE_MAP[variable_name])
                            data_series[i] = data + (value,)
                            print(f"Added computed value of {variable_name} to element ID {element_id}:", data_series[i])
            
            # Advance time.
            next_h = tk.nextH(self._handle)
            print("*"*30)
            
            # End of loop.
            if next_h == 0:
                break

    def calibrate(self):
        """
        Print a calibration report per variable and overall network.
        """
        for variable, dataset in self.variables.items():
            print(f"\nCalibration Statistics for {variable.capitalize()}\n")
            print("                Num    Observed    Computed    Mean     RMS")
            print("  ID            Obs        Mean        Mean   Error   Error")
            print("  ---------------------------------------------------------")

            location_stats = []  # Store per-node stats for network summary
            obs_means, comp_means = [], []

            for element_id, series in dataset.elements.items():
                # Filter only triplets (skip if computed not appended)
                series = [entry for entry in series if len(entry) == 3]
                if not series:
                    continue

                times, obs_vals, comp_vals = zip(*series)
                num_obs = len(obs_vals)
                obs_mean = statistics.mean(obs_vals)
                comp_mean = statistics.mean(comp_vals)
                errors = [c - o for o, c in zip(obs_vals, comp_vals)]
                mean_error = statistics.mean(errors)
                rms_error = math.sqrt(statistics.mean([e**2 for e in errors]))

                obs_means.append(obs_mean)
                comp_means.append(comp_mean)
                location_stats.append((num_obs, obs_mean, comp_mean, mean_error, rms_error))

                print(f"{element_id:>12} {num_obs:7} {obs_mean:11.2f} {comp_mean:11.2f} {mean_error:7.3f} {rms_error:7.3f}")

            print("  ---------------------------------------------------------")
            if location_stats:
                total_obs = sum(x[0] for x in location_stats)
                mean_obs = statistics.mean([x[1] for x in location_stats])
                mean_comp = statistics.mean([x[2] for x in location_stats])
                mean_error = statistics.mean([x[3] for x in location_stats])
                rms_error = statistics.mean([x[4] for x in location_stats])

                print(f"{'Network':>12} {total_obs:7} {mean_obs:11.2f} {mean_comp:11.2f} {mean_error:7.3f} {rms_error:7.3f}")

                # Correlation between observed and computed means
                try:
                    r = statistics.correlation(obs_means, comp_means)
                    print(f"\n  Correlation Between Means: {r:.3f}")
                except Exception:
                    print("\n  Correlation Between Means: not computable (insufficient data)")

        