import os
import sys
import platform
import subprocess
import urllib.request
import time
import shutil

def run_command(cmd, shell=True):
    print(f"Running: {cmd}")
    try:
        subprocess.run(cmd, shell=shell, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        return False

def install_ollama():
    system = platform.system().lower()
    print(f"Detected OS: {platform.system()}")

    if system == "linux":
        print("Installing Ollama on Linux...")
        # Use official install script
        run_command("curl -fsSL https://ollama.com/install.sh | sh")
        
    elif system == "darwin":
        print("Installing Ollama on macOS...")
        # Check if brew exists
        if shutil.which("brew"):
            print("Homebrew detected. Installing via Homebrew...")
            run_command("brew install ollama")
        else:
            print("Homebrew not found. Downloading Ollama app zip...")
            zip_url = "https://ollama.com/download/Ollama-darwin.zip"
            zip_path = "Ollama-darwin.zip"
            try:
                urllib.request.urlretrieve(zip_url, zip_path)
                print("Extracting Ollama app to /Applications...")
                run_command(f"unzip -o {zip_path} -d /Applications")
                os.remove(zip_path)
                print("Ollama installed to /Applications/Ollama.app")
            except Exception as e:
                print(f"Failed to download and install macOS zip: {e}")
                print("Please download manually from https://ollama.com/download")
                return False
                
    elif system == "windows":
        print("Downloading Ollama installer for Windows...")
        exe_url = "https://ollama.com/download/OllamaSetup.exe"
        exe_path = os.path.join(os.environ.get("TEMP", "."), "OllamaSetup.exe")
        try:
            urllib.request.urlretrieve(exe_url, exe_path)
            print(f"Launching installer: {exe_path}")
            # Run the installer setup
            subprocess.Popen([exe_path])
            print("Ollama installer opened. Please complete the installer window.")
        except Exception as e:
            print(f"Failed to download installer: {e}")
            print("Please download manually from https://ollama.com/download")
            return False
    else:
        print(f"Unsupported OS: {system}")
        return False

    # Start Ollama service if offline (try starting in background)
    print("Checking if Ollama is running...")
    # Attempt to start service/app depending on OS
    if system == "darwin":
        # Launch Ollama app
        subprocess.Popen(["open", "-a", "Ollama"])
    elif system == "linux":
        # Start service
        subprocess.Popen(["systemctl", "start", "ollama"])
    
    # Wait for service to warm up
    time.sleep(3)

    # Pull recommended model
    print("\nPulling recommended local model 'qwen2.5-coder:7b' (4.7 GB)...")
    ollama_path = shutil.which("ollama") or "/usr/local/bin/ollama"
    if os.path.exists(ollama_path) or shutil.which("ollama"):
        run_command(f"{ollama_path} pull qwen2.5-coder:7b")
        print("\nOllama and model setup completed successfully!")
    else:
        # Check standard paths on macOS if brew wasn't used
        mac_app_path = "/Applications/Ollama.app/Contents/Resources/ollama"
        if system == "darwin" and os.path.exists(mac_app_path):
            run_command(f"{mac_app_path} pull qwen2.5-coder:7b")
            print("\nOllama and model setup completed successfully!")
        else:
            print("\nOllama binary not found in PATH yet. You may need to restart your terminal first, then run:")
            print("  ollama pull qwen2.5-coder:7b")

if __name__ == "__main__":
    install_ollama()
