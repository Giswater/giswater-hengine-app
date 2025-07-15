from __future__ import annotations
"""
data_container.py

Defines DataContainer for storing time-series simulation results
organized by scenario, element type, element ID, and variable.
Enforces fixed interval between consecutive entries per scenario.
Uses efficient storage: flat arrays for floats and bit arrays for status.
Provides utility methods for metadata access.
Includes integrated unit tests when run as main.
"""

from collections import deque, defaultdict
from datetime import datetime, timedelta
from array import array


class DataContainer:
    def __init__(
        self,
        interval: timedelta,
    ):
        """
        Init container for simulation results.

        Args:
            interval: Required interval between consecutive timestamps per scenario.
        """
        self.interval = interval
        # storage per scenario
        self._data: dict[str, deque[tuple[datetime, dict]]] = defaultdict(deque)
        # schema per scenario
        self._schema: dict[str, dict[str, dict[str, set[str]]]] = {}
        # efficient storage indexes and data per scenario
        self._float_index: dict[str, dict[tuple[str, str, str], int]] = {}
        self._status_index: dict[str, dict[tuple[str, str, str], int]] = {}
        self._float_data: dict[str, deque[array]] = defaultdict(deque)
        self._status_data: dict[str, deque[array]] = defaultdict(deque)

    def add(
        self,
        timestamp: datetime,
        *args,
    ) -> None:
        """Store results for a scenario at given timestamp.

        Usage:
            add(timestamp, results)
            add(timestamp, scenario, results)

        If no scenario name is provided, uses 'default'.

        Args:
            timestamp: datetime for this data point.
            scenario: Optional scenario name to store data under (default 'default').
            results: Nested dict of element_type -> element_id -> var -> value.
        """
        # unpack args
        if len(args) == 1:
            scenario = 'default'
            results = args[0]
        elif len(args) == 2:
            scenario, results = args
        else:
            raise TypeError(f"add() takes 2 or 3 positional arguments but {1 + len(args)} were given")

        dq = self._data[scenario]
        if dq:
            expected = dq[-1][0] + self.interval
            if timestamp != expected:
                raise ValueError(
                    f"{scenario}: expected timestamp {expected.isoformat()}, got {timestamp.isoformat()}"
                )
        # schema capture or validation per scenario
        if scenario not in self._schema:
            schema = {
                etype: {eid: set(vars.keys()) for eid, vars in elems.items()}
                for etype, elems in results.items()
            }
            self._schema[scenario] = schema
            fidx, sidx = {}, {}
            fcount = scount = 0
            for etype, elems in sorted(schema.items()):
                for eid, vars in sorted(elems.items()):
                    for var in sorted(vars):
                        key = (etype, eid, var)
                        val = results[etype][eid][var]
                        if isinstance(val, str):
                            sidx[key] = scount
                            scount += 1
                        else:
                            fidx[key] = fcount
                            fcount += 1
            self._float_index[scenario] = fidx
            self._status_index[scenario] = sidx
        else:
            schema = self._schema[scenario]
            if set(results.keys()) != set(schema.keys()):
                raise ValueError(f"{scenario}: element types mismatch schema")
            for etype, elems in results.items():
                if set(elems.keys()) != set(schema[etype].keys()):
                    raise ValueError(f"{scenario}:{etype}: IDs mismatch schema")
                for eid, vars in elems.items():
                    if set(vars.keys()) != schema[etype][eid]:
                        raise ValueError(f"{scenario}:{etype}:{eid}: vars mismatch schema")
        dq.append((timestamp, results))
        # pack into efficient arrays
        fidx = self._float_index[scenario]
        sidx = self._status_index[scenario]
        floats = array('d', [0.0] * len(fidx))
        statuses = array('B', [0] * len(sidx))
        for (etype, eid, var), idx in fidx.items():
            floats[idx] = results[etype][eid][var]
        for (etype, eid, var), idx in sidx.items():
            statuses[idx] = 1 if results[etype][eid][var] == 'OPEN' else 0
        self._float_data[scenario].append(floats)
        self._status_data[scenario].append(statuses)

    def get(
        self,
        scenarios: list[str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        element_types: list[str] = None,
        element_ids: list[str] = None,
        variables: list[str] = None,
    ) -> dict[str, dict[str, dict[str, dict[str, float|str]]]]:
        """Query stored data with optional filters across scenarios.

        Args:
            scenarios: list of scenario names to include (default all)
            start_time: datetime start (inclusive)
            end_time: datetime end (exclusive)
            element_types: list of element types to include
            element_ids: list of element IDs to include
            variables: list of variable names to include
        Returns:
            Nested dict: {scenario: {timestamp_iso: {etype: {eid: {var: value}}}}}
        """
        out: dict[str, dict[str, dict]] = {}
        target_scenarios = scenarios or list(self._data.keys())
        for sc in target_scenarios:
            if sc not in self._data:
                continue
            sc_dict: dict[str, dict] = {}
            dq = self._data[sc]
            # filter element_ids by types if both provided
            if element_types and element_ids is not None:
                schema_sc = self._schema.get(sc, {})
                filtered = []
                for et in element_types:
                    filtered.extend(eid for eid in schema_sc.get(et, {}) if eid in element_ids)
                element_ids = filtered

            fidx = self._float_index.get(sc, {})
            sidx = self._status_index.get(sc, {})
            for (ts, _), floats, statuses in zip(
                dq,
                self._float_data.get(sc, []),
                self._status_data.get(sc, []),
            ):
                if start_time and ts < start_time:
                    continue
                if end_time and ts >= end_time:
                    continue
                ts_data: dict[str, dict] = {}
                # floats
                for (etype, eid, var), idx in fidx.items():
                    if element_types and etype not in element_types:
                        continue
                    if element_ids and eid not in element_ids:
                        continue
                    if variables and var not in variables:
                        continue
                    ts_data.setdefault(etype, {}).setdefault(eid, {})[var] = floats[idx]
                # statuses
                for (etype, eid, var), idx in sidx.items():
                    if element_types and etype not in element_types:
                        continue
                    if element_ids and eid not in element_ids:
                        continue
                    if variables and var not in variables:
                        continue
                    ts_data.setdefault(etype, {}).setdefault(eid, {})[var] = (
                        'OPEN' if statuses[idx] == 1 else 'CLOSED'
                    )
                if ts_data:
                    sc_dict[ts.isoformat()] = ts_data
            if sc_dict:
                out[sc] = sc_dict
        return out

    def get_start_timestamp(self) -> datetime | None:
        """Return the earliest timestamp across all scenarios."""
        all_ts = [dq[0][0] for dq in self._data.values() if dq]
        return min(all_ts) if all_ts else None

    def get_end_timestamp(self) -> datetime | None:
        """Return the latest timestamp across all scenarios."""
        all_ts = [dq[-1][0] for dq in self._data.values() if dq]
        return max(all_ts) if all_ts else None

    def get_time_count(self) -> int:
        """Return number of timestamps (assumed uniform)."""
        for dq in self._data.values():
            return len(dq)
        return 0

    def get_num_scenarios(self) -> int:
        """Return count of scenarios with data."""
        return len(self._data)

    def get_element_counts(self, scenario: str) -> dict[str, int]:
        """Return mapping of element_type to element count for a specific scenario."""
        schema = self._schema.get(scenario, {})
        return {etype: len(eids) for etype, eids in schema.items()}

    def get_variables(self, element_type: str) -> list[str]:
        """Return sorted list of variable names for a given element_type (assumes uniform)."""
        for schema in self._schema.values():
            elems = schema.get(element_type, {})
            return sorted(next(iter(elems.values()))) if elems else []
        return []

    def get_scenarios(self) -> list[str]:
        """Return list of scenario names."""
        return list(self._data.keys())


# Integrated tests
if __name__ == '__main__':
    import unittest
    from datetime import datetime, timedelta

    class TestDataContainer(unittest.TestCase):
        def setUp(self):
            self.interval = timedelta(minutes=15)
            self.start = datetime(2025, 7, 11, 0, 0)
            counts = {'junction': 2, 'reservoir': 1}
            self.scenarios = ['base', 'alt']
            def make_sample(i):
                sample = {}
                status_str = 'OPEN' if i % 2 == 0 else 'CLOSED'
                for etype, cnt in counts.items():
                    sample[etype] = {}
                    for idx in range(1, cnt+1):
                        eid = f"{etype}{idx}"
                        sample[etype][eid] = {'value': float(i), 'status': status_str}
                return sample
            total = 4
            self.timestamps = [self.start + n*self.interval for n in range(total)]
            self.samples = [make_sample(n) for n in range(total)]

        def test_add_and_default(self):
            dc = DataContainer(interval=self.interval)
            for ts, sample in zip(self.timestamps, self.samples):
                dc.add(ts, sample)
            self.assertIn('default', dc.get_scenarios())
            self.assertEqual(len(dc.get_scenarios()), 1)

        def test_get_filters(self):
            dc = DataContainer(interval=self.interval)
            for sc in self.scenarios:
                for ts, sample in zip(self.timestamps, self.samples):
                    dc.add(ts, sc, sample)
            # time filter
            res = dc.get(start_time=self.timestamps[1], end_time=self.timestamps[3])
            for sc, data in res.items():
                for ts in data:
                    self.assertGreaterEqual(datetime.fromisoformat(ts), self.timestamps[1])
                    self.assertLess(datetime.fromisoformat(ts), self.timestamps[3])
            # scenario filter
            only_base = dc.get(scenarios=['base'])
            self.assertListEqual(list(only_base.keys()), ['base'])
            # element and id filter
            vals = dc.get(element_types=['junction'], element_ids=['junction1'], variables=['value'])
            for sc, data in vals.items():
                for _, ets in data.items():
                    self.assertIn('junction', ets)
                    self.assertIn('junction1', ets['junction'])

    unittest.main()
