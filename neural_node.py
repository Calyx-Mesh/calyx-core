import trio
import os
import sys
from lib_node import INGRVMNode, INGRVMMobileNode

if __name__ == "__main__":
    # Determine config from environment or default to shard_config.json
    config_name = os.getenv("INGRVM_SHARD_CONFIG", "shard_config.json")
    mobile_mode = os.getenv("INGRVM_MOBILE_MODE", "false").lower() == "true"
    
    if mobile_mode:
        node = INGRVMMobileNode(config_name=config_name)
    else:
        node = INGRVMNode(config_name=config_name)
        
    try:
        trio.run(node.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Node Error: {e}")
        import traceback
        traceback.print_exc()

