import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import ProgressBar
from seed_generator import DigitalSeed
from metabolism import NodeMetabolism

console = Console()

class CortexDashboard:
    """
    The Command Center for a INGRVM Node.
    Orchestrates all modules into a single, beautiful Solarpunk interface.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.seed = DigitalSeed(node_id)
        self.meta = NodeMetabolism()
        self.start_time = time.time()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        return layout

    def get_header(self):
        return Panel(f"[bold gold1]DOPAAPSE CORTEX v1.0.0[/bold gold1] | Node: [green]{self.node_id[:16]}...[/green]", style="white on #0A0F0D")

    def get_vitality_panel(self, reputation: float):
        plant = self.seed.generate_plant(reputation)
        return Panel(plant, title="Node Vitality (Living Seed)", border_style="green")

    def get_stats_panel(self):
        stats = self.meta.get_status()
        table = Table.grid(expand=True)
        table.add_row(f"Energy Level: [bold cyan]{stats['energy_level']}[/bold cyan]")
        table.add_row(f"Available Joules: [bold green]{stats['joules']} J[/bold green]")
        table.add_row(f"Reputation: [bold gold1]1.85[/bold gold1]") # Mocked
        table.add_row(f"Uptime: [white]{int(time.time() - self.start_time)}s[/white]")
        return Panel(table, title="Metabolic Stats", border_style="cyan")

    def get_ingrvms_panel(self):
        table = Table(box=None, expand=True)
        table.add_column("ingrvm", style="magenta")
        table.add_column("Status", justify="right")
        table.add_row("Sentiment Alpha", "[green]Online[/green]")
        table.add_row("Shard Manager", "[green]Active[/green]")
        table.add_row("Validator Gate", "[yellow]Auditing[/yellow]")
        return Panel(table, title="Active Neural ingrvms", border_style="magenta")

    def run(self):
        layout = self.generate_layout()
        
        with Live(layout, refresh_per_second=4, screen=True):
            while True:
                layout["header"].update(self.get_header())
                layout["left"].update(self.get_vitality_panel(reputation=1.85))
                layout["right"].split_column(
                    Layout(self.get_stats_panel()),
                    Layout(self.get_ingrvms_panel())
                )
                layout["footer"].update(Panel("[bold white]PRESS CTRL+C TO DISCONNECT FROM MESH[/bold white]", style="red on black"))
                time.sleep(0.5)

if __name__ == "__main__":
    # Test with current Node Identity
    NODE_ID = "4QbWtbA6DrtI/dc0h+9iX+73vuiLS+RReHZf9nEVNlc="
    dash = CortexDashboard(NODE_ID)
    try:
        dash.run()
    except KeyboardInterrupt:
        console.clear()
        console.print("[bold red]Node Offline. Mesh synchronization terminated.[/bold red]")

