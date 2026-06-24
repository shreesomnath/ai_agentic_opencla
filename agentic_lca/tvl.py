class ThermodynamicVerifier:
    """
    Implements stoichiometric and thermodynamic checks (e.g., bulk mass balance)
    on processes in the LCA inventory to ensure physical consistency.
    """
    def __init__(self, tolerance=0.01):
        self.tolerance = tolerance
        # Standard conversion factors to kg
        self.mass_units = {
            "kg": 1.0,
            "g": 1e-3,
            "mg": 1e-6,
            "t": 1e3,
            "ton": 1e3,
            "lb": 0.45359237,
            "kilogram": 1.0,
            "gram": 1e-3,
            "metric ton": 1e3
        }

    def verify_mass_balance(self, process):
        """
        Calculates the bulk mass balance of a process's exchanges.
        Converts volume of water to mass using standard water density.
        Returns a tuple of (is_balanced, report_dict).
        """
        total_input_mass = 0.0
        total_output_mass = 0.0
        mass_exchanges = []
        
        for exchange in process.exchanges:
            flow = exchange.flow
            unit = exchange.unit
            amount = exchange.amount
            
            if not flow or not unit:
                continue
                
            flow_name = flow.name.lower()
            unit_name = unit.name.lower()
            flow_property_name = ""
            if getattr(exchange, "flow_property", None) and exchange.flow_property.name:
                flow_property_name = exchange.flow_property.name.lower()
                
            is_mass = False
            mass_in_kg = 0.0
            
            # Check if it is a mass flow property or has standard mass unit
            if flow_property_name == "mass" or unit_name in self.mass_units:
                factor = self.mass_units.get(unit_name, 1.0)
                mass_in_kg = amount * factor
                is_mass = True
            # Physical conversions: water volume to mass
            elif "water" in flow_name and unit_name in ["m3", "cubic meter", "cubic metre"]:
                mass_in_kg = amount * 1000.0 # 1 m3 = 1000 kg water
                is_mass = True
            # For other volume flows, we could add density factors if chemical composition is known.
            
            if is_mass:
                mass_exchanges.append({
                    "flow_name": flow.name,
                    "amount": amount,
                    "unit": unit.name,
                    "mass_kg": mass_in_kg,
                    "is_input": exchange.is_input
                })
                if exchange.is_input:
                    total_input_mass += mass_in_kg
                else:
                    total_output_mass += mass_in_kg
                    
        # Calculate discrepancy
        if total_input_mass > 0:
            discrepancy = abs(total_input_mass - total_output_mass)
            relative_error = discrepancy / total_input_mass
        else:
            discrepancy = abs(total_output_mass)
            relative_error = 1.0 if total_output_mass > 0 else 0.0
            
        is_balanced = relative_error <= self.tolerance
        
        report = {
            "process_name": process.name,
            "process_id": process.id,
            "total_input_mass_kg": total_input_mass,
            "total_output_mass_kg": total_output_mass,
            "discrepancy_kg": discrepancy,
            "relative_error": relative_error,
            "is_balanced": is_balanced,
            "mass_exchanges_tracked": mass_exchanges
        }
        
        return is_balanced, report
