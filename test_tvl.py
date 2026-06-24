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
        
        verifier = ThermodynamicVerifier(tolerance=0.02) # 2% tolerance
        is_balanced, report = verifier.verify_mass_balance(proc)
        
        print("\n=== TVL MASS BALANCE REPORT ===")
        print(f"Process Name: {report['process_name']}")
        print(f"Total Input Mass:  {report['total_input_mass_kg']:.6f} kg")
        print(f"Total Output Mass: {report['total_output_mass_kg']:.6f} kg")
        print(f"Discrepancy:      {report['discrepancy_kg']:.6f} kg")
        print(f"Relative Error:   {report['relative_error']*100:.4f}%")
        print(f"Is Mass Balanced? {report['is_balanced']}")
        
        print("\nTop 5 Input Flows by Mass:")
        inputs = sorted([e for e in report['mass_exchanges_tracked'] if e['is_input']], key=lambda x: x['mass_kg'], reverse=True)
        for e in inputs[:5]:
            print(f" - {e['flow_name']}: {e['mass_kg']:.6f} kg ({e['amount']} {e['unit']})")
            
        print("\nTop 5 Output Flows by Mass:")
        outputs = sorted([e for e in report['mass_exchanges_tracked'] if not e['is_input']], key=lambda x: x['mass_kg'], reverse=True)
        for e in outputs[:5]:
            print(f" - {e['flow_name']}: {e['mass_kg']:.6f} kg ({e['amount']} {e['unit']})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
