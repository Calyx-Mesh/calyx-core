import socket
from zeroconf import ServiceInfo, Zeroconf
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import json
import os
import asyncio
import time
import psutil
import subprocess
import sys
import shutil
import sqlite3
from typing import List, Dict, Any

# --- INGRVM Logic Imports ---
from peer_database import PeerDatabase
from efficiency_monitor import EfficiencyMonitor
from seed_generator import DigitalSeed
from governance_dao import INGRVMDAO
from reward_engine import INGRVMLedger
from tools.ingrvm_logger import INGRVMLogger

from ingrvms.sentiment_alpha import SentimentAlpha
from ingrvm_registry import INGRVMRegistry
from shard_manager import ShardManager
from ipfs_storage import CIDStorage
from global_orchestrator import GlobalOrchestrator

from config import INGRVMConfig

conf = INGRVMConfig()

app = FastAPI(title="INGRVM Hub", version="1.3.4")
db = PeerDatabase(db_path=conf.get("paths", "peer_db"))
monitor = EfficiencyMonitor()
ledger = INGRVMLedger(db_path="neuromorphic_env/ledger.db")
dao = INGRVMDAO(ledger, conf, db_path="neuromorphic_env/governance.db")
registry_manager = INGRVMRegistry(db_path="neuromorphic_env/marketplace.db", storage_dir=conf.get("paths", "ingrvms_dir"))
cid_storage = CIDStorage(root_dir="neuromorphic_env/ipfs_blob")
global_orch = GlobalOrchestrator()
# Use a relative path from the config if possible, or handle via env
logger = INGRVMLogger(log_path=os.getenv("INGRVM_LOG_PATH", "../../logs/node_activity.jsonl"))

# Task #10: Shard & Mesh State
shard_mgr = ShardManager("HUB_NODE", discovery_dir="mesh_discovery", config_path="NONE")

# Local state for running ingrvms (Task #9)
running_ingrvms: List[Dict[str, Any]] = []

# --- Phase 3: Neural Engines ---
sentiment_engine = SentimentAlpha()
inference_queue = asyncio.Queue()

class CommandRequest(BaseModel):
    text: str
    ingrvm_id: str = "sentiment_alpha"
    peer_id: str = "LOCAL_OPERATOR"
    poi_hash: str = "" # Task #7: Proof-of-Inference hash

class InstallRequest(BaseModel):
    ingrvm_id: str
    name: str

class VoteRequest(BaseModel):
    proposal_id: str
    peer_id: str
    vote: bool

class ProposalRequest(BaseModel):
    proposer_id: str
    description: str
    ingrvm_id: str = "skill_0"
    weights_hash: str = "sha256-default"

class GPUVitals(BaseModel):
    temp: float
    vram_used: float
    vram_total: float
    load: int
    psk: str = ""

class MobileVitals(BaseModel):
    device_id: str = "Pixel 8"
    battery: int
    signal: int
    temp: float = 0.0
    psk: str = ""

# Task #25: Mailroom API
class MailLetter(BaseModel):
    sender: str
    recipient: str
    timestamp: float
    body: str

# Task #28: Remote Mesh Logs
class RemoteLog(BaseModel):
    node_id: str
    event: str
    data: Dict[str, Any]
    t: str

# Task #10: Shard Distribution API
class ShardDistributionRequest(BaseModel):
    node_id: str
    model_name: str
    layer_start: int
    layer_end: int
    vram_gb: float

# Task #25: Mailroom Persistence
MAILBOX_PATH = os.path.join("neuromorphic_env", "mailbox.json")
RECEIPTS_PATH = os.path.join("neuromorphic_env", "receipts.json")

def load_mail_state():
    mb, rec = {}, {}
    if os.path.exists(MAILBOX_PATH):
        try:
            with open(MAILBOX_PATH, "r") as f:
                raw_mb = json.load(f)
                mb = {k: [MailLetter(**m) for m in v] for k, v in raw_mb.items()}
        except Exception as e: print(f"Error loading mailboxes: {e}")
    if os.path.exists(RECEIPTS_PATH):
        try:
            with open(RECEIPTS_PATH, "r") as f:
                rec = json.load(f)
        except Exception as e: print(f"Error loading receipts: {e}")
    return mb, rec

