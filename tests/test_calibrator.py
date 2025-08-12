import os
import pytest
from src.core.calibrator import OptimizationProblem, calibrate

# Directory where the test data files are located
TEST_DATA_DIR = os.path.dirname(__file__)

@pytest.fixture
def test_files():
    """Return absolute paths to the input and pressure observation data files."""
    return {
        "inp_file": os.path.join(TEST_DATA_DIR, "calibration_example.inp"),
        "pressure_file": os.path.join(TEST_DATA_DIR, "observed_pressure.dat"),
    }


def test_adjust_roughness(test_files):
    """
    Manual inspection test:
    Adjust the roughness of the model.
    """

    inp_fname = test_files["inp_file"]
    observed_data = { "pressure" : test_files["pressure_file"]}

    # Create an optimization problem
    op = OptimizationProblem(inp_fname, observed_data)
    op.set_bounds(0.001, 0.2)

    # Print results.
    print("-"*40)
    print("Cheking some values.")
    for x in [0.2, 0.1, .01, 0.001]:
        print(f"For roughness {x} fitness is {op.fitness(x)}")
    print('-'*40)
    print("Using solver.")
    print(calibrate(op))
    print("-"*40)
