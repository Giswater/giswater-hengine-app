"""
data_container module.

Defines TimeSeries and DataContainer classes.

TimeSeries: manage a series of (time, value) tuples with a single scalar value.
DataContainer: store multiple TimeSeries indexed by (element_type, element_id,
variable, value_source), with units.
"""
from __future__ import annotations
from array import array
from typing import Dict, Iterable, List, Optional, Tuple, Union
import math


class TimeSeries:
    """
    Manage time series of (time, value) tuples using arrays.

    time: seconds (float)
    value: float or bool
    """

    def __init__(
        self,
        dtype: type = float
    ) -> None:
        self._dtype: type = dtype
        self._is_uniform: bool = True
        self._initial_time: Optional[float] = None
        self._delta_time: Optional[float] = None
        self._count: int = 0
        self._times: Optional[array] = None
        self._values: Optional[array] = None
        self._time_code: str = 'd'
        self._value_code: str = (
            'b' if self._dtype is bool else 'd'
        )

    def __len__(self) -> int:
        return self._count

    def __iter__(self) -> Iterable:
        return self.items()

    def add(
        self,
        time: float,
        value: Union[float, bool]
    ) -> None:
        """
        Append (time, value); allow out-of-order times.
        Detect uniformity and free _times when uniform.
        """
        t = float(time)
        v = self._dtype(value)

        # first point
        if self._count == 0:
            self._initial_time = t
            self._times = array(
                self._time_code,
                [t]
            )
            self._values = array(
                self._value_code,
                [
                    int(v) if self._dtype is bool else v
                ]
            )
            self._count = 1
            return

        assert self._times and self._values

        # duplicate time?
        for tt in self._times:
            if abs(tt - t) < 1e-9:
                raise ValueError(
                    f"Duplicate time {t}"
                )

        # derive delta on second point
        if self._is_uniform and self._count == 1:
            self._delta_time = (
                t - self._initial_time  # type: ignore
            )

        # append
        self._times.append(t)
        self._values.append(
            int(v) if self._dtype is bool else v
        )
        self._count += 1

        # uniform check
        if self._is_uniform:
            exp = (
                self._initial_time  # type: ignore
                + (self._count - 1)
                * self._delta_time  # type: ignore
            )
            if abs(t - exp) < 1e-9:
                return
            self._is_uniform = False
            return

        # check regained uniformity
        if not self._is_uniform and self._count >= 3:
            pairs = list(zip(
                self._times,
                self._values
            ))
            pairs.sort(key=lambda x: x[0])
            ts = [p[0] for p in pairs]
            vs = [p[1] for p in pairs]
            diffs = [
                ts[i+1] - ts[i]
                for i in range(len(ts)-1)
            ]
            d0 = diffs[0]
            if all(
                abs(d - d0) < 1e-9
                for d in diffs
            ):
                self._initial_time = ts[0]
                self._delta_time = d0
                self._values = array(
                    self._value_code,
                    vs
                )
                self._times = None
                self._count = len(vs)
                self._is_uniform = True

    def value(
        self,
        time: float
    ) -> Union[float, bool]:
        """
        Return value at time or KeyError.
        """
        t = float(time)
        if self._count == 0:
            raise KeyError(
                f"Time {t} out of range"
            )

        if (
            self._is_uniform
            and self._delta_time is not None
        ):
            idx = int(round(
                (t - self._initial_time)
                / self._delta_time  # type: ignore
            ))
            if 0 <= idx < self._count:
                exp = (
                    self._initial_time
                    + idx
                    * self._delta_time  # type: ignore
                )
                if abs(exp - t) < 1e-9:
                    val = self._values[idx]
                    return (
                        bool(val)
                        if self._dtype is bool
                        else val
                    )
            raise KeyError(
                f"Time {t} out of range"
            )

        # non-uniform lookup
        assert self._times
        for tt, vv in zip(
            self._times,
            self._values
        ):
            if abs(tt - t) < 1e-9:
                return (
                    bool(vv)
                    if self._dtype is bool
                    else vv
                )
        raise KeyError(
            f"Time {t} not found"
        )

    def update(
        self,
        time: float,
        value: Union[float, bool]
    ) -> None:
        """
        Update value at time or KeyError.
        """
        t = float(time)
        v = self._dtype(value)
        if self._count == 0:
            raise KeyError(
                f"Time {t} out of range"
            )

        if (
            self._is_uniform
            and self._delta_time is not None
        ):
            idx = int(round(
                (t - self._initial_time)
                / self._delta_time  # type: ignore
            ))
            if 0 <= idx < self._count:
                exp = (
                    self._initial_time
                    + idx
                    * self._delta_time  # type: ignore
                )
                if abs(exp - t) < 1e-9:
                    self._values[idx] = (
                        int(v)
                        if self._dtype is bool
                        else v
                    )
                    return
            raise KeyError(
                f"Time {t} out of range"
            )

        assert self._times
        for i, tt in enumerate(self._times):
            if abs(tt - t) < 1e-9:
                self._values[i] = (
                    int(v)
                    if self._dtype is bool
                    else v
                )
                return
        raise KeyError(
            f"Time {t} not found"
        )

    def drop(
        self,
        time: float
    ) -> None:
        """
        Remove entry at time or KeyError.
        """
        t = float(time)
        if self._count == 0:
            raise KeyError(
                f"Time {t} out of range"
            )

        if self._is_uniform:
            self._is_uniform = False
            self._times = array(
                self._time_code,
                [
                    self._initial_time  # type: ignore
                    + i
                    * self._delta_time  # type: ignore
                    for i in range(
                        self._count
                    )
                ]
            )

        assert self._times
        for i, tt in enumerate(self._times):
            if abs(tt - t) < 1e-9:
                self._times.pop(i)
                self._values.pop(i)
                self._count -= 1
                return
        raise KeyError(
            f"Time {t} not found"
        )

    def times(self) -> Iterable[float]:
        """Yield times."""
        if (
            self._is_uniform
            and self._delta_time is not None
        ):
            return (
                self._initial_time  # type: ignore
                + i
                * self._delta_time  # type: ignore
                for i in range(
                    self._count
                )
            )
        assert self._times
        return iter(self._times)

    def values(
        self
    ) -> Iterable[Union[float, bool]]:
        """Yield values."""
        return (
            bool(v)
            if self._dtype is bool
            else v
            for v in self._values  # type: ignore
        )

    def items(
        self
    ) -> Iterable[Tuple[float, Union[float, bool]]]:
        """Yield (time, value) tuples."""
        return zip(
            self.times(),
            self.values()
        )

    def time_is_uniform(
        self
    ) -> Tuple[bool, Optional[Dict[str, float]]]:
        """Return (is_uniform, params)."""
        if self._is_uniform:
            return True, {
                "initial_time":
                self._initial_time,  # type: ignore
                "delta_time":
                self._delta_time,     # type: ignore
                "count": self._count
            }
        return False, None

    def variable_type(self) -> str:
        """Return 'float' or 'boolean'."""
        return (
            "boolean"
            if self._dtype is bool
            else "float"
        )

    def statistics(self) -> Dict[str, Union[int, float, None]]:
        """
        Return basic stats: count, mean, std.
        """
        vals = list(self.values())
        n = len(vals)
        if n == 0:
            return {"count": 0, "mean": None, "std": None}
        mean = sum(vals) / n
        variance = sum((x - mean) ** 2 for x in vals) / n
        std = math.sqrt(variance)
        return {"count": n, "mean": mean, "std": std}

    def calibrate(
        self,
        other: 'TimeSeries'
    ) -> Dict[str, Union[int, float, None]]:
        """
        Compare this series with another over common times.
        Returns count, mean_self, mean_other, mean_error, rmse.
        """
        t1 = set(self.times())
        t2 = set(other.times())
        common = sorted(t1 & t2)
        n = len(common)
        if n == 0:
            return {
                "count": 0,
                "mean_self": None,
                "mean_other": None,
                "mean_error": None,
                "rmse": None
            }
        vals1 = [self.value(t) for t in common]
        vals2 = [other.value(t) for t in common]
        errors = [v1 - v2 for v1, v2 in zip(vals1, vals2)]
        mean1 = sum(vals1) / n
        mean2 = sum(vals2) / n
        mean_err = sum(errors) / n
        rmse = math.sqrt(sum(e * e for e in errors) / n)
        return {
            "count": n,
            "mean_self": mean1,
            "mean_other": mean2,
            "mean_error": mean_err,
            "rmse": rmse
        }

    def correlation(
        self,
        series_list: List['TimeSeries']
    ) -> Dict[Tuple[int, int], float]:
        """
        Compute Pearson correlation coefficients between each pair
        in the provided list of series.
        Returns a dict mapping (i,j) -> corr.
        """
        results: Dict[Tuple[int, int], float] = {}
        for i in range(len(series_list)):
            for j in range(i + 1, len(series_list)):
                s1 = series_list[i]
                s2 = series_list[j]
                t1 = set(s1.times())
                t2 = set(s2.times())
                common = t1 & t2
                n = len(common)
                if n == 0:
                    results[(i, j)] = float('nan')
                    continue
                vals1 = [s1.value(t) for t in common]
                vals2 = [s2.value(t) for t in common]
                m1 = sum(vals1) / n
                m2 = sum(vals2) / n
                num = sum((a - m1) * (b - m2) for a, b in zip(vals1, vals2))
                denom = math.sqrt(
                    sum((a - m1) ** 2 for a in vals1)
                    * sum((b - m2) ** 2 for b in vals2)
                )
                corr = num / denom if denom != 0 else float('nan')
                results[(i, j)] = corr
        return results

