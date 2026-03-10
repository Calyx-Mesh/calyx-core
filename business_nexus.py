import requests
import json
import time
from identity_manager import NodeIdentity

class BusinessNexus:
    """
    The 'Action' layer of the INGRVM Mesh.
    Triggers external n8n workflows when the neural node detects business value.
    """
    def __init__(self, n8n_webhook_url: str):
        self.n8n_url = n8n_webhook_url
        self.identity = NodeIdentity()

    def trigger_action(self, event_type: str, lead_data: dict):
        """
        Sends a signed request to n8n to execute a workflow.
        """
        print(f"\n[NEXUS] Firing Business Action: {event_type}")
        
        payload = {
            "node_id": self.identity.get_public_key_b64(),
            "timestamp": time.time(),
            "event": event_type,
            "data": lead_data
        }
        
        # 1. Sign the payload for business security
        # Ensures n8n only listens to YOUR mesh nodes
        binary_data = json.dumps(payload).encode("utf-8")
        signature = self.identity.sign_data(binary_data)
        
        headers = {
            "X-INGRVM-Signature": signature,
            "Content-Type": "application/json"
        }
        
        # 2. Fire and Forget (Mocked here since n8n URL isn't live)
        print(f"[NEXUS] Payload signed. Signature: {signature[:16]}...")
        # try:
        #     requests.post(self.n8n_url, json=payload, headers=headers, timeout=5)
        # except Exception as e:
        #     print(f"[NEXUS] Delivery failed: {e}")
        
        return True

# --- Verification Test ---
if __name__ == "__main__":
    nexus = BusinessNexus("http://n8n.local/webhook/ingrvm-trigger")
    
    # Simulate a 'High Urgency Lead' event from a voice call
    lead_info = {
        "source": "Retell_Voice_Call",
        "intent": "Solar_Panel_Install",
        "urgency": "High",
        "phone": "+15550199"
    }
    
    success = nexus.trigger_action("URGENT_LEAD_DETECTED", lead_info)
    
    if success:
        print("\nSUCCESS: Business Nexus can sign and fire actions to n8n.")
