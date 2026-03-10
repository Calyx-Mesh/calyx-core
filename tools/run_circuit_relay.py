import trio
import os
import sys
from pathlib import Path

# Add Core to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from circuit_relay import INGRVMRelayV2

async def main():
    """
    Task #02: Standalone Circuit Relay Server.
    Provides WAN traversal for nodes behind restrictive NATs.
    """
    relay_id = os.getenv("INGRVM_RELAY_ID", "12D3KooW_MASTER_RELAY_V2")
    port = int(os.getenv("INGRVM_RELAY_PORT", 60000))
    
    print(f"📡 [WAN] Launching INGRVM Circuit Relay...")
    relay = INGRVMRelayV2(relay_id, port=port)
    
    async with trio.open_nursery() as nursery:
        # Run the reservation cleanup loop
        nursery.start_soon(relay.run_cleanup_loop)
        
        print(f"✅ [WAN] Relay active and listening for reservations.")
        # Keep alive
        await trio.sleep_forever()

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        print("\n[WAN] Shutting down Relay.")
