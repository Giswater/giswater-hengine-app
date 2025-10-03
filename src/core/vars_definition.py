"""
vars_definition.py

Module for defining calibration variables for EPANET network modifications.

This module provides a structured way to define variables that will be used
to modify network parameters during calibration. Each variable definition
includes the parameter to modify, the target elements, the modification
method, and the bounds for the variable value.
"""

from __future__ import annotations
from typing import List, Union, Dict
from enum import Enum
from dataclasses import dataclass
from epanet import toolkit as tk


# -----------------------------------------------------------------------------
# Variable maps - EPANET toolkit parameter codes
# -----------------------------------------------------------------------------
SYSTEM_VARIABLE_MAP: Dict[str, int] = {
    'relative_viscosity': tk.SP_VISCOS,
    'demand_multiplier': tk.DEMANDMULT,
    'emitter_exponent': tk.EMITEXPON,
    'relative_diffusivity': tk.SP_DIFFUS,
    'bulk_reaction_order': tk.BULKORDER,
    # 'global_bulk_coeff': tk.GLOBALBULK,
    # 'global_wall_coeff': tk.GLOBALWALL,
    'limiting_concentration': tk.CONCENLIMIT,
    'wall_coefficient_correlation': tk.WALLORDER,
    'pump_efficiency': tk.GLOBALEFFIC
}

NODE_VARIABLE_MAP: Dict[str, int] = {
    'base_demand': tk.BASEDEMAND,
    'emitter_coefficient': tk.EMITTER,
    'initial_quality': tk.INITQUAL,
    'mixing_fraction': tk.MIXFRACTION,
    'reaction_coefficient': tk.KBULK,
}

LINK_VARIABLE_MAP: Dict[str, int] = {
    'length': tk.LENGTH,
    'diameter': tk.DIAMETER,
    'roughness': tk.ROUGHNESS,
    'loss_coefficient': tk.MINORLOSS,
    'bulk_coefficient': tk.KBULK,
    'wall_coefficient': tk.KWALL,
    'setting': tk.SETTING,
}

PATTERN_VARIABLE_MAP: Dict[str, int] = {
    'pattern_multiplier': tk.PATTERN,  # Pattern multipliers
}


class ModificationMethod(Enum):
    """
    Enumeration of methods for applying variable values to network parameters.
    
    REPLACE: Directly replace the parameter value with the variable value.
    ADD: Add the variable value to the current parameter value.
    MULTIPLY: Multiply the current parameter value by the variable value.
    """
    REPLACE = "REPLACE"
    ADD = "ADD"
    MULTIPLY = "MULTIPLY"


@dataclass
class VariableDefinition:
    """
    Definition of a single calibration variable.
    
    Attributes
    ----------
    variable_name : str
        Name of the variable (must exist in one of the variable maps).
    variable_code : int
        EPANET toolkit code for the variable.
    variable_type : str
        Type of variable: 'system', 'node', 'link', or 'pattern'.
    features : Union[str, List[str]]
        Element ID(s) to which this variable applies.
        Can be a single ID, a list of IDs, or a mask pattern (e.g., "P*").
    method : ModificationMethod
        How to apply the variable value to the parameter.
    lower_bound : float
        Minimum allowed value for this variable.
    upper_bound : float
        Maximum allowed value for this variable.
    """
    variable_name: str
    variable_code: int
    variable_type: str
    features: Union[str, List[str]]
    method: ModificationMethod
    lower_bound: float
    upper_bound: float
    
    def __repr__(self) -> str:
        return (f"VariableDefinition(name={self.variable_name}, "
                f"type={self.variable_type}, features={self.features}, "
                f"method={self.method.value}, "
                f"bounds=[{self.lower_bound}, {self.upper_bound}])")


