import os
import pytest
from src.core.comparer import Comparer

# Directory containing test .inp files
TEST_DATA_DIR = os.path.dirname(__file__)

@pytest.fixture
def sample_models():
    """Provide paths to two EPANET models with same configuration but different data."""
    return [
        os.path.join(TEST_DATA_DIR, "comparer_example_1.inp"),
        os.path.join(TEST_DATA_DIR, "comparer_example_2.inp"),
    ]

def test_comparer_basic_run(sample_models):
    """
    Run the comparer on two input files with minimal filtering.
    This is a smoke test to check that the comparison completes.
    """
    try:
        comp = Comparer(
            inp_files=sample_models,
            element_filter=None,
            id_filter=["J08", "Well", "Tank"],
            variable_filter=["pressure", "tank_volume", "quality", "head"]
            )
    except Exception as e:
        pytest.fail(f"Comparer failed to load data: {e}")

    try:
        comp.run()
    except Exception as e:
        pytest.fail(f"Comparer failed to run: {e}")