class DataContainer:
    """
    Store multiple TimeSeries indexed by element attributes and source.

    Keys: (element_type, element_id, variable, value_source).
    """

    def __init__(self) -> None:
        Key = Tuple[str, str, str, str]
        self._series: Dict[Key, TimeSeries] = {}
        self._units: Dict[Key, str] = {}

    def add(
        self,
        ts: TimeSeries,
        element_type: str,
        element_id: str,
        variable: str,
        value_source: str,
        units: str,
    ) -> None:
        """Add a TimeSeries under identifiers, storing its units."""
        key = (element_type, element_id, variable, value_source)
        self._series[key] = ts
        self._units[key] = units

    def get(
        self,
        element_type: str,
        element_id: str,
        variable: str,
        value_source: str,
    ) -> TimeSeries:
        """Return the TimeSeries for the given identifiers or KeyError."""
        key = (element_type, element_id, variable, value_source)
        try:
            return self._series[key]
        except KeyError:
            raise KeyError(f"No series for key {key}")

    def units(
        self,
        element_type: str,
        element_id: str,
        variable: str,
        value_source: str,
    ) -> str:
        """Return the units for the given identifiers or KeyError."""
        key = (element_type, element_id, variable, value_source)
        try:
            return self._units[key]
        except KeyError:
            raise KeyError(f"No units for key {key}")

    def drop(self, element_type: str, element_id: str) -> None:
        """Remove all series for given element_type and element_id."""
        to_del = [
            k for k in self._series
            if k[0] == element_type and k[1] == element_id
        ]
        for k in to_del:
            del self._series[k]
            del self._units[k]

    def element_types(self) -> Tuple[str, ...]:
        """Return defined element types."""
        return tuple(set(sorted({k[0] for k in self._series})))

    def element_ids(self, element_type: str) -> Tuple[str, ...]:
        """Return IDs for a given element_type."""
        return tuple(
            sorted(set(k[1] for k in self._series if k[0] == element_type))
        )

    def variables(self, element_type: str, element_id: str) -> Tuple[str, ...]:
        """Return variables for given element_type and element_id."""
        return tuple(
            sorted(
                set(
                    k[2]
                    for k in self._series
                    if k[0] == element_type and k[1] == element_id
                )
            )
        )

    def value_sources(
        self,
        element_type: str,
        element_id: str,
        variable: str
    ) -> Tuple[str, ...]:
        """Return value_source strings for a given series key."""
        return tuple(
            sorted(
                set(
                    k[3]
                    for k in self._series
                    if (k[0], k[1], k[2]) == (element_type, element_id, variable)
                )
            )
        )

    def count(self) -> int:
        """Return number of stored series."""
        return len(self._series)

    def total_points(self) -> int:
        """Return total number of data points across all series."""
        return sum(len(ts) for ts in self._series.values())

    def total_memory(self) -> int:
        """
        Return total memory usage in bytes:
        for each TimeSeries, sum array lengths × itemsize.
        """
        tb = 0
        for ts in self._series.values():
            # values array always present
            vals = ts._values  # type: ignore
            tb += len(vals) * vals.itemsize
            # times array only if non-uniform
            if ts._times is not None:
                times = ts._times  # type: ignore
                tb += len(times) * times.itemsize
        return tb