class VarsDefinition:
    """
    Container for managing multiple calibration variable definitions.
    
    This class stores and validates variable definitions that will be used
    to modify network parameters during calibration.
    
    Attributes
    ----------
    variables : List[VariableDefinition]
        List of all defined calibration variables.
    
    Examples
    --------
    >>> vars_def = VarsDefinition()
    >>> vars_def.add_variable("roughness P* MULTIPLY 0.8 1.2")
    >>> vars_def.add_variable("base_demand J01,J02,J03 MULTIPLY 0.9 1.1")
    >>> vars_def.add_variable("initial_quality J05 ADD -5.0 5.0")
    >>> print(f"Total variables: {len(vars_def)}")
    >>> for var in vars_def.variables:
    ...     print(var)
    """
    
    def __init__(self):
        """Initialize an empty variable definitions container."""
        self.variables: List[VariableDefinition] = []
    
    def add_variable(self, definition: str) -> None:
        """
        Add a variable definition from a formatted string.
        
        Parameters
        ----------
        definition : str
            Space-separated string with format:
            "variable_name feature method lower_bound upper_bound"
            
            - variable_name: Must exist in one of the variable maps
            - feature: Element ID, comma-separated list (no spaces), or mask
                      Examples: "J01", "J01,J02,J03", "P*", "PIPE_*"
            - method: REPLACE, ADD, or MULTIPLY
            - lower_bound: Minimum value (float)
            - upper_bound: Maximum value (float)
        
        Raises
        ------
        ValueError
            If the definition string is malformed or contains invalid values.
        
        Examples
        --------
        Single element:
        >>> vars_def.add_variable("roughness PIPE01 REPLACE 100 150")
        
        Multiple elements (comma-separated, no spaces):
        >>> vars_def.add_variable("base_demand J01,J02,J03 MULTIPLY 0.9 1.1")
        
        Pattern mask:
        >>> vars_def.add_variable("roughness P* MULTIPLY 0.8 1.2")
        
        System variable:
        >>> vars_def.add_variable("demand_multiplier SYSTEM REPLACE 0.8 1.2")
        """
        parts = definition.strip().split()
        
        if len(parts) != 5:
            raise ValueError(
                f"Invalid definition format. Expected 5 parts, got {len(parts)}. "
                f"Format: 'variable_name feature method lower_bound upper_bound'"
            )
        
        variable_name, features_str, method_str, lower_str, upper_str = parts
        
        # Validate and get variable info
        variable_code, variable_type = self._resolve_variable(variable_name)
        
        # Parse feature (can be single ID, list, or mask)
        features = self._parse_features(features_str)
        
        # Parse modification method
        try:
            method = ModificationMethod[method_str.upper()]
        except KeyError:
            valid_methods = [m.value for m in ModificationMethod]
            raise ValueError(
                f"Invalid method '{method_str}'. "
                f"Must be one of: {', '.join(valid_methods)}"
            )
        
        # Parse bounds
        try:
            lower_bound = float(lower_str)
            upper_bound = float(upper_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid bounds: lower='{lower_str}', upper='{upper_str}'. "
                f"Must be numeric values. Error: {e}"
            )
        
        # Validate bounds
        if lower_bound > upper_bound:
            raise ValueError(
                f"Lower bound ({lower_bound}) cannot be greater than "
                f"upper bound ({upper_bound})"
            )
        
        # Create and store the variable definition
        var_def = VariableDefinition(
            variable_name=variable_name,
            variable_code=variable_code,
            variable_type=variable_type,
            features=features,
            method=method,
            lower_bound=lower_bound,
            upper_bound=upper_bound
        )
        
        self.variables.append(var_def)
    
    def _resolve_variable(self, variable_name: str) -> tuple[int, str]:
        """
        Resolve variable name to EPANET code and type.
        
        Parameters
        ----------
        variable_name : str
            Name of the variable to resolve.
        
        Returns
        -------
        tuple[int, str]
            (variable_code, variable_type) where variable_type is one of:
            'system', 'node', 'link', 'pattern'
        
        Raises
        ------
        ValueError
            If variable_name is not found in any variable map.
        """
        if variable_name in SYSTEM_VARIABLE_MAP:
            return SYSTEM_VARIABLE_MAP[variable_name], 'system'
        elif variable_name in NODE_VARIABLE_MAP:
            return NODE_VARIABLE_MAP[variable_name], 'node'
        elif variable_name in LINK_VARIABLE_MAP:
            return LINK_VARIABLE_MAP[variable_name], 'link'
        elif variable_name in PATTERN_VARIABLE_MAP:
            return PATTERN_VARIABLE_MAP[variable_name], 'pattern'
        else:
            raise ValueError(
                f"Unknown variable '{variable_name}'. "
                f"Must be defined in one of: SYSTEM_VARIABLE_MAP, "
                f"NODE_VARIABLE_MAP, LINK_VARIABLE_MAP, PATTERN_VARIABLE_MAP"
            )
    
    def _parse_features(self, features_str: str) -> Union[str, List[str]]:
        """
        Parse feature string into element ID(s).
        
        Parameters
        ----------
        features_str : str
            Single ID, comma-separated list, or mask pattern.
        
        Returns
        -------
        Union[str, List[str]]
            Single string if one element or mask, list if multiple elements.
        
        Examples
        --------
        >>> self._parse_feature("J01")
        'J01'
        >>> self._parse_feature("J01,J02,J03")
        ['J01', 'J02', 'J03']
        >>> self._parse_feature("P*")
        'P*'
        """
        # Check if it's a list (contains commas)
        if ',' in features_str:
            elements = [e.strip() for e in features_str.split(',')]
            # Remove empty strings
            elements = [e for e in elements if e]
            if not elements:
                raise ValueError("Empty feature list provided")
            return elements
        
        # Single element or mask
        return features_str.strip()
    
    def get_bounds(self) -> tuple[List[float], List[float]]:
        """
        Get lower and upper bounds for all variables.
        
        Returns
        -------
        tuple[List[float], List[float]]
            (lower_bounds, upper_bounds) where each is a list of floats
            with one entry per variable.
        """
        lower_bounds = [var.lower_bound for var in self.variables]
        upper_bounds = [var.upper_bound for var in self.variables]
        return lower_bounds, upper_bounds
    
    def get_variable(self, index: int) -> VariableDefinition:
        """
        Get a specific variable definition by index.
        
        Parameters
        ----------
        index : int
            Index of the variable in the list.
        
        Returns
        -------
        VariableDefinition
            The variable definition at the specified index.
        """
        return self.variables[index]
    
    def clear(self) -> None:
        """Remove all variable definitions."""
        self.variables.clear()
    
    def __len__(self) -> int:
        """Return the number of defined variables."""
        return len(self.variables)
    
    def __iter__(self):
        """Allow iteration over variable definitions."""
        return iter(self.variables)
    
    def __repr__(self) -> str:
        return f"VarsDefinition(n_variables={len(self.variables)})"
    
    def __str__(self) -> str:
        lines = [f"VarsDefinition with {len(self.variables)} variable(s):"]
        for i, var in enumerate(self.variables, 1):
            lines.append(f"  {i}. {var}")
        return "\n".join(lines)


