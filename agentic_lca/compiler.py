import uuid
import olca_schema as o

class LcaCompiler:
    """
    Programmatically compiles recursive hierarchical Bills of Materials (BOM)
    into structured openLCA flows, processes, and product systems.
    """
    def __init__(self, executor, mapper, verifier):
        self.executor = executor
        self.client = executor.client
        self.mapper = mapper
        self.verifier = verifier
        self.unit_map = {}
        self.assembly_processes = {}
        self.created_flows = []
        self.created_processes = []
        self.created_product_systems = []
        self._load_units()

    def _load_units(self):
        """Pre-caches common unit references to speed up compilation by reading exchanges from a sample process."""
        try:
            processes = list(self.client.get_descriptors(o.Process))
            sample_proc_desc = next((p for p in processes if "silicone product production" in p.name), None)
            if not sample_proc_desc and processes:
                sample_proc_desc = processes[0]
                
            if sample_proc_desc:
                sample_proc = self.client.get(o.Process, sample_proc_desc.id)
                for ex in sample_proc.exchanges:
                    if ex.unit:
                        self.unit_map[ex.unit.name.lower()] = ex.unit
        except Exception as e:
            print(f"[Compiler Warning] Failed to load units: {e}")

    def get_unit_ref(self, name):
        """Retrieves a o.Ref for a unit by name (case-insensitive)."""
        name_lower = name.lower()
        if name_lower in self.unit_map:
            return self.unit_map[name_lower]
            
        # Fallback to kg
        return self.unit_map.get("kg")

    def compile_bom(self, bom_dict):
        """
        Recursively compiles a hierarchical BOM dictionary into the database.
        Returns a tuple: (top_flow_ref, top_proc_ref, product_system_ref)
        """
        top_flow_ref, top_proc_ref = self._compile_node(bom_dict)
        
        # Build the final product system in openLCA
        print(f"[Compiler] Building product system for '{bom_dict['name']}'...")
        sys_ref = self.client.create_product_system(top_proc_ref)
        self.created_product_systems.append(sys_ref)
        
        return top_flow_ref, top_proc_ref, sys_ref

    def _compile_node(self, node):
        """Recursively parses a BOM node."""
        name = node["name"]
        amount = float(node.get("amount", 1.0))
        unit_str = node.get("unit", "kg")
        inputs = node.get("inputs", [])
        
        # Leaf Node: Match to existing database flow
        if not inputs:
            print(f"[Compiler] Leaf node '{name}' detected. Mapping to database flow...")
            matches = self.mapper.search(name, top_k=1)
            if not matches:
                raise ValueError(f"Could not map leaf node '{name}' to database flows.")
            flow_desc, score = matches[0]
            
            # Return descriptor reference
            flow_ref = o.Ref(
                ref_type=o.RefType.Flow,
                id=flow_desc.id,
                name=flow_desc.name,
                ref_unit=flow_desc.ref_unit
            )
            return flow_ref, None
            
        # Intermediate Assembly Node: Compile sub-inputs recursively
        print(f"[Compiler] Assembly node '{name}' detected. Compiling sub-inputs...")
        
        compiled_exchanges = []
        internal_counter = 2
        
        for sub_node in inputs:
            sub_name = sub_node["name"]
            sub_amt = float(sub_node.get("amount", 1.0))
            sub_unit_str = sub_node.get("unit", "kg")
            
            sub_flow_ref, sub_proc_ref = self._compile_node(sub_node)
            
            # Create exchange input reference
            ex = o.Exchange()
            ex.is_input = True
            ex.flow = sub_flow_ref
            ex.amount = sub_amt
            ex.unit = self.get_unit_ref(sub_unit_str)
            ex.flow_property = o.Ref(
                ref_type=o.RefType.FlowProperty,
                id="93a60a56-a3c8-11da-a746-0800200b9a66", # Mass
                name="Mass"
            )
            ex.internal_id = internal_counter
            internal_counter += 1
            compiled_exchanges.append(ex)
            
        # Create custom flow for the assembly
        flow_id = str(uuid.uuid4())
        custom_flow = o.Flow()
        custom_flow.id = flow_id
        custom_flow.name = f"Custom Assembly - {name}"
        custom_flow.flow_type = o.FlowType.PRODUCT_FLOW
        custom_flow.flow_properties = [
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
        self.client.put(custom_flow)
        self.created_flows.append(o.Ref(ref_type=o.RefType.Flow, id=flow_id))
        
        # Create unit process for the assembly
        proc_id = str(uuid.uuid4())
        custom_proc = o.Process()
        custom_proc.id = proc_id
        custom_proc.name = f"Custom Process - {name} Manufacturing"
        custom_proc.process_type = o.ProcessType.UNIT_PROCESS
        
        # Quantitative reference output exchange
        out_ex = o.Exchange()
        out_ex.is_input = False
        out_ex.flow = o.Ref(
            ref_type=o.RefType.Flow,
            id=custom_flow.id,
            name=custom_flow.name,
            ref_unit=unit_str
        )
        out_ex.amount = amount
        out_ex.unit = self.get_unit_ref(unit_str)
        out_ex.flow_property = o.Ref(
            ref_type=o.RefType.FlowProperty,
            id="93a60a56-a3c8-11da-a746-0800200b9a66",
            name="Mass"
        )
        out_ex.is_quantitative_reference = True
        out_ex.internal_id = 1
        
        custom_proc.exchanges = [out_ex] + compiled_exchanges
        
        # Verify physical conservation of this compiled assembly
        is_bal, rep = self.verifier.verify_mass_balance(custom_proc)
        print(f"[Compiler] Mass balance verification for assembly '{name}': {'PASSED' if is_bal else 'FAILED'} (Discrepancy: {rep['discrepancy_kg']:.4f} kg)")
        
        # Put the compiled process in database
        self.client.put(custom_proc)
        
        # Generate references
        flow_ref = o.Ref(ref_type=o.RefType.Flow, id=flow_id, name=custom_flow.name, ref_unit=unit_str)
        proc_ref = o.Ref(ref_type=o.RefType.Process, id=proc_id, name=custom_proc.name)
        
        self.created_processes.append(proc_ref)
        self.assembly_processes[custom_flow.name] = proc_ref
        
        return flow_ref, proc_ref

    def cleanup(self):
        """Deletes all custom product systems, processes, and flows created during compilation."""
        print("[Compiler] Cleaning up temporary compilation entities from database...")
        # 1. Delete product systems first
        for sys_ref in self.created_product_systems:
            try:
                self.client.delete(sys_ref)
            except Exception as e:
                print(f"  [Warning] Failed to delete product system {sys_ref.id}: {e}")
                
        # 2. Delete processes
        for proc_ref in self.created_processes:
            try:
                self.client.delete(proc_ref)
            except Exception as e:
                print(f"  [Warning] Failed to delete process {proc_ref.id}: {e}")
                
        # 3. Delete flows
        for flow_ref in self.created_flows:
            try:
                self.client.delete(flow_ref)
            except Exception as e:
                print(f"  [Warning] Failed to delete flow {flow_ref.id}: {e}")
