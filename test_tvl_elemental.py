from agentic_lca.client import LcaExecutor
from agentic_lca.tvl import ThermodynamicVerifier

def main():
    try:
        executor = LcaExecutor()
        print("Finding 'silicone product production' process...")
        procs = executor.find_process("silicone product production")
        if not procs:
            print("Process not found.")
            return
            
        proc = executor.get_process(procs[0].id)
        
        verifier = ThermodynamicVerifier(tolerance=0.02)
        is_balanced, report = verifier.verify_mass_balance(proc)
        
        print("\n=== TVL MASS BALANCE REPORT ===")
        print(f"Process Name: {report['process_name']}")
        print(f"Total Input Mass:  {report['total_input_mass_kg']:.6f} kg")
        print(f"Total Output Mass: {report['total_output_mass_kg']:.6f} kg")
        print(f"Discrepancy:      {report['discrepancy_kg']:.6f} kg")
        print(f"Relative Error:   {report['relative_error']*100:.4f}%")
        print(f"Is Balanced?      {report['is_balanced']}")
        print(f"Is Bulk Balanced? {report['is_bulk_balanced']}")
        print(f"Is Elemental Balanced? {report['is_elemental_balanced']}")
        
        if report['elemental_discrepancies']:
            print("\nElemental Discrepancies:")
            for el, data in report['elemental_discrepancies'].items():
                print(f" - Element '{el}':")
                print(f"   Input:  {data['input_kg']:.6f} kg")
                print(f"   Output: {data['output_kg']:.6f} kg")
                print(f"   Diff:   {data['difference_kg']:.6f} kg")
                print(f"   Error:  {data['relative_error']*100:.4f}%")
        else:
            print("\nNo elemental mass discrepancies detected!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
