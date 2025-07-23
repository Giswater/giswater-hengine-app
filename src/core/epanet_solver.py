"""
Module for defining and executing EPANET simulations.

This module provides a high-level interface to configure and run hydraulic and
water quality analyses using the EPANET Toolkit.

Key components:
- ModelType: Enumeration of supported analysis types:
    * HYDRAULIC
    * AGE
    * TRACE
    * CHEMICAL

- Concentration units:
    * MGL – milligrams per liter (mg/L)
    * UGL – micrograms per liter (µg/L)

- ObservedVariables: Enum specifying variables used to modify demands and
  control element behavior during simulation steps.

- DistrictMeteredArea: Represents a demand management zone (DMA), allowing
  weighted distribution of inflows across network nodes.

- EpanetModel: Creates and configures a model instance for a single analysis type.

- EpanetSimulation: Orchestrates a complete simulation cycle, consisting of:
    1. One HYDRAULIC simulation (base model)
    2. Optional AGE analysis
    3. Zero or more TRACE analyses
    4. Optional CHEMICAL analysis

  The simulation class coordinates model execution and collects results from
  all configured analyses.
"""

from __future__ import annotations

import logging
from pathlib import Path
from enum import IntEnum, Enum
from typing import Dict, Optional
from epanet import toolkit as tk


class ModelType(IntEnum):
    HYDRAULIC = tk.NONE
    AGE = tk.AGE
    TRACE = tk.TRACE
    CHEMICAL = tk.CHEM

# Toolkit concentration units.
MGL = "mg/L"
UGL = "ug/L"

# Possible observed variables
class ObservedVariables(str, Enum):
    INFLOWS = "inflows"                   # ¿Flow?
    VALVE_STATES = "valve_states"
    VALVE_SETPOINTS = "valve_setpoints"
    PUMP_SPEEDS = "pump_speeds"
# Note: "tank_level" and "pressure" are not yet supported.

# Configure logger to write to "solver.log"
logging.basicConfig(
    filename="solver.log",               # name of the log file
    filemode='w',                        # overwrite
    level=logging.INFO,                  # minimum severity level to capture
    format="%(asctime)s %(levelname)s: %(message)s",  # format
    datefmt="%Y-%m-%d %H:%M:%S"          # datetime format
)

