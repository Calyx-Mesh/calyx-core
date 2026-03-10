/**
 * Task #10: Mesh Health Map
 * Visualizes the global state of the INGRVM nervous system.
 */

class MeshHealthMap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.nodes = {};
    }

    update(nodesData) {
        // Expected format: { nodes: [...], links: [...] }
        this.render(nodesData.nodes);
    }

    render(nodes) {
        this.container.innerHTML = "";
        
        // Create a grid layout for nodes
        const grid = document.createElement("div");
        grid.className = "grid grid-cols-2 md:grid-cols-4 gap-4 w-full";
        
        nodes.forEach(node => {
            const card = document.createElement("div");
            card.className = `p-4 rounded-xl border transition-all ${
                node.is_ready ? 'bg-chlorophyll/10 border-chlorophyll/30' : 'bg-red-900/10 border-red-500/30 opacity-50'
            }`;
            
            const statusColor = node.is_ready ? "text-chlorophyll" : "text-red-500";
            const statusText = node.is_ready ? "ONLINE" : "OFFLINE";
            
            card.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <div class="text-[10px] font-bold text-mist/80 uppercase">${node.label}</div>
                    <div class="text-[8px] font-black ${statusColor} animate-pulse">${statusText}</div>
                </div>
                <div class="text-[8px] text-mist/40 font-mono mb-3">${node.id.substring(0, 16)}...</div>
                
                <div class="space-y-1">
                    <div class="flex justify-between text-[7px] uppercase tracking-widest text-mist/30">
                        <span>Latency</span>
                        <span class="text-mist/60">${node.is_ready ? Math.floor(Math.random() * 50) + 10 : '--'}ms</span>
                    </div>
                    <div class="w-full bg-black/40 h-1 rounded-full overflow-hidden">
                        <div class="bg-chlorophyll h-full" style="width: ${node.is_ready ? '85%' : '0%'}"></div>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
        
        this.container.appendChild(grid);
    }
}

// Global instance if needed
window.MeshHealthMap = MeshHealthMap;

