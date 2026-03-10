import os
import sys
import subprocess
import shutil
import platform

def print_step(msg):
    print(f"\n>>> [INSTALLER] {msg}")

def check_python_version():
    print_step("Checking Python Version...")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"❌ Error: Python 3.10+ required. Found {v.major}.{v.minor}")
        sys.exit(1)
    print(f"✅ Python {v.major}.{v.minor} detected.")

def check_cuda():
    print_step("Checking for NVIDIA GPU (CUDA)...")
    try:
        # Simple check using nvidia-smi
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ NVIDIA GPU detected. Will install CUDA-enabled torch.")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠️  No NVIDIA GPU found. Installing CPU-only version (Slower).")
        return False

def install_dependencies(has_cuda):
    print_step("Installing Dependencies...")
    
    # Core requirements
    pkgs = [
        "snntorch", "libp2p", "trio", "msgpack", 
        "cryptography", "fastapi", "uvicorn", 
        "requests", "pydantic", "rich", "numpy", "matplotlib"
    ]
    
    # 1. Install generic packages
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)
    
    # 2. Install Torch (Flavor depends on hardware)
    print_step("Installing PyTorch...")
    if has_cuda:
        # Install CUDA 11.8 compatible torch
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu118"
        ])
    else:
        # CPU only
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ])

def setup_directories():
    print_step("Initializing Node Directory Structure...")
    dirs = [
        "neuromorphic_env/ingrvms", 
        "neuromorphic_env/packages", 
        "neuromorphic_env/proto"
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"Created {d}/")

def main():
    print("========================================")
    print("   DOPAAPSE NODE INSTALLER v1.0.0        ")
    print("   'Wake up your hardware.'             ")
    print("========================================")
    
    check_python_version()
    has_cuda = check_cuda()
    
    # Setup Env
    install_dependencies(has_cuda)
    setup_directories()
    
    print("\n========================================")
    print("✅ INSTALLATION COMPLETE")
    print("========================================")
    print("Run the system check:")
    print("  python neuromorphic_env/preflight.py")
    print("\nLaunch your node:")
    print("  python neuromorphic_env/master_node.py")

if __name__ == "__main__":
    main()

