from agentic_lca.client import LcaExecutor
from agentic_lca.tvl import ThermodynamicVerifier
from agentic_lca.multiobjective import MultiObjectiveEvaluator

class DummyFlowDesc:
    def __init__(self, fid, name, unit="kg"):
        self.id = fid
        self.name = name
        self.ref_unit = unit

def main():
    try:
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier()
        
        # Test 1: steel replaced by polyethylene (high mismatch!)
        orig_steel = DummyFlowDesc("1", "steel, low-alloyed")
        sub_poly = DummyFlowDesc("2", "polyethylene, high density, granulate")
        
        print("Test 1: Substituting 'steel, low-alloyed' with 'polyethylene'...")
        orig_comp = verifier.get_flow_composition(orig_steel.name)
        sub_comp = verifier.get_flow_composition(sub_poly.name)
        print(f" - Original composition: {orig_comp}")
        print(f" - Substitute composition: {sub_comp}")
        
        discrepancy = 0.0
        all_elements = set(orig_comp.keys()) | set(sub_comp.keys())
        for el in all_elements:
            discrepancy += abs(orig_comp.get(el, 0.0) - sub_comp.get(el, 0.0))
            
        print(f" - Elemental discrepancy distance: {discrepancy*100:.1f}%")
        if discrepancy > 0.20:
            print(" -> [REJECTED] Mismatch exceeds 20% limit. TVL works!")
        else:
            print(" -> [ACCEPTED]")
            
        # Test 2: steel replaced by iron/scrap steel (low mismatch!)
        sub_scrap = DummyFlowDesc("3", "scrap steel")
        print("\nTest 2: Substituting 'steel, low-alloyed' with 'scrap steel'...")
        sub_comp2 = verifier.get_flow_composition(sub_scrap.name)
        print(f" - Substitute composition: {sub_comp2}")
        
        discrepancy2 = 0.0
        all_elements2 = set(orig_comp.keys()) | set(sub_comp2.keys())
        for el in all_elements2:
            discrepancy2 += abs(orig_comp.get(el, 0.0) - sub_comp2.get(el, 0.0))
            
        print(f" - Elemental discrepancy distance: {discrepancy2*100:.1f}%")
        if discrepancy2 > 0.20:
            print(" -> [REJECTED]")
        else:
            print(" -> [ACCEPTED] Mismatch within 20% limit. TVL works!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
