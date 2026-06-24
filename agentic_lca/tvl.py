import re
import requests

class ThermodynamicVerifier:
    """
    Implements stoichiometric and thermodynamic checks (e.g., bulk mass balance 
    and elemental mass conservation) on processes in the LCA inventory to ensure physical consistency.
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
        
        self.atomic_weights = {
            "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81, "C": 12.011,
            "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.18, "Na": 22.99, "Mg": 24.305,
            "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948,
            "K": 39.098, "Ca": 40.078, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933,
            "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Br": 79.904, "Ag": 107.87, "Sn": 118.71,
            "I": 126.9, "Ba": 137.33, "W": 183.84, "Pt": 195.08, "Au": 196.97, "Pb": 207.2
        }

        self.chemical_map = {
            "water": {"H": 0.1119, "O": 0.8881},
            "polyethylene": {"C": 0.8563, "H": 0.1437},
            "glass": {"Si": 0.4674, "O": 0.5326},
            "silicon": {"Si": 1.0},
            "steel": {"Fe": 1.0},
            "iron": {"Fe": 1.0},
            "aluminum": {"Al": 1.0},
            "aluminium": {"Al": 1.0},
            "carbon dioxide": {"C": 0.2729, "O": 0.7271},
            "methane": {"C": 0.7487, "H": 0.2513},
            "silicone": {"C": 0.324, "H": 0.0816, "O": 0.2158, "Si": 0.3786},
            "silicon tetrachloride": {"Si": 0.1653, "Cl": 0.8347}
        }

    def _clean_name(self, name):
        """Cleans flow names to matching chemical words."""
        cleaned = name.lower()
        cleaned = cleaned.split(",")[0]
        cleaned = cleaned.replace("tap ", "")
        cleaned = cleaned.replace("scrap ", "")
        cleaned = cleaned.replace("sorted ", "")
        cleaned = cleaned.replace("cullet", "glass")
        return cleaned.strip()

    def _query_pubchem(self, cleaned_name):
        """Queries PubChem REST API for the molecular formula of a substance."""
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cleaned_name}/property/MolecularFormula/JSON"
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                properties = data.get("PropertyTable", {}).get("Properties", [])
                if properties:
                    return properties[0].get("MolecularFormula")
        except Exception:
            pass
        return None

    def _parse_formula(self, formula):
        """Parses a molecular formula string to return elemental mass fractions."""
        pattern = r'([A-Z][a-z]?)([0-9]*)'
        matches = re.findall(pattern, formula)
        
        element_counts = {}
        total_mass = 0.0
        
        for element, count_str in matches:
            count = int(count_str) if count_str else 1
            weight = self.atomic_weights.get(element, 0.0)
            if weight == 0.0:
                continue
            element_mass = count * weight
            element_counts[element] = element_counts.get(element, 0.0) + element_mass
            total_mass += element_mass
            
        if total_mass == 0.0:
            return {}
            
        return {el: mass / total_mass for el, mass in element_counts.items()}

    def get_flow_composition(self, name):
        """Retrieves or queries the elemental mass composition of a substance name."""
        if "custom assembly" in name.lower() or "custom process" in name.lower():
            return {}
            
        cleaned_name = self._clean_name(name)
        
        # Check local registry with word boundary constraints to avoid false substring matches (e.g. fiberglass matching glass)
        for key, comp in self.chemical_map.items():
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, cleaned_name):
                return comp
                
        # Query PubChem as fallback
        formula = self._query_pubchem(cleaned_name)
        if formula:
            comp = self._parse_formula(formula)
            if comp:
                # Cache
                self.chemical_map[cleaned_name] = comp
                return comp
                
        return {}

    def verify_mass_balance(self, process):
        """
        Calculates both bulk mass balance and elemental stoichiometric conservation.
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
            
            if flow_property_name == "mass" or unit_name in self.mass_units:
                factor = self.mass_units.get(unit_name, 1.0)
                mass_in_kg = amount * factor
                is_mass = True
            elif "water" in flow_name and unit_name in ["m3", "cubic meter", "cubic metre"]:
                mass_in_kg = amount * 1000.0
                is_mass = True
                
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
                    
        # Bulk discrepancies
        if total_input_mass > 0:
            discrepancy = abs(total_input_mass - total_output_mass)
            relative_error = discrepancy / total_input_mass
        else:
            discrepancy = abs(total_output_mass)
            relative_error = 1.0 if total_output_mass > 0 else 0.0
            
        is_bulk_balanced = relative_error <= self.tolerance

        # Elemental discrepancies calculation
        elemental_inputs = {}
        elemental_outputs = {}
        
        for ex in mass_exchanges:
            flow_name = ex["flow_name"]
            mass_kg = ex["mass_kg"]
            is_input = ex["is_input"]
            
            comp = self.get_flow_composition(flow_name)
            if not comp:
                continue
                
            for el, fraction in comp.items():
                el_mass = mass_kg * fraction
                if is_input:
                    elemental_inputs[el] = elemental_inputs.get(el, 0.0) + el_mass
                else:
                    elemental_outputs[el] = elemental_outputs.get(el, 0.0) + el_mass
                    
        # Check main output flow synthesis for assemblies
        main_output = next((ex for ex in process.exchanges if not ex.is_input and ex.is_quantitative_reference), None)
        if main_output and main_output.flow:
            main_output_name = main_output.flow.name
            main_output_comp = self.get_flow_composition(main_output_name)
            if not main_output_comp:
                other_output_elements = {}
                for ex in mass_exchanges:
                    if not ex["is_input"] and ex["flow_name"] != main_output_name:
                        comp = self.get_flow_composition(ex["flow_name"])
                        if comp:
                            for el, frac in comp.items():
                                other_output_elements[el] = other_output_elements.get(el, 0.0) + (ex["mass_kg"] * frac)
                                
                net_elements = {}
                for el, m_in in elemental_inputs.items():
                    m_other_out = other_output_elements.get(el, 0.0)
                    net_m = m_in - m_other_out
                    if net_m > 0:
                        net_elements[el] = net_m
                        
                main_output_mass = next((ex["mass_kg"] for ex in mass_exchanges if ex["flow_name"] == main_output_name), 0.0)
                if main_output_mass > 0:
                    synthesized_comp = {el: net_m / main_output_mass for el, net_m in net_elements.items()}
                    elemental_outputs = {}
                    for ex in mass_exchanges:
                        if not ex["is_input"]:
                            if ex["flow_name"] == main_output_name:
                                comp = synthesized_comp
                            else:
                                comp = self.get_flow_composition(ex["flow_name"])
                            if comp:
                                for el, frac in comp.items():
                                    elemental_outputs[el] = elemental_outputs.get(el, 0.0) + (ex["mass_kg"] * frac)

        # Compare elemental balances
        elemental_discrepancies = {}
        is_elemental_balanced = True
        
        all_elements = set(elemental_inputs.keys()) | set(elemental_outputs.keys())
        for el in all_elements:
            m_in = elemental_inputs.get(el, 0.0)
            m_out = elemental_outputs.get(el, 0.0)
            
            if m_in < 1e-4 and m_out < 1e-4:
                continue
                
            diff = abs(m_in - m_out)
            max_m = max(m_in, m_out)
            rel_err = diff / max_m if max_m > 0 else 0.0
            
            if rel_err > self.tolerance:
                if (m_in == 0 or m_out == 0) and diff < 0.01:
                    continue
                elemental_discrepancies[el] = {
                    "input_kg": m_in,
                    "output_kg": m_out,
                    "difference_kg": diff,
                    "relative_error": rel_err
                }
                is_elemental_balanced = False
                
        # Total balanced state is a combination of bulk and elemental conservation
        is_balanced = is_bulk_balanced and is_elemental_balanced
        
        report = {
            "process_name": process.name,
            "process_id": process.id,
            "total_input_mass_kg": total_input_mass,
            "total_output_mass_kg": total_output_mass,
            "discrepancy_kg": discrepancy,
            "relative_error": relative_error,
            "is_balanced": is_balanced,
            "is_bulk_balanced": is_bulk_balanced,
            "is_elemental_balanced": is_elemental_balanced,
            "elemental_discrepancies": elemental_discrepancies,
            "mass_exchanges_tracked": mass_exchanges
        }
        
        return is_balanced, report
