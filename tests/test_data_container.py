import pytest
from src.core.data_container import TimeSeries, DataContainer


def test_timeseries():
    ts = TimeSeries()
    ts.add(0, 0.0)
    ts.add(15, 1.0)
    ts.add(30, 1.1)
    assert len(ts) == 3
    is_u, params = ts.time_is_uniform()
    assert is_u is True
    assert params == {'initial_time': 0.0, 'delta_time': 15.0, 'count': 3}
    assert ts.value(0) == 0.0
    assert ts.value(15) == 1.0
    assert ts.value(30) == 1.1


def test_renormalize():
    ts = TimeSeries()
    ts.add(0, 0.0)
    ts.add(15, 1.0)
    ts.add(45, 1.1)
    is_u, params = ts.time_is_uniform()
    assert is_u is False
    ts.add(30, 1.1)
    is_u, params = ts.time_is_uniform()
    assert is_u is True
    assert params == {'initial_time': 0.0, 'delta_time': 15.0, 'count': 4}
    assert ts.value(30) == 1.1


def test_duplicate_time_error():
    ts = TimeSeries()
    ts.add(0, 1.0)
    with pytest.raises(ValueError):
        ts.add(0, 2.0)


def test_datacontainer_basic():
    ts1 = TimeSeries()
    ts1.add(0, 1.0)
    ts1.add(1, 2.0)
    ts2 = TimeSeries()
    ts2.add(0, 1.1)
    ts2.add(1, 1.9)
    dc = DataContainer()
    dc.add(ts1, 'node', 'n1', 'head', 'obs', 'm')
    dc.add(ts2, 'node', 'n1', 'pressure', 'calc', 'm.c.a.')
    assert dc.element_types() == ('node',)
    assert dc.element_ids('node') == ('n1',)
    assert dc.variables('node', 'n1') == ('head', 'pressure')
    assert dc.value_sources('node', 'n1', 'head') == ('obs',)
    assert dc.get('node', 'n1', 'head', 'obs') is ts1
    assert dc.units('node', 'n1', 'head', 'obs') == 'm'


def test_datacontainer_drop_and_totals():
    ts1 = TimeSeries()
    ts1.add(0, 1.0)
    ts2 = TimeSeries()
    ts2.add(0, 3.0)
    dc = DataContainer()
    dc.add(ts1, 'et', 'eid', 'v1', 'main', 'u1')
    dc.add(ts2, 'et', 'eid', 'v2', 'main', 'u2')
    assert dc.total_points() == 2
    mem = dc.total_memory()
    assert isinstance(mem, int) and mem > 0
    dc.drop('et', 'eid')
    with pytest.raises(KeyError):
        dc.get('et', 'eid', 'v1', 'main')
