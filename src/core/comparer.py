"""
comparer.py
"""

from __future__ import annotations

from typing import List
from epanet import toolkit as tk

# Map EPANET element types to toolkit variables
VARIABLE_MAP: dict[str, dict[str, int]] = {
    'JUNCTIONS': {
        'demand': tk.DEMAND,
        'head': tk.HEAD,
        'pressure': tk.PRESSURE,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'RESERVOIRS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'TANKS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        'tank_level': tk.TANKLEVEL,
        'tank_volume' : tk.TANKVOLUME,
        'quality': tk.QUALITY,
        'source_mass': tk.SOURCEMASS
    },
    'PIPES': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'headloss': tk.HEADLOSS,
        'status': tk.STATUS,
        # Link status can be:
        # CLOSED = 0
        # OPEN = 1
        # 'quality' : tk.LINKQUAL
    },
    'VALVES': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'headloss': tk.HEADLOSS,
        'status': tk.STATUS
        # See PIPES
    },
    'PUMPS': {
        'flow': tk.FLOW,
        'velocity': tk.VELOCITY,
        'head': tk.HEAD,
        'energy': tk.ENERGY,
        'pump_efficiency' : tk.PUMP_EFFIC,
        'pump_state': tk.PUMP_STATE
        # Pump state can be:
        # PUMP_XHEAD   = 0,  //!< Pump closed - cannot supply head
        # PUMP_CLOSED  = 2,  //!< Pump closed
        # PUMP_OPEN    = 3,  //!< Pump open
        # PUMP_XFLOW   = 5   //!< Pump open - cannot supply flow
    },
}