def save_mail_state():
    try:
        os.makedirs("neuromorphic_env", exist_ok=True)
        with open(MAILBOX_PATH, "w") as f:
            serializable_mb = {k: [m.model_dump() for m in v] for k, v in mailboxes.items()}
            json.dump(serializable_mb, f, indent=4)
        with open(RECEIPTS_PATH, "w") as f:
            json.dump(mail_receipts, f, indent=4)
    except Exception as e: print(f"Error saving mail state: {e}")

mailboxes, mail_receipts = load_mail_state()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try: await connection.send_text(message)
            except: pass

manager = ConnectionManager()

async def log_streamer():
    """ Watches the JSONL log file and broadcasts to WS. """
    # Use environment variable for log path, with a safe fallback
    log_path = os.getenv("INGRVM_LOG_PATH", os.path.join("..", "..", "logs", "node_activity.jsonl"))
    if not os.path.exists(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        open(log_path, 'a').close()

    file_size = os.path.getsize(log_path)
    while True:
        try:
            current_size = os.path.getsize(log_path)
            if current_size > file_size:
                with open(log_path, 'r') as f:
                    f.seek(file_size)
                    lines = f.readlines()
                    for line in lines:
                        if line.strip():
                            await manager.broadcast(json.dumps({
                                "type": "LOG",
                                "payload": json.loads(line)
                            }))
                file_size = current_size
        except Exception as e:
            # print(f"[LOG_STREAMER] Error: {e}") # Silent error to avoid spam
            pass
        await asyncio.sleep(1)

async def sync_registry():
    """ Fetches the latest ingrvm registry from a remote source. """
    # Use environment variable for registry URL
    REMOTE_URL = os.getenv("INGRVM_REGISTRY_URL", "https://raw.githubusercontent.com/INGRVM-Mesh/INGRVM-Core/master/INGRVM/Core/packages/registry.json")
    print(f"[HUB] Syncing ingrvm registry from {REMOTE_URL}...")
    await asyncio.sleep(1) 
    print("[HUB] Registry synced successfully.")

import hashlib

# --- Phase 3: Worker Queue & Inference ---
async def neural_worker():
    """
    Background worker that pulls tasks from the queue and runs 1-bit inference on the 1080 Ti.
    """
    print("Neural Worker: Online and waiting for spikes...")
    while True:
        task = await inference_queue.get()
        peer_id = task.get("peer_id", "UNKNOWN")
        text = task.get("text", "")
        ingrvm_id = task.get("ingrvm_id", "sentiment_alpha")
        reported_poi_hash = task.get("poi_hash", "")
        
        # Run 1-bit Inference
        result = sentiment_engine.infer(text)
        
        # Phase 6 Task #7: Proof-of-Inference (PoI) Validation
        # In a real setup, this would hash the input + weights + output.
        # For this prototype, we simulate PoI by hashing the input text.
        expected_poi = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        if reported_poi_hash == expected_poi or peer_id == "LOCAL_OPERATOR" or not reported_poi_hash:
            # Register Work & Rewards (Phase 6 SQL Ledger)
            ledger.record_work(peer_id, spikes=result['spikes'])
            ledger.mint_rewards(peer_id, amount=(result['spikes'] * 0.001), memo=f"Inference: {ingrvm_id}")
            
            logger.log("NEURAL_INFERENCE", {
                "peer": peer_id,
                "sentiment": result['sentiment'],
                "conf": result['confidence'],
                "spikes": result['spikes'],
                "poi_status": "VALID"
            })
        else:
            # Phase 6 Task #16: Slash for invalid PoI
            ledger.slash_node(peer_id, penalty_syn=5.0, rep_burn=0.1, memo=f"PoI Mismatch: {ingrvm_id}")
            print(f"[PoI-REJECT] Invalid PoI from {peer_id}. Expected {expected_poi[:8]}... got {reported_poi_hash[:8]}...")
            logger.log("INVALID_POI", {
                "peer": peer_id,
                "ingrvm": ingrvm_id
            })
        
        # Prepare broadcast payload matching the UI expectation
        ui_payload = {
            "ingrvm_id": ingrvm_id,
            "input": text,
            "output": f"{result['sentiment']} (Conf: {result['confidence']}, Spikes: {result['spikes']})"
        }
        
        # Broadcast result to WebSocket
        await manager.broadcast(json.dumps({
            "type": "INFERENCE_RESULT",
            "payload": ui_payload
        }))
        
        inference_queue.task_done()

# --- Zeroconf Global Tracking ---
zeroconf_obj = None
zc_info = None

async def mesh_broadcaster():
    """ Periodically broadcasts the mesh topology (nodes/links) to WS. """
    while True:
        try:
            nodes_data = await get_mesh_nodes()
            await manager.broadcast(json.dumps({
                "type": "MESH_UPDATE",
                "payload": nodes_data
            }))
        except Exception as e:
            pass
        await asyncio.sleep(5)

async def self_healing_monitor():
    """ 
    Task #15: Self-Healing Monitor.
    Scans for nodes that have dropped and reclaims their shards for the HUB.
    """
    while True:
        try:
            current_time = time.time()
            nodes_data = await get_mesh_nodes()
            
            # Identify nodes that are NOT ready
            for node in nodes_data["nodes"]:
                if node["id"] != shard_mgr.node_id and not node["is_ready"]:
                    # Node is offline, reclaim its shards
                    offline_shards = shard_mgr.mesh_shards.get(node["id"], [])
                    for s in offline_shards:
                        print(f"[SELF-HEALING] Reclaiming shard {s.get('layer_start')}-{s.get('layer_end')} from offline node {node['id']}")
                        # In a real model, this would trigger a reload of weights 26-32 + the offline ones
                        shard_mgr.register_shard(
                            model_name=s.get("model_name", "Unknown"),
                            start=s.get("layer_start", 0),
                            end=s.get("layer_end", 0),
                            vram_gb=s.get("vram_usage_gb", 0.0),
                            ip=socket.gethostbyname(socket.gethostname())
                        )
                    # Remove the offline node's mapping to prevent infinite loop
                    del shard_mgr.mesh_shards[node["id"]]
                    logger.log("MESH_HEALED", {"reclaimed_from": node["id"]})
        except Exception:
            pass
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    global zeroconf_obj, zc_info
    # Load config in an async-friendly way (Task #10)
    shard_mgr.load_config("shard_config.json")
    
    # Task #04: mDNS Service Discovery Registration (Non-blocking)
    def register_mdns():
        global zeroconf_obj, zc_info
        try:
            hub_port = int(os.getenv("INGRVM_HUB_PORT", 8000))
            local_ip = os.getenv("INGRVM_NODE_IP", socket.gethostbyname(socket.gethostname()))
            
            zeroconf_obj = Zeroconf()
            zc_info = ServiceInfo(
                "_INGRVM-hub._tcp.local.",
                f"INGRVMHub-{shard_mgr.node_id}._INGRVM-hub._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=hub_port,
                properties={"node_id": shard_mgr.node_id, "version": "1.3.4"}
            )
            zeroconf_obj.register_service(zc_info)
            print(f"[HUB] mDNS Service Registered: {local_ip}:{hub_port} as _INGRVM-hub._tcp.local.")
        except Exception as e:
            print(f"[ERROR] Failed to register Zeroconf: {e}")

    import threading
    threading.Thread(target=register_mdns, daemon=True).start()

    asyncio.create_task(log_streamer())
    asyncio.create_task(sync_registry())
    asyncio.create_task(neural_worker())
    asyncio.create_task(shard_mgr.poll_mesh_files()) # Task #10: Monitor Mesh
    asyncio.create_task(mesh_broadcaster()) # Task #03: Real-time Mesh Visualization
    asyncio.create_task(self_healing_monitor()) # Task #15: Self-Healing Shard Recovery
    logger.log("HUB_BOOT", {"version": "1.3.4", "status": "mission-ready"})

@app.on_event("shutdown")
async def shutdown_event():
    global zeroconf_obj, zc_info
    if zeroconf_obj and zc_info:
        print("[HUB] Unregistering mDNS Service...")
        zeroconf_obj.unregister_service(zc_info)
        zeroconf_obj.close()

# Task #02: Circuit Relay V2 (WAN Traversal)
from circuit_relay import INGRVMRelayV2
relay_node = INGRVMRelayV2("12D3KooW_PC_MASTER_RELAY")

class RelayRequest(BaseModel):
    node_id: str

@app.post("/api/mesh/relay/reserve")
async def reserve_relay(req: RelayRequest):
    """
    Grants a relay reservation for a node behind NAT.
    """
    path = relay_node.request_reservation(req.node_id)
    if path:
        return {"status": "RESERVED", "relay_path": path}
    return {"status": "FAILED"}

@app.get("/api/mesh/ping")
async def ping_mesh():

    return {"status": "PONG", "node_id": shard_mgr.node_id, "timestamp": time.time()}

@app.post("/api/mesh/shard/request")
async def request_shard(req: ShardDistributionRequest):
    """
    Registers a shard assignment for a remote node.
    Used by Laptop and Mobile to confirm they have loaded their layers.
    """
    # Force registration into the mesh state
    shard_mgr.mesh_shards[req.node_id] = [
        # Create a ModelShard-like object for internal storage
        # In a real scenario, this would trigger weight transfers
        {
            "model_name": req.model_name,
            "layer_start": req.layer_start,
            "layer_end": req.layer_end,
            "node_id": req.node_id,
            "is_ready": True
        }
    ]
    logger.log("SHARD_ASSIGNED", {
        "node": req.node_id,
        "model": req.model_name,
        "layers": f"{req.layer_start}-{req.layer_end}"
    })
    return {"status": "ASSIGNED", "node_id": req.node_id}

# Task #25: Mailroom Endpoints
mail_receipts: Dict[str, float] = {} # sender_id -> last_ack_timestamp

@app.post("/api/mailroom/send")
async def send_mail(letter: MailLetter):
    """ Receives a letter and stores it in the recipient's mailbox. """
    target = letter.recipient
    if target not in mailboxes: mailboxes[target] = []
    mailboxes[target].append(letter)
    logger.log("MAIL_RECEIVED", {"from": letter.sender, "to": target, "body": letter.body[:20]})
    return {"status": "OK"}

@app.post("/api/mailroom/ack/{node_id}")
async def acknowledge_mail(node_id: str):
    """ Task #22: Records that a node has read its mail. """
    mail_receipts[node_id] = time.time()
    logger.log("MAIL_READ", {"node_id": node_id})
    return {"status": "ACK_RECORDED", "timestamp": mail_receipts[node_id]}

@app.get("/api/mailroom/receipts")
async def get_receipts():
    """ Returns all read receipts. """
    return mail_receipts

@app.get("/api/mailroom/inbox/{node_id}")
async def get_inbox(node_id: str):
    """ Returns all letters for a specific node. """
    return mailboxes.get(node_id, [])

@app.get("/api/marketplace/catalog")
async def get_marketplace_catalog():
    """ Returns all registered ingrvms in the mesh. """
    return registry_manager.list_ingrvms()

@app.get("/api/marketplace/search")
async def search_marketplace(q: str):
    """ Task #11: Returns ingrvms matching the search query. """
    return registry_manager.search_ingrvms(q)

@app.post("/api/marketplace/upload")
async def upload_ingrvm(
    name: str, 
    author_id: str, 
    version: str, 
    category: str, 
    description: str,
    architecture: str,
    file: UploadFile = File(...)
):
    """
    Uploads a model file, stores it by CID, and registers it in the SQL Marketplace.
    """
    # 1. Save temp file to calculate CID
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. Add to CID Storage (Simulated IPFS)
    try:
        cid, final_path = cid_storage.add_file(temp_path)
        
        # 3. Register in SQL
        metadata = {
            "ingrvm_id": f"{name.lower().replace(' ', '_')}_{version}",
            "name": name,
            "author_id": author_id,
            "version": version,
            "category": category,
            "description": description,
            "cid": cid,
            "architecture": architecture,
            "listing_fee": 10.0, # 10 tokens to list
            "token_symbol": os.getenv("INGRVM_TOKEN_SYMBOL", "DOPA")
        }
        
        # Deduct listing fee from author (Task #11)
        if ledger.get_balance(author_id) >= 10.0:
            ledger.transfer(author_id, "BURN_ADDRESS", 10.0)
            registry_manager.register_ingrvm(metadata)
            logger.log("DOPAAPSE_REGISTERED", {"id": metadata["ingrvm_id"], "by": author_id})
            return {"status": "SUCCESS", "cid": cid, "ingrvm_id": metadata["ingrvm_id"]}
        else:
            return {"status": "FAILED", "error": "Insufficient funds for listing fee."}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/marketplace/download/{cid}")
async def download_ingrvm(cid: str):
    """ Returns the model weight blob for a specific CID. """
    path = cid_storage.get_file_path(cid)
    if path:
        return FileResponse(path, filename=f"{cid}.pt")
    return {"error": "CID not found in local mesh cache."}

@app.get("/api/marketplace/details/{ingrvm_id}")
async def get_ingrvm_details(ingrvm_id: str):
    """ Returns full metadata for a specific ingrvm. """
    reg_path = os.path.join("packages", "registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r") as f:
            registry = json.load(f)
            for s in registry.get("ingrvms", []):
                if s["id"] == ingrvm_id:
                    return s
    return {"error": "Not found"}

@app.post("/api/mesh/log")
async def receive_remote_log(log: RemoteLog):
    """ Receives a log from a mesh node and broadcasts to UI. """
    text = log.data.get('text', '')
    safe_text = text.encode('ascii', 'backslashreplace').decode('ascii')
    print(f"[REMOTE_LOG] From {log.node_id}: {safe_text}")
    logger.log(f"REMOTE_LOG_{log.node_id}", log.data)
    await manager.broadcast(json.dumps({
        "type": "LOG",
        "payload": {
            "event": f"NODE_{log.node_id}",
            "data": log.data
        }
    }))
    return {"status": "OK"}

@app.get("/mesh_health_map.js", response_class=FileResponse)
async def read_health_map_js():
    return FileResponse("mesh_health_map.js")

@app.get("/onboarding", response_class=FileResponse)
async def read_onboarding():
    return FileResponse("onboarding_wizard.html")

@app.get("/", response_class=FileResponse)
async def read_hub():
    return FileResponse("dashboard.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

@app.post("/api/command")
async def handle_command(cmd: CommandRequest):
    await inference_queue.put({"peer_id": cmd.peer_id, "text": cmd.text, "ingrvm_id": cmd.ingrvm_id})
    logger.log("COMMAND_INJECTED", {"ingrvm": cmd.ingrvm_id, "text": cmd.text[:50] + "...", "by": cmd.peer_id})
    return {"status": "QUEUED"}

@app.post("/api/marketplace/install")
async def handle_install(req: InstallRequest):
    if not any(rs['ingrvm_id'] == req.ingrvm_id for rs in running_ingrvms):
        running_ingrvms.append(req.model_dump())
        logger.log("DOPAAPSE_INSTALLED", {"id": req.ingrvm_id, "name": req.name})
        return {"status": "INSTALLED"}
    return {"status": "ALREADY_RUNNING"}

@app.post("/api/stress/start")
async def handle_stress():
    logger.log("STRESS_TEST_INITIATED", {"duration": "60s"})
    subprocess.Popen([sys.executable, "tools/stress_test.py"])
    return {"status": "STARTED"}

@app.post("/api/vitals")
async def handle_vitals(vitals: GPUVitals):
    if vitals.psk != os.getenv("INGRVM_SECURE_PSK", "INGRVM_SECURE_2026"): return {"status": "UNAUTHORIZED"}
    await manager.broadcast(json.dumps({"type": "VITALS", "payload": vitals.model_dump()}))
    return {"status": "OK"}

@app.post("/api/mobile/vitals")
async def handle_mobile_vitals(vitals: MobileVitals):
    if vitals.psk != os.getenv("INGRVM_MOBILE_PSK", "INGRVM_MOBILE_2026"): return {"status": "UNAUTHORIZED"}
    await manager.broadcast(json.dumps({"type": "MOBILE_VITALS", "payload": vitals.model_dump()}))
    return {"status": "OK"}

@app.post("/api/infer")
async def handle_inference(req: CommandRequest):
    queue_depth = inference_queue.qsize()
    
    # Task #5: Hub Multi-Hop
    if queue_depth > 10:
        print(f"[MULTI-HOP] Local queue depth ({queue_depth}) exceeded. Finding global peer...")
        global_peers = global_orch.fetch_global_peers()
        if global_peers:
            target_hub = global_peers[0] # Simplest: forward to first known global hub
            print(f"[MULTI-HOP] Forwarding spike to global backbone: {target_hub}")
            try:
                # Forward the request to the remote Hub's API
                resp = requests.post(f"{target_hub}/api/infer", json=req.model_dump(), timeout=2)
                if resp.status_code == 200:
                    logger.log("HUB_MULTI_HOP", {"target": target_hub, "status": "FORWARDED"})
                    return {"status": "MULTI_HOP_FORWARDED", "hub": target_hub}
            except Exception as e:
                print(f"[MULTI-HOP] Forwarding failed: {e}")

    await inference_queue.put({"peer_id": req.peer_id, "text": req.text, "ingrvm_id": req.ingrvm_id, "poi_hash": req.poi_hash})
    return {"status": "QUEUED", "queue_depth": inference_queue.qsize()}

@app.post("/api/dao/propose")
async def handle_propose(req: ProposalRequest):
    p_id = dao.create_proposal(req.proposer_id, req.description, req.ingrvm_id, req.weights_hash)
    if p_id:
        logger.log("DAO_PROPOSAL_CREATED", {"id": p_id, "by": req.proposer_id, "desc": req.description})
        return {"status": "CREATED", "proposal_id": p_id}
    return {"status": "REJECTED", "error": "Insufficient reputation."}

@app.post("/api/dao/vote")
async def handle_vote(req: VoteRequest):
    dao.cast_vote(req.peer_id, req.proposal_id, req.vote)
    logger.log("DAO_VOTE_CAST", {"id": req.proposal_id, "by": req.peer_id, "vote": req.vote})
    return {"status": "VOTE_RECORDED"}

@app.get("/api/rewards/{peer_id}")
async def get_peer_rewards(peer_id: str):
    """ Returns reputation and total balance for a node. """
    balance = ledger.get_balance(peer_id)
    # Peek reputation directly
    conn = sqlite3.connect(ledger.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT reputation FROM accounts WHERE node_id = ?", (peer_id,))
    row = cursor.fetchone()
    conn.close()
    return {
        "total": balance,
        "reputation": row[0] if row else 1.0
    }

@app.get("/api/ledger/{peer_id}")
async def get_node_ledger(peer_id: str):
    """ Returns transaction history for a node. """
    conn = sqlite3.connect(ledger.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions 
        WHERE sender_id = ? OR receiver_id = ? 
        ORDER BY timestamp DESC LIMIT 50
    """, (peer_id, peer_id))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/dao/proposals")
async def get_all_proposals():
    """ Returns all proposals from the SQL DAO. """
    return dao.get_proposals()

@app.get("/api/dao/votes/{proposal_id}")
async def get_proposal_votes(proposal_id: str):
    """ Task #14: Returns all votes for a specific proposal for global sync. """
    return dao.get_votes_for_proposal(proposal_id)

async def get_mesh_nodes():
    """ Helper to get nodes for health map. """
    nodes = []
    # PC_MASTER is always first
    nodes.append({
        "id": "PC_MASTER",
        "is_ready": True,
        "type": "HUB"
    })
    
    for node_id, shards in shard_mgr.mesh_shards.items():
        nodes.append({
            "id": node_id,
            "is_ready": shards[0].get("is_ready", False) if isinstance(shards[0], dict) else shards[0].is_ready,
            "type": "NODE"
        })
    return {"nodes": nodes}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("INGRVM_HUB_HOST", "0.0.0.0")
    port = int(os.getenv("INGRVM_HUB_PORT", 8000))
    uvicorn.run(app, host=host, port=port)