# Example usage and testing
if __name__ == "__main__":
    # Create instance
    vars_def = VarsDefinition()
    
    # Add various variable definitions
    print("Adding variable definitions...")
    
    # SYSTEM variables
    vars_def.add_variable("demand_multiplier SYSTEM MULTIPLY 0.8 1.2")
    
    # NODE variables
    vars_def.add_variable("base_demand J01,J02,J03 MULTIPLY 0.9 1.1")
    vars_def.add_variable("emitter_coefficient N05 REPLACE 0.0 10.0")
    vars_def.add_variable("initial_quality J* REPLACE 0.0 1.0")
    
    # LINK variables
    vars_def.add_variable("roughness P* MULTIPLY 0.8 1.2")
    vars_def.add_variable("diameter PIPE01 ADD -0.05 0.05")
    vars_def.add_variable("loss_coefficient V* REPLACE 0.0 5.0")
    
    # Print results
    print(f"\n{vars_def}\n")
    
    # Get bounds
    lower, upper = vars_def.get_bounds()
    print(f"Lower bounds: {lower}")
    print(f"Upper bounds: {upper}")
    
    # Iterate over variables
    print("\nIteration test:")
    for i, var in enumerate(vars_def):
        print(f"{i}: {var.variable_name} -> {var.features}")
    
    # Test error handling
    print("\n--- Testing error handling ---")
    try:
        vars_def.add_variable("invalid_var J01 REPLACE 0 1")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
    
    try:
        vars_def.add_variable("roughness J01 INVALID_METHOD 0 1")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
    
    try:
        vars_def.add_variable("roughness J01 REPLACE 10 5")  # lower > upper
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")