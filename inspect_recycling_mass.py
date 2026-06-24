from agentic_lca import LcaExecutor
from agentic_lca.tvl import ThermodynamicVerifier
import olca_schema as o

def main():
    try:
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier()
        
        sys_name = "Mechanical recycling of used c-Si panel - US-TRE"
        systems = executor.find_product_system(sys_name)
        sys_obj = executor.client.get(o.ProductSystem, systems[0].id)
        ref_proc = sys_obj.ref_process
        proc = executor.get_process(ref_proc.id)
        
        is_balanced, report = verifier.verify_mass_balance(proc)
        
        print(f"=== Baseline Mass Verification for: {proc.name} ===")
        print(f"Is balanced? {is_balanced}")
        print(f"Total Input Mass:  {report['total_input_mass_kg']:.6f} kg")
        print(f"Total Output Mass: {report['total_output_mass_kg']:.6f} kg")
        print(f"Discrepancy:      {report['discrepancy_kg']:.6f} kg")
        print(f"Relative Error:   {report['relative_error']*100:.4f}%")
        
        print("\n--- Tracked Mass Exchanges ---")
        for e in report['mass_exchanges_tracked']:
            direction = "Input" if e['is_input'] else "Output"
            print(f" - [{direction}] {e['flow_name']}: {e['mass_kg']:.6f} kg ({e['amount']} {e['unit']})")
            
        print("\n--- Non-Mass Exchanges (Not Tracked by TVL) ---")
        all_tracked_flows = {e['flow_name'] for e in report['mass_exchanges_tracked']}
        for ex in proc.exchanges:
            if ex.flow.name not in all_tracked_flows:
                direction = "Input" if ex.is_input else "Output"
                print(f" - [{direction}] {ex.flow.name}: {ex.amount} {ex.unit.name if ex.unit else 'N/A'}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
