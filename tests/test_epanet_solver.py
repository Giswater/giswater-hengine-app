import os
import pytest

from src.core.epanet_solver import EpanetSimulation, MGL

# Directory where the test data files are located
TEST_DATA_DIR = os.path.dirname(__file__)

@pytest.fixture
def test_file():
    """Return absolute paths to the inp file."""
    return os.path.join(TEST_DATA_DIR, "example.inp")

def test_epanet_solver(test_file):
    # Path for tests
    sim = EpanetSimulation(
        test_file,
        enable_age=True,
        trace_nodes=["Well", "Spring"],
        chemical_name="FC",
        concentration_units=MGL,
        dmas = {'J07': {'dma_id': 'Sector_1', 'weight': 0.75  },
                'J08': {'dma_id': 'Sector_1', 'weight': 0.25  },
                'J09': {'dma_id': 'Sector_2', 'weight': 0.50},
                'J10': {'dma_id': 'Sector_2', 'weight': 0.50 }}
    )
    data_to_update = {'inflows' : {'Sector_1': 5.0, 'Sector_2': 6.0},
                      'valve_states': {'C01': 'OPEN', 'C04': 'CLOSED'},
                      'valve_setpoints': {'FCV': 0.0},
                      'pump_speeds': {'Pump': 1.0}
    }
    # Print a simulation
    counter = 300
    print("\n Time", "Value")
    print("-"*20)
    while counter:
        counter -=1
        sim.run_step(data_to_update)
        time = sim.current_time()
        variable = sim.results['junctions']["J08"]["loss"]
        # variable = sim.results['pumps']["Pump"]["energy"]
        print(f"{time } {variable:.6f}")
    sim.close()