class DistrictMeteredArea:
    """
    A District Metered Area (DMA) with weighted nodes.

    Net initial demands are computed by distributing the DMA’s net outflow
    (inflow minus losses) to each node according to its weight.
    """

    def __init__(self) -> None:
        # Mapping of node IDs to their distribution weight
        self.nodes: Dict[str, float] = {}

    def add_node(self, node_id: str, weight: float) -> None:
        """
        Add a node to the DMA with its distribution weight.

        Args:
            node_id: Identifier for the EPANET node.
            weight: Positive weight value used for allocating demand.

        Raises:
            ValueError: If the weight is not positive.
        """
        if weight <= 0:
            msg = f"Weight for node '{node_id}' must be >=0, got {weight}."
            raise ValueError(msg)
        self.nodes[node_id] = weight

    def _total_weight(self) -> float:
        """
        Compute the sum of all node weights in this DMA.

        Returns:
            The total of all weights.
        """
        return sum(self.nodes.values())

    def compute_initial_demands(
        self,
        inflow: float,
        losses: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Distribute the DMA’s net outflow (inflow minus losses) among its nodes.

        Args:
            inflow: Total inflow to the DMA (must be ≥ 0).
            losses: Optional mapping of node IDs to their computed water losses.
                    If None or empty, no losses are subtracted.

        Returns:
            A dict mapping each node ID to its allocated initial demand.

        Raises:
            ValueError: If inflow is negative, total weight is zero,
                        or net outflow after losses is negative.
        """
        if inflow < 0:
            raise ValueError("`inflow` must be non-negative.")

        total_weight = self._total_weight()
        if total_weight == 0:
            raise ValueError("Total weight is zero; cannot allocate demands.")

        # Sum only the losses for nodes that belong to this DMA
        total_losses = 0.0
        if losses:
            for node_id, loss in losses.items():
                if node_id in self.nodes:
                    total_losses += loss

        net_outflow = inflow - total_losses
        if net_outflow < 0:
            raise ValueError(
                f"Net outflow is negative ({net_outflow}); "
                "ensure inflow ≥ sum of losses."
            )

        # Allocate net outflow in proportion to each node’s weight
        return {
            node_id: net_outflow * weight / total_weight
            for node_id, weight in self.nodes.items()
        }



class EpanetModel:
    """Create and configure an EPANET model clone for a single analysis type."""

    def __init__(
        self,
        base_inp: str | Path,
        model_type: ModelType,
        *,
        chemical_name: str = "",
        concentration_units: str = "",
        trace_node: str = ""
    ) -> None:
        original_path = Path(base_inp).expanduser().resolve()
        if not original_path.is_file():
            raise FileNotFoundError(original_path)

        self.model_type = model_type
        self.chemical_name = chemical_name
        self.concentration_units = concentration_units
        self.trace_node = trace_node

        # Determine output filename based on model type.
        stem, suffix = original_path.stem, original_path.suffix
        if model_type is ModelType.HYDRAULIC:
            out_name = f"{stem}_hydraulic{suffix}"
        elif model_type is ModelType.AGE:
            out_name = f"{stem}_age{suffix}"
        elif model_type is ModelType.TRACE:
            if not trace_node:
                raise ValueError("trace_node required for TRACE models")
            out_name = f"{stem}_trace_{trace_node}{suffix}"
        elif model_type is ModelType.CHEMICAL:
            if not chemical_name:
                raise ValueError("chemical_name required for CHEMICAL models")
            if concentration_units not in (MGL, UGL):
                raise ValueError(f"Invalid concentration_units: {concentration_units}")
            out_name = f"{stem}_{chemical_name}{suffix}"
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        # Open toolkit project and configure.
        self.handle = tk.createproject()
        rpt, binf = original_path.with_suffix('.rpt'), original_path.with_suffix('.bin')
        err = tk.open(self.handle, str(original_path), str(rpt), str(binf))
        if err:
            raise RuntimeError(f"Toolkit open error {err}")

        err = tk.setqualtype(
            self.handle,
            self.model_type,
            self.chemical_name,
            self.concentration_units,
            self.trace_node
        )
        if err:
            raise RuntimeError(f"Can't set quality type ({err})")

        # Save cloned .inp file.
        clone_path = original_path.with_name(out_name)
        err = tk.saveinpfile(self.handle, str(clone_path))
        if err:
            raise RuntimeError(f"Toolkit saveinpfile error {err}")
        self.inp_path = clone_path

    def close(self) -> None:
        """Release EPANET resources for this model."""
        try:
            tk.close(self.handle)
            tk.deleteproject(self.handle)
        except Exception:
            pass
        finally:
            self.handle = None
        logging.info("Model: '%s' closed.", self.inp_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class EpanetSimulation:
    """
    Encapsulates parallel EPANET simulations: one hydraulic run and multiple
    water-quality analyses.
    
    Args:
        base_inp (str | Path): Path to the base .inp file.
        enable_age (bool): Indicates whether AGE analysis is enabled.
        trace_nodes (list[str]): Node identifiers for TRACE analyses.
        chemical_name (str): Species name for the CHEMICAL analysis.
        concentration_units (str): Units for the CHEMICAL analysis.
        dmas (dict): Mapping of node IDs to dictionaries containing:
            - dma_id (str)
            - weight (float)
    
    Workflow:
        1. Perform the hydraulic calculation. If losses are defined, repeat:
           a. Assume losses equal to the previously calculated values or zero.
           b. Set initial demands.
           c. Execute one step and obtain new losses.
           d. If the difference between new and previous losses is within the
              tolerance, proceed; otherwise, update the previous losses and
              return to step b.
        2. Perform the water-quality calculations.
        3. Return the results.
    
    Time control:
        - model_time: seconds elapsed from 0 up to the simulation duration.
        - cycle_count: number of completed cycles.
        - current_time: model_time + duration * cycle_number
    
    Implemented methods:
        - current_time()
        - run_step()
        """

    def __init__(
        self,
        base_inp: str | Path,
        *,
        enable_age: bool = False,
        trace_nodes: list[str] | None = None,
        chemical_name: str = "",
        concentration_units: str = "",
        dmas: dict[str, str | None] | None = None,
        # Numeric tolerance when computing losses.
        tolerance: float = 1e-9
    ) -> None:

        # Start simulation.
        logging.info("START OF SIMULATION")

        # Create hydraulic model.
        self.hydraulic = EpanetModel(base_inp, ModelType.HYDRAULIC)
        logging.info("Hydraulic model defined.")

        # Store the collection of handles for the quality models.
        self.quality_handles = []

        # Retrieve simulation duration from INP
        self.duration = tk.gettimeparam(self.hydraulic.handle, tk.DURATION)
        self.hydraulic_step = tk.gettimeparam(self.hydraulic.handle, tk.HYDSTEP)
        self.quality_step = tk.gettimeparam(self.hydraulic.handle, tk.QUALSTEP)

        # Ensure quality step does not exceed hydraulic step
        if self.quality_step > self.hydraulic_step:
            raise ValueError(
                f"Quality step ({self.quality_step}) must be ≤ "
                f"hydraulic step ({self.hydraulic_step})."
            )

        # Ensure hydraulic step is a multiple of quality step
        if self.hydraulic_step % self.quality_step != 0:
            raise ValueError(
                f"Hydraulic step ({self.hydraulic_step}) must be a multiple of "
                f"quality step ({self.quality_step})."
            )
        logging.info("The simulation duration is %s s.", self.duration)

        # Open hydraulic model.
        tk.openH(self.hydraulic.handle)
        logging.info("Hydraulic model opened.")

        # Simulation timing
        self.model_time = 0
        self.cycle_count = 0

        # Optional single age model
        self.age: EpanetModel | None = None
        if enable_age:
            self.age = EpanetModel(base_inp, ModelType.AGE)
            tk.openH(self.age.handle)
            tk.openQ(self.age.handle)
            self.quality_handles.append(self.age.handle)
            logging.info("AGE model activated.")

        # Optional trace models
        self.traces: dict[str, EpanetModel] = {}
        for node in trace_nodes:
            self.traces[node] = EpanetModel(base_inp,
                                            ModelType.TRACE,
                                            trace_node=node
                                            )
            tk.openH(self.traces[node].handle)
            tk.openQ(self.traces[node].handle)
            self.quality_handles.append(self.traces[node].handle)
            logging.info('TRACE activated from node "%s".', node)

        # Optional single chemical model
        self.chemical: EpanetModel | None = None
        if chemical_name or concentration_units:
            if not (chemical_name and concentration_units):
                raise ValueError(
                    "Both chemical name and units required for CHEMICAL model."
                )
            self.chemical = EpanetModel(
                base_inp,
                ModelType.CHEMICAL,
                chemical_name=chemical_name,
                concentration_units=concentration_units
            )
            tk.openH(self.chemical.handle)
            tk.openQ(self.chemical.handle)
            # print("Modelo CHEMICAL abierto.")
            self.quality_handles.append(self.chemical.handle)
            logging.info('Tracing "%s". Units: "%s".', chemical_name, concentration_units)
        logging.info("%s quality models have been defined.", len(self.quality_handles))

        # Define DMAs.
        logging.info("MDAs definition.")
        self.dmas = {}
        for node_id, value in dmas.items():
            dma_id = value['dma_id']
            weight = value['weight']
            if dma_id not in self.dmas:
                self.dmas[dma_id] = DistrictMeteredArea()
                logging.info("New DMA created: %s.", dma_id)
            self.dmas[dma_id].add_node(node_id, weight)
            logging.info("Node added: %s with weight: %s to DMA: %s.", node_id, weight, dma_id)

        # Define calculate losses.
        self.calculated_losses = None
        self.tolerance = tolerance

        # Define calculate results.
        self.results = {}

        # End of initialization.
        msg = "Initialization complete. The simulation is ready to run."
        logging.info(msg)

    def current_time(self):
        """Returns the time in seconds since the start of the simulation."""
        return self.duration * self.cycle_count + self.model_time

    def _update(self, data_to_update: dict[str, dict]) -> None:
        """
        Update simulation model values from external observations or control inputs.
    
        Args:
            data_to_update: A dictionary where each key is an update type and
                            each value is a dictionary of element IDs to new values.
                            Supported keys:
                              - "inflows": dict[dma_id, float]
                              - "pipe_states": dict[pipe_id, 'OPEN' | 'CLOSED']
                              - "valve_setpoints": dict[valve_id, float]
                              - "pump_speeds": dict[pump_id, float]
    
        Raises:
            ValueError: If any update type is not supported.
        """
        for update_type, elements in data_to_update.items():
            if update_type not in (v.value for v in ObservedVariables):
                raise ValueError(f"Unsupported update type: '{update_type}'")
            match update_type:
                case 'inflows':
                    handle = self.hydraulic.handle
                    for dma_id, inflow in elements.items():
                        losses = self.calculated_losses
                        outflows = self.dmas[dma_id].compute_initial_demands(inflow, losses)
                        for node_id, value in outflows.items():
                            index = tk.getnodeindex(handle, node_id)
                            tk.setnodevalue(handle, index, tk.BASEDEMAND, value)
                        for handle in self.quality_handles:
                            tk.setnodevalue(handle, index, tk.BASEDEMAND, value)
                case 'valve_states':
                    for link_id, value in elements.items():
                        handle = self.hydraulic.handle
                        index = tk.getlinkindex(handle, link_id)
                        status = 1 if value == 'OPEN' else 0
                        tk.setlinkvalue(handle, index, tk.STATUS, status)
                        for handle in self.quality_handles:
                            tk.setlinkvalue(handle, index, tk.STATUS, status)
                case 'valve_setpoints':
                    for link_id, value in elements.items():
                        handle = self.hydraulic.handle
                        index = tk.getlinkindex(handle, link_id)
                        tk.setlinkvalue(handle, index, tk.SETTING, value)
                        for handle in self.quality_handles:
                            tk.setlinkvalue(handle, index, tk.SETTING, value)
                case 'pump_speeds':
                    for link_id, value in elements.items():
                        handle = self.hydraulic.handle
                        index = tk.getlinkindex(handle, link_id)
                        tk.setlinkvalue(handle, index, tk.SETTING, value)
                        for handle in self.quality_handles:
                            tk.setlinkvalue(handle, index, tk.SETTING, value)
        logging.info("Updated models.")

    def _compute_losses(self, handle) -> float:
        """
        Compute per-node losses and return the max error between
        previous and current loss values.
        """
        total_losses = 0
        exp = tk.getoption(handle, tk.EMITEXPON)
        # Initialize losses on first call
        if self.calculated_losses is None:
            self.calculated_losses = {}
            for dma in self.dmas.values():
                for node_id in dma.nodes:
                    idx = tk.getnodeindex(handle, node_id)
                    emitter = tk.getnodevalue(handle, idx, tk.EMITTER)
                    pressure = tk.getnodevalue(handle, idx, tk.PRESSURE)
                    loss = emitter * pressure**exp
                    total_losses += loss
                    self.calculated_losses[node_id] = loss
            return self.tolerance + 1.0
        # Compute new losses and track max error
        max_error = 0.0
        for node_id, prev_loss in self.calculated_losses.items():
            idx = tk.getnodeindex(handle, node_id)
            emitter = tk.getnodevalue(handle, idx, tk.EMITTER)
            pressure = tk.getnodevalue(handle, idx, tk.PRESSURE)
            loss = emitter * pressure**exp
            error = abs(loss - prev_loss)
            max_error = max(max_error, error)
            total_losses += loss
            self.calculated_losses[node_id] = loss

        logging.info("Computed losses: %s.", total_losses)

        return max_error

    def _get_hydraulic_results(self) -> dict[str, dict]:
        """
        Collects hydraulic results at the end of the simulation step.
    
        Returns a dict:
          {
            'junctions': {...},
            'reservoirs': {...},
            'tanks': {...},
            'pipes': {...},
            'valves': {...},
            'pumps': {...}
          }
        Each inner dict maps element ID to its computed values.
        """

        handle = self.hydraulic.handle

        # Nodes.
        junctions, reservoirs, tanks = {}, {}, {}
        node_count = tk.getcount(handle, tk.NODECOUNT)

        for index in range(1, node_count + 1):
            node_id = tk.getnodeid(handle, index)
            node_type = tk.getnodetype(handle, index)

            if node_type == tk.JUNCTION:
                junctions[node_id] = {
                    "demand": tk.getnodevalue(handle, index, tk.DEMAND),
                    "head": tk.getnodevalue(handle, index, tk.HEAD),
                    "pressure": tk.getnodevalue(handle, index, tk.PRESSURE),
                    "loss": self.calculated_losses.get(node_id, 0.0)
                }
            elif node_type == tk.RESERVOIR:
                reservoirs[node_id] = {
                    "inflow": tk.getnodevalue(handle, index, tk.DEMAND),
                    "head": tk.getnodevalue(handle, index, tk.HEAD)
                }
            elif node_type == tk.TANK:
                tanks[node_id] = {
                    "inflow": tk.getnodevalue(handle, index, tk.DEMAND),
                    "head": tk.getnodevalue(handle, index, tk.HEAD),
                    "pressure": tk.getnodevalue(handle, index, tk.PRESSURE)
                }

        self.results["junctions"] = junctions
        self.results["reservoirs"] = reservoirs
        self.results["tanks"] = tanks

        # Links.
        pipes, valves, pumps = {}, {}, {}
        link_count = tk.getcount(handle, tk.LINKCOUNT)

        for index in range(1, link_count + 1):
            link_id = tk.getlinkid(handle, index)
            link_type = tk.getlinktype(handle, index)

            if link_type == tk.PIPE:
                pipes[link_id] = {
                    "flow": tk.getlinkvalue(handle, index, tk.FLOW),
                    "velocity": tk.getlinkvalue(handle, index, tk.VELOCITY),
                    "headloss": tk.getlinkvalue(handle, index, tk.HEADLOSS)
                }
            elif link_type in (tk.PRV, tk.PSV, tk.PBV, tk.FCV, tk.TCV, tk.GPV):
                valves[link_id] = {
                    "flow": tk.getlinkvalue(handle, index, tk.FLOW),
                    "velocity": tk.getlinkvalue(handle, index, tk.VELOCITY),
                    "headloss": tk.getlinkvalue(handle, index, tk.HEADLOSS),
                    "status": tk.getlinkvalue(handle, index, tk.STATUS)
                }
            elif link_type == tk.PUMP:
                pumps[link_id] = {
                    "flow": tk.getlinkvalue(handle, index, tk.FLOW),
                    "status": tk.getlinkvalue(handle, index, tk.STATUS),
                    "energy": tk.getlinkvalue(handle, index, tk.ENERGY)
                }

        self.results["pipes"] = pipes
        self.results["valves"] = valves
        self.results["pumps"] = pumps

        logging.info("Hydraulic results stored.")

    def _add_quality_results(self):
        """Adds water quality results (AGE, TRACE, CHEMICAL) to hydraulic results."""

        def add_node_quality(node_id: str, target: dict):
            """Adds quality values for a given node."""
            if self.age:
                index = tk.getnodeindex(self.age.handle, node_id)
                target["age"] = tk.getnodevalue(self.age.handle, index, tk.QUALITY)
            for trace_id, trace in self.traces.items():
                index = tk.getnodeindex(trace.handle, node_id)
                target[f"trace_{trace_id}"] = tk.getnodevalue(trace.handle, index, tk.QUALITY)
            if self.chemical:
                index = tk.getnodeindex(self.chemical.handle, node_id)
                chem_name = self.chemical.chemical_name
                target[chem_name] = tk.getnodevalue(self.chemical.handle, index, tk.QUALITY)

        def add_link_quality(link_id: str, target: dict):
            """Adds quality values for a given link."""
            if self.age:
                index = tk.getlinkindex(self.age.handle, link_id)
                target["age"] = tk.getlinkvalue(self.age.handle, index, tk.QUALITY)
            for trace_id, trace in self.traces.items():
                index = tk.getlinkindex(trace.handle, link_id)
                target[f"trace_{trace_id}"] = tk.getlinkvalue(trace.handle, index, tk.QUALITY)
            if self.chemical:
                index = tk.getlinkindex(self.chemical.handle, link_id)
                chem_name = self.chemical.chemical_name
                target[chem_name] = tk.getlinkvalue(self.chemical.handle, index, tk.QUALITY)

        # Add quality to nodes
        for type_element in ["junctions", "reservoirs", "tanks"]:
            for node_id, variables in self.results.get(type_element, {}).items():
                add_node_quality(node_id, variables)

        # Add quality to links
        for type_element in ["pipes", "valves", "pumps"]:
            for link_id, variables in self.results.get(type_element, {}).items():
                add_link_quality(link_id, variables)

        logging.info("Water quality results added to hydraulic results.")

    def run_step(self, data_update) -> None:
        """
        Execute one simulation timestep: hydraulic then quality models.
        """
        logging.info("RUN SIMULATION STEP.")
        msg = f"Current time {self.current_time()} s. "
        msg += f"Model time: {self.model_time} s. "
        msg += f"Cycle count: {self.cycle_count}."
        logging.info(msg)

        # At the start of each simulation cycle, reset models.
        if self.model_time == 0:
            tk.initH(self.hydraulic.handle, 00)
            msg = "Model reinitialized [H"
            for handle in self.quality_handles:
                tk.initH(handle, 00)
                tk.initQ(handle, 00)
                msg += "Q"
            msg += "]"
            logging.info(msg)

        # Compute hydraulic.
        logging.info("Solving the hydraulic model...")

        # Solves iteratively until the loss error is within acceptable limits.
        loss_loop_count = 0
        while True:
            loss_loop_count += 1
            logging.info("Loss loop count: %s.", loss_loop_count)

            # Updates demands and configurations.
            self._update(data_update)

            # Solves the calculation step.
            handle = self.hydraulic.handle
            time_h = tk.runH(handle)
            error = self._compute_losses(handle)
            logging.info("Maximum error in loss calculation: %s.", error)
            if error < self.tolerance:
                break

        # Stores hydraulic results
        self._get_hydraulic_results()

        # Advances to the next cycle. If time_h == duration, initializes.
        if time_h == self.duration:
            self.model_time = 0
            self.cycle_count += 1
        else:
            next_h = tk.nextH(handle)
            self.model_time += next_h

        # Compute quality.
        logging.info("Solving the quality models...")
        for handle in self.quality_handles:
            # Computes hydraulic model.
            time_h = tk.runH(handle)
            # Computes qality models.
            while True:
                time_q = tk.runQ(handle)
                tk.nextQ(handle)
                if time_q == time_h:
                    break
            # Advances to the next hydraulic event.
            if time_h < self.duration:
                tk.nextH(handle)

        # Adds quality results.
        self._add_quality_results()

    def close(self) -> None:
        """Close all underlying models."""
        self.hydraulic.close()
        if self.age:
            self.age.close()
        for m in self.traces.values():
            m.close()
        if self.chemical:
            self.chemical.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


if __name__ == "__main__":
    # Path for tests
    file = "D:/Documentos/Repositorio/solver/tests/example.inp"
    sim = EpanetSimulation(
        file,
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
    print("Time", "Value")
    while counter:
        counter -=1
        sim.run_step(data_to_update)
        time = sim.current_time()
        variable = sim.results['junctions']["J08"]["loss"]
        # variable = sim.results['pumps']["Pump"]["energy"]
        print(f"{time } {variable:.6f}")
    sim.close()