class Comparer:
    """
    Compare EPANET simulation outputs between two network input files.
    """

    def __init__(
        self,
        inp_files: List,
        element_filter: List| None = None,
        id_filter: List| None = None,
        variable_filter: List| None = None
    ):
        """
        Initialize the Comparer with two network input paths and optional
        report/binary file names.

        Args:
            inp_files: List with path to  EPANET .inp files to compare.
            element_filter
            id_filter
            variable_filter
        """
        assert len(inp_files) > 1, "Almost 2 files should be compared!"
        self.inp_files = inp_files
        self._handles = []
        self.element_filter = element_filter
        self.id_filter = id_filter
        self.variable_filter = variable_filter

    def _open(self, inp: str) -> int:
        """
        Create and open an EPANET project file.

        Returns:
            handle: Integer project handle for EPANET toolkit operations.
        """
        handle = tk.createproject()
        tk.open(handle, inp, inp.replace('.inp', '.rep'), '')
        return handle

    def _close(self, handle: int) -> None:
        """
        Close a previously opened EPANET project handle.
        """
        tk.close(handle)
        tk.deleteproject(handle)
        

    def _check_consistency(self) -> None:
        """
        Verify that both models use identical simulation settings:
        - Flow units
        - Headloss formula
        - Time parameters (duration, hydro step, quality step)
        - Quality analysis type
        """
        # 1. Compare flow units.
        base_fu = tk.getflowunits(self._handles[0])
        for h in self._handles[1:]:
            fu = tk.getflowunits(h)
            if fu != base_fu:
                raise RuntimeError(f"Flow units differ: {base_fu} vs {fu}")
        
        # 2. Compare headloss formula.
        base_hl = tk.getoption(self._handles[0], tk.HEADLOSSFORM)
        for h in self._handles[1:]:
            hl = tk.getoption(h, tk.HEADLOSSFORM)
            if hl != base_hl:
                raise RuntimeError(f"Headloss formula differs: {base_hl} vs {hl}")

        # 3. Compare key time parameters.
        params = {
            'DURATION': tk.DURATION,
            'HYDSTEP':  tk.HYDSTEP,
            'QUALSTEP': tk.QUALSTEP,
        }
        for name, code in params.items():
            base_val = tk.gettimeparam(self._handles[0], code)
            for h in self._handles[1:]:
                val = tk.gettimeparam(h, code)
                if val != base_val:
                    raise RuntimeError(
                        f"Time parameter {name} differs: {base_val} vs {val}"
                    )
    
        # 4. Compare quality analysis type.
        base_qt, _ = tk.getqualtype(self._handles[0])
        for h in self._handles[1:]:
            qt, _ = tk.getqualtype(h)
            if qt != base_qt:
                raise RuntimeError(
                    f"Quality analysis type differs: {base_qt} vs {qt}"
                )

    def _collect(self, handles, element_ids, element_type, variable_filter) -> None:
        def _is_node(element_type):
            if element_type in ["JUNCTIONS", "RESERVOIRS", "TANKS"]:
                return True
            return False
        
        for element_id in element_ids:
            print("+"*30)
            print(element_type, ":", element_id)
            model_index = 0
            for handle in handles:
                model_index += 1
                print("> Model #", model_index)
                if _is_node(element_type):
                    index = tk.getnodeindex(handle, element_id)
                else:
                    index = tk.getlinkindex(handle, element_id)
                for variable, code in VARIABLE_MAP[element_type].items():
                    if variable_filter is None or variable in variable_filter:
                        if _is_node(element_type):
                            value = tk.getnodevalue(handle, index, code)
                        else:
                            value = tk.getlinkvalue(handle, index, code)
                        print(">>", variable, "=", value)        

    def run(self):
        # Open proyect handles
        check = len(self.inp_files) == len(set(self.inp_files))
        assert check, "Files should be different!"
        for inp_file in self.inp_files:
            handle =  self._open(inp_file)
            self._handles.append(handle)

        # Check consistency between models.
        self._check_consistency()
        
        # Filtering.
        junctions, reservoirs, tanks = [], [], []
        node_count = tk.getcount(self._handles[0], tk.NODECOUNT)
        print("Node count:", node_count)
        for nindex in range(1, node_count + 1):
            element_id = tk.getnodeid(self._handles[0], nindex)
            node_type = tk.getnodetype(self._handles[0], nindex)
            match node_type:
                case tk.JUNCTION:
                    if self.element_filter is None or 'JUNCTIONS' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            junctions.append(element_id)
                            print('Add JUNCTION: ', element_id)
                case tk.RESERVOIR:
                    if self.element_filter is None or 'RESERVOIRS' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            reservoirs.append(element_id)
                            print('Add RESERVOIR: ', element_id)
                case tk.TANK:
                    if self.element_filter is None or 'TANKS' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            tanks.append(element_id)
                            print('Add TANK: ', element_id)            
        pipes, valves, pumps = [], [], []
        link_count = tk.getcount(self._handles[0], tk.LINKCOUNT)
        print("Link count:", link_count)
        for lindex in range(1, link_count + 1):
            element_id = tk.getlinkid(self._handles[0], lindex)
            link_type = tk.getlinktype(self._handles[0], lindex)
            match link_type:
                case tk.PIPE:
                    if self.element_filter is None or 'PIPES' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            pipes.append(element_id)
                            print('Add PIPE: ', element_id)
                case tk.PUMP:
                    if self.element_filter is None or 'PUMPS' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            pumps.append(element_id)
                            print('Add PUMP: ', element_id)   
                case _:
                    if self.element_filter is None or 'VALVES' in self.element_filter:
                        if self.id_filter is None or element_id in self.id_filter:
                            valves.append(element_id)
                            print('Add VALVE: ', element_id)
        
        # Get results
        duration = tk.gettimeparam(self._handles[0], tk.DURATION)
        print("Model duration =", duration)
        quality_analysis_type, _ = tk.getqualtype(self._handles[0])
        print("Quality Analysis =", quality_analysis_type != tk.NONE)
        
     
        # Start Hydraulic analysis.
        for handle in self._handles:
            tk.openH(handle)
            tk.initH(handle, 00)
       
        # Start quality analysisis.
        if quality_analysis_type != tk.NONE: 
             for handle in self._handles:
                 tk.openQ(handle)
                 tk.initQ(handle, 00)
        
        # Solve loop.
        loop_count = 0
        print("*"*30)
        while True:
            loop_count += 1
            print("Loop count =", loop_count)
            
            # Run hydraulic step.
            time_h = tk.runH(self._handles[0])
            print("Time hydraulic =", time_h)
            for handle in self._handles[1:]:
                time_h2 = tk.runH(handle)
                assert time_h == time_h2, "Error!"
                
            # Computes qality models.
            if quality_analysis_type != tk.NONE:
                model_index = 0
                for handle in self._handles:
                    model_index += 1
                    while True:
                        time_q = tk.runQ(handle)
                        tk.nextQ(handle)
                        if time_q == time_h:
                            break
                print("Time quality =", time_q)
            
            # Store results.
            self._collect(self._handles, junctions, "JUNCTIONS", self.variable_filter)
            self._collect(self._handles, reservoirs, "RESERVOIRS", self.variable_filter)
            self._collect(self._handles, tanks, "TANKS", self.variable_filter)                
            self._collect(self._handles, pipes, "PIPES", self.variable_filter)
            self._collect(self._handles, valves, "VALVES", self.variable_filter)
            self._collect(self._handles, pumps, "PUMPS", self.variable_filter)
            
            # Advance time.
            next_h = tk.nextH(self._handles[0])
            for handle in self._handles[1:]:
                next_h2 = tk.nextH(handle)
                assert next_h == next_h2, "Error!"
            print("*"*30)
            
            # End of loop.
            if next_h == 0:
                break    

        # Close project handles
        for handle in self._handles:
            self._close(handle)
