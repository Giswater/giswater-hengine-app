import os
import time
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
    print("Checking some values.")
    for x in [0.2, 0.1, .01, 0.001]:
        print(f"For roughness {x} fitness is {op.fitness(x)}")
    print('-'*40)
    print("Using solver.")
    res = calibrate(op)
    print(f"X = {res.x} \nFitness: {res.fun}")
    print("-"*40)

    # Performance.
    time_counter = time.time()
    op_number = 5
    for i in range(op_number):
        calibrate(op)
    time_counter = time.time() - time_counter

    print(f"Number of solutions per second : {op_number/time_counter}")
