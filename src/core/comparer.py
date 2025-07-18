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
        # 'quality': tk.QUALITY,
        # 'source_mass': tk.SOURCEMASS
    },
    'RESERVOIRS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        # 'quality': tk.QUALITY,
        # 'source_mass': tk.SOURCEMASS
    },
    'TANKS': {
        'inflow': tk.DEMAND,
        'elevation': tk.HEAD,
        'tank_level': tk.TANKLEVEL,
        'tank_volume' : tk.TANKVOLUME,
        # 'quality': tk.QUALITY,
        # 'source_mass': tk.SOURCEMASS
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
        'head': tk.HEADLOSS,
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
        inp1: str,
        inp2: str,
        element_filter: List| None = None,
        id_filter: List| None = None,
        variable_filter: List| None = None
    ):
        """
        Initialize the Comparer with two network input paths and optional
        report/binary file names.

        Args:
            inp1: Path to first EPANET .inp file.
            inp2: Path to second EPANET .inp file.
            rpt: Optional report file name for both runs.
            out: Optional binary output file name for both runs.
        """
        self.inp1 = inp1
        self.inp2 = inp2
        self._handle1: int | None = None
        self._handle2: int | None = None
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
        

    def _check_consistency(self):
        # Check flow units.
        fu1 = tk.getflowunits(self._handle1)
        fu2 = tk.getflowunits(self._handle2)
        assert fu1 == fu2, "Flow units are different!"
        # Check headloss form.
        hl1 = tk.getoption(self._handle1, tk.HEADLOSSFORM)
        hl2 = tk.getoption(self._handle2, tk.HEADLOSSFORM)
        assert hl1 == hl2, "Headloss forms are different!"
        for param in [tk.DURATION, tk.HYDSTEP, tk.QUALSTEP]:
            t_p1 = tk.gettimeparam(self._handle1, param)
            t_p2 = tk.gettimeparam(self._handle2, param)
            assert t_p1 == t_p2, "Time paramenters are different!"
        # Check quality type analysis.
        qa1 = tk.getqualtype(self._handle1)
        qa2 = tk.getqualtype(self._handle2)
        assert qa1 == qa2, "Type analysis are different!"
        
    def run(self):
        # Open proyect handles
        assert self.inp1 != self.inp2, "Files should be different!"
        self._handle1 = self._open(self.inp1)
        self._handle2 = self._open(self.inp2)

        # Check consistency between models.
        self._check_consistency()
        
        # Filtering.
        junctions, reservoirs, tanks = [], [], []
        node_count = tk.getcount(self._handle1, tk.NODECOUNT)
        print("Node count:", node_count)
        for nindex in range(1, node_count + 1):
            node_id = tk.getnodeid(self._handle1, nindex)
            node_type = tk.getnodetype(self._handle1, nindex)
            match node_type:
                case tk.JUNCTION:
                    if self.element_filter is None or 'JUNCTIONS' in self.element_filter:
                        if self.id_filter is None or node_id in self.id_filter:
                            junctions.append(node_id)
                            print('Add JUNCTION: ', node_id)
                case tk.RESERVOIR:
                    if self.element_filter is None or 'RESERVOIRS' in self.element_filter:
                        if self.id_filter is None or node_id in self.id_filter:
                            reservoirs.append(node_id)
                            print('Add RESERVOIR: ', node_id)
                case tk.TANK:
                    if self.element_filter is None or 'TANKS' in self.element_filter:
                        if self.id_filter is None or node_id in self.id_filter:
                            tanks.append(node_id)
                            print('Add TANK: ', node_id)            
        pipes, valves, pumps = [], [], []
        link_count = tk.getcount(self._handle1, tk.LINKCOUNT)
        print("Link count:", link_count)
        for lindex in range(1, link_count + 1):
            link_id = tk.getlinkid(self._handle1, lindex)
            link_type = tk.getlinktype(self._handle1, lindex)
            match link_type:
                case tk.PIPE:
                    if self.element_filter is None or 'PIPES' in self.element_filter:
                        if self.id_filter is None or link_id in self.id_filter:
                            pipes.append(link_id)
                            print('Add PIPE: ', link_id)
                case tk.PUMP:
                    if self.element_filter is None or 'PUMPS' in self.element_filter:
                        if self.id_filter is None or link_id in self.id_filter:
                            pumps.append(link_id)
                            print('Add PUMP: ', link_id)   
                case _:
                    if self.element_filter is None or 'VALVES' in self.element_filter:
                        if self.id_filter is None or link_id in self.id_filter:
                            valves.append(link_id)
                            print('Add VALVE: ', link_id)
        
        # Get results
        duration = tk.gettimeparam(self._handle1, tk.DURATION)
        quality_analysis_type, _ = tk.getqualtype(self._handle1)
        if quality_analysis_type == tk.NONE:
            # Hydraulic analysis.
            tk.openH(self._handle1)
            tk.openH(self._handle2)
            tk.initH(self._handle1, 00)
            tk.initH(self._handle2, 00)          
            
            # Solve.
            while True:
                # Run sep.
                time = tk.runH(self._handle1)
                tk.runH(self._handle2)
                print("Time = ", time)
                
                # Store results.
                for node_id in junctions:
                    print("Junction:", node_id)
                    nindex_1 = tk.getnodeindex(self._handle1, node_id)
                    nindex_2 = tk.getnodeindex(self._handle2, node_id)
                    for variable, code in VARIABLE_MAP["JUNCTIONS"].items():
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getnodevalue(self._handle1, nindex_1, code)
                            value_2 = tk.getnodevalue(self._handle2, nindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
                            
                for node_id in reservoirs:
                    print("Reservoir:", node_id)
                    nindex_1 = tk.getnodeindex(self._handle1, node_id)
                    nindex_2 = tk.getnodeindex(self._handle2, node_id)
                    for variable, code in VARIABLE_MAP["RESERVOIRS"].items():
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getnodevalue(self._handle1, nindex_1, code)
                            value_2 = tk.getnodevalue(self._handle2, nindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
                            
                for node_id in tanks:
                    print("Tank:", node_id)
                    nindex_1 = tk.getnodeindex(self._handle1, node_id)
                    nindex_2 = tk.getnodeindex(self._handle2, node_id)
                    for variable, code in VARIABLE_MAP["TANKS"].items():     
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getnodevalue(self._handle1, nindex_1, code)
                            value_2 = tk.getnodevalue(self._handle2, nindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
               
                for link_id in pipes:
                    print("Pipe:", link_id)
                    lindex_1 = tk.getlinkindex(self._handle1, link_id)
                    lindex_2 = tk.getlinkindex(self._handle2, link_id)
                    for variable, code in VARIABLE_MAP["PIPES"].items():
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getlinkvalue(self._handle1, lindex_1, code)
                            value_2 = tk.getlinkvalue(self._handle2, lindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
                            
                for link_id in valves:
                    print("Valve:", link_id)
                    lindex_1 = tk.getlinkindex(self._handle1, link_id)
                    lindex_2 = tk.getlinkindex(self._handle2, link_id)
                    for variable, code in VARIABLE_MAP["VALVES"].items():
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getlinkvalue(self._handle1, lindex_1, code)
                            value_2 = tk.getlinkvalue(self._handle2, lindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
                            
                for link_id in pumps:
                    print("Pump:", link_id)
                    lindex_1 = tk.getlinkindex(self._handle1, link_id)
                    lindex_2 = tk.getlinkindex(self._handle2, link_id)
                    for variable, code in VARIABLE_MAP["PUMPS"].items():     
                        if self.variable_filter is None or variable in self.variable_filter:
                            value_1 = tk.getlinkvalue(self._handle1, lindex_1, code)
                            value_2 = tk.getlinkvalue(self._handle2, lindex_2, code)
                            print(variable, end=" = ")
                            print("Value 1:", value_1, "Value 2:", value_2)
               
                # End of loop.
                if time == duration:
                    break
                else:
                    tk.nextH(self._handle1)
                    tk.nextH(self._handle2)
                
            tk.closeH(self._handle1)
            tk.closeH(self._handle2)
        else:
            # Quality analysis.
            pass


        # Close project handles
        self._close(self._handle1)
        self._close(self._handle2)


if __name__ == '__main__':
    inp1 = "D:\MODELOS\example_1.inp"
    inp2 = "D:\MODELOS\example_2.inp"
    comp = Comparer(inp1, inp2, ["TANKS", "PUMPS"], ["Tank", "Pump"], ["tank_volume", "pump_state", "energy"])
    comp.run()
