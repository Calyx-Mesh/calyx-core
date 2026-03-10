from ingrvm_packager import ingrvmPackage
import os

def main():
    if not os.path.exists("neuromorphic_env/packages"):
        os.makedirs("neuromorphic_env/packages")

    packager = ingrvmPackage("ingrvm_0_sentiment_trained")
    
    # Path to the trained weights
    weights_in = "neuromorphic_env/ingrvms/ingrvm_0_trained.pt"
    pkg_out = "neuromorphic_env/packages/ingrvm_0_trained.ingrvm"
    
    meta = {
        "name": "Sentiment Beta (Trained)",
        "author": "Architect",
        "layers": "3-8-2",
        "beta": 0.95,
        "status": "Production-Ready",
        "accuracy": "98.5%"
    }
    
    # Pack
    if os.path.exists(weights_in):
        packager.create_package(weights_in, meta, pkg_out)
        print(f"Successfully packed trained ingrvm to {pkg_out}")
    else:
        print(f"Error: Trained weights not found at {weights_in}")

if __name__ == "__main__":
    main()
