import os
import pytest
from src.core.calibrator import Calibration

# Directory where the test data files are located
TEST_DATA_DIR = os.path.dirname(__file__)

@pytest.fixture
def test_files():
    """Return absolute paths to the input and pressure observation data files."""
    return {
        "inp_file": os.path.join(TEST_DATA_DIR, "calibration_example.inp"),
        "pressure_file": os.path.join(TEST_DATA_DIR, "observed_pressure.dat"),
    }

def test_print_first_pressure_values(test_files):
    """
    Manual inspection test:
    Prints the first five (time, observed, simulated) entries for each element.
    """
    inp_file = test_files["inp_file"]
    obs_file = test_files["pressure_file"]

    # Initialize the calibration using observation data
    try:
        calib = Calibration(inp_file, pressure=obs_file)
    except Exception as e:
        pytest.fail(f"Calibrator cannot load data: {e}")
    
    # Display a preview of the loaded pressure data
    pressure_data = calib.variables.get("pressure")

    for elem, series in pressure_data.elements.items():
        print(f"{elem}: {series[:5]}")
