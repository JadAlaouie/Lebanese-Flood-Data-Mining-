#!/usr/bin/env python3
"""
Setup script for Ollama integration
"""

import subprocess
import sys
import requests
import time
import json

def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama command failed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Ollama is not installed or not in PATH")
        return False

def check_ollama_service():
    """Check if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama service is running")
            print(f"Available models: {[m['name'] for m in models]}")
            return True, models
        else:
            print("❌ Ollama service not responding properly")
            return False, []
    except requests.exceptions.ConnectionError:
        print("❌ Ollama service is not running at http://localhost:11434")
        return False, []
    except Exception as e:
        print(f"❌ Error checking Ollama service: {e}")
        return False, []

def install_model(model_name="llama2"):
    """Install a model in Ollama"""
    try:
        print(f"Installing model '{model_name}'...")
        print("This may take several minutes depending on your internet connection.")
        
        result = subprocess.run(['ollama', 'pull', model_name], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✓ Model '{model_name}' installed successfully")
            return True
        else:
            print(f"❌ Failed to install model '{model_name}':")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Model installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing model: {e}")
        return False

def test_model_response(model_name="llama2"):
    """Test if the model responds correctly"""
    try:
        print(f"Testing model '{model_name}'...")
        
        test_prompt = "Is this text about flooding? Answer with just YES or NO: Heavy rain caused flooding in the city center."
        
        payload = {
            "model": model_name,
            "prompt": test_prompt,
            "stream": False
        }
        
        response = requests.post("http://localhost:11434/api/generate", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', '').strip().upper()
            print(f"✓ Model response: {answer}")
            
            if 'YES' in answer:
                print("✓ Model correctly identified flood-related content")
                return True
            else:
                print("⚠️  Model response unexpected, but it's working")
                return True
        else:
            print(f"❌ Model test failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

def main():
    print("🚀 Ollama Setup for Flood Data Mining")
    print("=" * 50)
    
    # Step 1: Check if Ollama is installed
    if not check_ollama_installed():
        print("\nPlease install Ollama first:")
        print("1. Go to https://ollama.ai")
        print("2. Download and install Ollama for your OS")
        print("3. Restart this script")
        return False
    
    # Step 2: Check if service is running
    service_running, models = check_ollama_service()
    if not service_running:
        print("\nPlease start the Ollama service:")
        print("- On Windows: Ollama should start automatically after installation")
        print("- On macOS/Linux: Run 'ollama serve' in a terminal")
        print("Then restart this script")
        return False
    
    # Step 3: Check if we have a suitable model
    model_name = "llama2"
    has_model = any(model_name in m['name'] for m in models)
    
    if not has_model:
        print(f"\nModel '{model_name}' not found. Installing...")
        if not install_model(model_name):
            print("Failed to install model. You can try manually:")
            print(f"ollama pull {model_name}")
            return False
    
    # Step 4: Test the model
    if not test_model_response(model_name):
        return False
    
    print("\n🎉 Ollama setup complete!")
    print("\nYour AI agent is ready. You can now:")
    print("1. Run: python test_ai_integration.py")
    print("2. Start the backend: python backend/app.py")
    print("3. Use the web interface to search and analyze flood data")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)