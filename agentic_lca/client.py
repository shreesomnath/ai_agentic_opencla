import olca_ipc as ipc
import olca_schema as o
import time

class LcaExecutor:
    """
    Executes and automates Life Cycle Assessment (LCA) workflows
    by interfacing programmatically with an active OpenLCA IPC server.
    """
    def __init__(self, port=8080):
        self.port = port
        self.client = ipc.Client(port)
        
    def find_process(self, query):
        """Find processes matching a query string."""
        processes = list(self.client.get_descriptors(o.Process))
        return [p for p in processes if query.lower() in p.name.lower()]
        
    def find_product_system(self, query):
        """Find product systems matching a query string."""
        systems = list(self.client.get_descriptors(o.ProductSystem))
        return [s for s in systems if query.lower() in s.name.lower()]
        
    def find_impact_method(self, query):
        """Find impact assessment methods matching a query string."""
        methods = list(self.client.get_descriptors(o.ImpactMethod))
        return [m for m in methods if query.lower() in m.name.lower()]
        
    def get_process(self, process_id):
        """Retrieve the full details of a process by its ID."""
        return self.client.get(o.Process, process_id)
        
    def get_flow(self, flow_id):
        """Retrieve the full details of a flow by its ID."""
        return self.client.get(o.Flow, flow_id)
        
    def calculate(self, system_id, method_id, amount=1.0, parameter_redefs=None):
        """Run an LCA calculation for the given system ID and method ID with optional parameter overrides."""
        setup = o.CalculationSetup()
        setup.target = o.Ref(ref_type=o.RefType.ProductSystem, id=system_id)
        setup.impact_method = o.Ref(ref_type=o.RefType.ImpactMethod, id=method_id)
        setup.amount = amount
        if parameter_redefs:
            setup.parameters = parameter_redefs
            
        result = self.client.calculate(setup)
        
        # Poll for results
        start_time = time.time()
        while True:
            state = result.get_state()
            if state.error:
                raise RuntimeError(f"Calculation error: {state.error}")
            if state.is_ready:
                break
            if time.time() - start_time > 120: # 2 minutes timeout
                result.dispose()
                raise TimeoutError("LCA calculation timed out.")
            time.sleep(0.5)
            
        # Parse impacts
        impact_values = result.get_total_impacts()
        results = []
        if impact_values:
            for val in impact_values:
                category = val.impact_category
                results.append({
                    "category_name": category.name,
                    "category_id": category.id,
                    "amount": val.amount,
                    "unit": category.ref_unit if category.ref_unit else ""
                })
        result.dispose()
        return results

    def create_product_system(self, process_id, name=None):
        """Create a new product system from a process ID."""
        process_ref = o.Ref(ref_type=o.RefType.Process, id=process_id)
        # In openLCA 2.x API, create_product_system is typically client.create_product_system(process_ref)
        system = self.client.create_product_system(process_ref)
        if name and system:
            system.name = name
            # Update descriptor in DB
            self.client.put(system)
        return system
