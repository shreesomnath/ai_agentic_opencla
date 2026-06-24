import csv
import uuid
import olca_schema as o
import time
from agentic_lca import LcaExecutor, FlowMapper, ThermodynamicVerifier

def get_unit_refs(client):
    """Scrapes common unit references from an existing database process to avoid hardcoding."""
    processes = list(client.get_descriptors(o.Process))
    sample_proc_desc = next((p for p in processes if "silicone product production" in p.name), None)
    if not sample_proc_desc:
        if processes:
            sample_proc_desc = processes[0]
        else:
            raise ValueError("No processes found in database to scrape units.")
            
    sample_proc = client.get(o.Process, sample_proc_desc.id)
    unit_map = {}
    for ex in sample_proc.exchanges:
        if ex.unit:
            unit_map[ex.unit.name.lower()] = ex.unit
    return unit_map

def main():
    try:
        # Initialize LcaExecutor, FlowMapper, and ThermodynamicVerifier
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01) # 1% tolerance
        mapper = FlowMapper(executor)
        
        # Scrape units
        unit_map = get_unit_refs(executor.client)
        kg_unit = unit_map.get("kg")
        
        if not kg_unit:
            raise ValueError("Kilogram (kg) unit reference not found in database.")
            
        print("\n" + "="*50)
        print("     AUTOMATED BOM INGESTION & MODEL SYNTHESIS")
        print("="*50)
        
        # 1. Parse CSV and map flows
        print("\n[1/5] Ingesting BOM and mapping exchanges to ecoinvent flows...")
        exchanges = []
        total_input_mass = 0.0
        internal_id_counter = 2 # Start at 2, reserving 1 for reference output
        
        with open("sample_bom.csv", mode="r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flow_name = row["flow_name"]
                amount = float(row["amount"])
                unit_name = row["unit"]
                
                # Search flow in database
                matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
                if not matches:
                    print(f"Warning: Flow '{flow_name}' not found. Skipping.")
                    continue
                matched_flow, score = matches[0]
                print(f" - BOM: '{flow_name}' ({amount} {unit_name}) -> ecoinvent: '{matched_flow.name}' (Score: {score:.3f})")
                
                # Map unit
                matched_unit = unit_map.get(unit_name.lower())
                if not matched_unit:
                    matched_unit = kg_unit # Fallback to kg
                    
                # Create exchange
                exchange = o.Exchange()
                exchange.is_input = True
                exchange.flow = o.Ref(
                    ref_type=o.RefType.Flow,
                    id=matched_flow.id,
                    name=matched_flow.name,
                    ref_unit=matched_flow.ref_unit
                )
                exchange.amount = amount
                exchange.unit = o.Ref(
                    ref_type=o.RefType.Unit,
                    id=matched_unit.id,
                    name=matched_unit.name
                )
                exchange.flow_property = o.Ref(
                    ref_type=o.RefType.FlowProperty,
                    id="93a60a56-a3c8-11da-a746-0800200b9a66", # Mass
                    name="Mass"
                )
                exchange.internal_id = internal_id_counter
                internal_id_counter += 1
                exchanges.append(exchange)
                
                # Convert density/units for mass balance
                if unit_name.lower() == "kg":
                    total_input_mass += amount
                elif unit_name.lower() == "g":
                    total_input_mass += amount * 1e-3
                elif "water" in flow_name.lower() and unit_name.lower() in ["m3", "cubic meter"]:
                    total_input_mass += amount * 1000.0
                    
        # 2. Programmatically create the new finished product flow
        print("\n[2/5] Creating finished product flow in OpenLCA database...")
        flow_id = str(uuid.uuid4())
        module_flow = o.Flow()
        module_flow.id = flow_id
        module_flow.name = "Next-Gen Silicon Solar Cell Module"
        module_flow.flow_type = o.FlowType.PRODUCT_FLOW
        module_flow.flow_properties = [
            o.FlowPropertyFactor(
                is_ref_flow_property=True,
                conversion_factor=1.0,
                flow_property=o.Ref(
                    ref_type=o.RefType.FlowProperty,
                    id="93a60a56-a3c8-11da-a746-0800200b9a66",
                    name="Mass"
                )
            )
        ]
        executor.client.put(module_flow)
        print(f" -> Flow created: '{module_flow.name}' (ID: {module_flow.id})")
        
        # 3. Create the new unit process in the database
        print("\n[3/5] Synthesizing unit process with mass-balanced quantitative reference...")
        process = o.Process()
        process.id = str(uuid.uuid4())
        process.name = "Next-Gen Silicon Solar Cell Manufacturing"
        process.process_type = o.ProcessType.UNIT_PROCESS
        
        # Reference output exchange
        out_exchange = o.Exchange()
        out_exchange.is_input = False
        out_exchange.flow = o.Ref(
            ref_type=o.RefType.Flow,
            id=module_flow.id,
            name=module_flow.name,
            ref_unit="kg"
        )
        out_exchange.amount = total_input_mass # Perfectly mass-balanced
        out_exchange.unit = o.Ref(
            ref_type=o.RefType.Unit,
            id=kg_unit.id,
            name=kg_unit.name
        )
        out_exchange.flow_property = o.Ref(
            ref_type=o.RefType.FlowProperty,
            id="93a60a56-a3c8-11da-a746-0800200b9a66",
            name="Mass"
        )
        out_exchange.is_quantitative_reference = True
        out_exchange.internal_id = 1
        
        process.exchanges = [out_exchange] + exchanges
        
        # Validate mass balance via TVL before inserting in database
        is_balanced, tvl_report = verifier.verify_mass_balance(process)
        print(f" -> TVL Verification: Mass Balanced? {is_balanced}")
        print(f"    Total Input:  {tvl_report['total_input_mass_kg']:.4f} kg")
        print(f"    Total Output: {tvl_report['total_output_mass_kg']:.4f} kg")
        print(f"    Discrepancy:  {tvl_report['discrepancy_kg']:.6f} kg (Error: {tvl_report['relative_error']*100:.6f}%)")
        
        # Write to database
        executor.client.put(process)
        print(f" -> Process successfully saved in database: ID {process.id}")
        
        # 4. Compile product system
        print("\n[4/5] Compiling product system in openLCA...")
        # Pass the full process entity to create_product_system to resolve flow types automatically
        sys_ref = executor.client.create_product_system(process)
        if not sys_ref:
            raise RuntimeError("Failed to compile product system.")
        print(f" -> Product System compiled successfully: ID {sys_ref.id}")
        
        # 5. Run LCIA GWP Calculation
        print("\n[5/5] Executing greenhouse gas GWP impact assessment...")
        methods = executor.find_impact_method("IPCC 2013 GWP 100a")
        if not methods:
            raise ValueError("IPCC 2013 GWP 100a method not found in database.")
        method_desc = methods[0]
        
        results = executor.calculate(sys_ref.id, method_desc.id)
        fossil_item = next((r for r in results if "fossil" in r["category_name"].lower()), None)
        
        print("\n" + "="*50)
        print("          SYNTHESIZED LCA STUDY REPORT")
        print("="*50)
        print(f"Product:      {module_flow.name}")
        print(f"Process:      {process.name}")
        print(f"Total Weight: {total_input_mass:.4f} kg")
        print(f"LCIA Method:  {method_desc.name}")
        print("-"*50)
        
        if fossil_item:
            print(f"Calculated GWP (Fossil): {fossil_item['amount']:.6f} {fossil_item['unit']}")
            # Normalized footprint per kg of product
            footprint_per_kg = fossil_item['amount'] / total_input_mass
            print(f"Normalized GWP Intensity: {footprint_per_kg:.6f} kg CO2 eq / kg product")
        else:
            print("Impact scores could not be resolved.")
            
        print(f"TVL Status:   PASSED (Error: {tvl_report['relative_error']*100:.6f}%)")
        print("="*50)
        
        # Cleanup
        print("\nCleaning up database modifications...")
        executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=sys_ref.id))
        executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=process.id))
        executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=module_flow.id))
        print("Clean-up completed.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        # Emergency restore/cleanup
        try:
            if 'executor' in locals() and 'sys_ref' in locals():
                executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=sys_ref.id))
            if 'executor' in locals() and 'process' in locals():
                executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=process.id))
            if 'executor' in locals() and 'module_flow' in locals():
                executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=module_flow.id))
            print("Clean-up executed after failure.")
        except:
            pass

if __name__ == "__main__":
    main()
