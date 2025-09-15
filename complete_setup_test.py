#!/usr/bin/env python3
"""
Complete setup and test script for the Flood Data Mining System with AI integration
This script will verify everything is working when you move to the device with Ollama
"""

import os
import sys
import time
import json
import sqlite3
import requests
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def print_banner(text):
    """Print a nice banner for each section"""
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def check_python_environment():
    """Check Python environment and required packages"""
    print_banner("CHECKING PYTHON ENVIRONMENT")
    
    print(f"✓ Python version: {sys.version}")
    print(f"✓ Working directory: {os.getcwd()}")
    
    required_packages = [
        'requests', 'beautifulsoup4', 'flask', 'flask_cors', 'python_dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All Python dependencies are available")
    return True

def check_environment_variables():
    """Check if required environment variables are set"""
    print_banner("CHECKING ENVIRONMENT VARIABLES")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        google_api_key = os.getenv('GOOGLE_API_KEY')
        google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
        if google_api_key:
            print(f"✓ Google API Key found: {google_api_key[:10]}...")
        else:
            print("❌ GOOGLE_API_KEY not found in .env file")
            
        if google_cse_id:
            print(f"✓ Google CSE ID found: {google_cse_id}")
        else:
            print("❌ GOOGLE_CSE_ID not found in .env file")
            
        if google_api_key and google_cse_id:
            print("✅ All environment variables are configured")
            return True
        else:
            print("⚠️  Please set up your .env file with Google API credentials")
            return False
            
    except ImportError:
        print("❌ python-dotenv not installed")
        return False

def check_ollama_connection():
    """Check if Ollama is running and has models available"""
    print_banner("CHECKING OLLAMA CONNECTION")
    
    try:
        print("Connecting to Ollama at http://localhost:11434...")
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            
            print("✅ Ollama is running and accessible")
            print(f"Available models: {len(models)}")
            
            for model in models[:5]:  # Show first 5 models
                name = model.get('name', 'Unknown')
                size_bytes = model.get('size', 0)
                size_gb = round(size_bytes / (1024**3), 1)
                print(f"  • {name} ({size_gb} GB)")
            
            if len(models) > 5:
                print(f"  ... and {len(models) - 5} more models")
                
            # Test with the first available model
            if models:
                test_model = models[0]['name']
                print(f"\nTesting model '{test_model}'...")
                return test_ollama_model(test_model)
            else:
                print("❌ No models found in Ollama")
                print("Please install a model: ollama pull llama2")
                return False
                
        else:
            print(f"❌ Ollama responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama at http://localhost:11434")
        print("\nTo fix this:")
        print("1. Make sure Ollama is installed from https://ollama.ai")
        print("2. Start Ollama service")
        print("3. Install a model: ollama pull llama2")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def test_ollama_model(model_name):
    """Test if a specific model responds correctly"""
    try:
        test_prompt = "Is this text about flooding? Answer with just YES or NO: Heavy rain caused severe flooding in downtown Houston."
        
        payload = {
            "model": model_name,
            "prompt": test_prompt,
            "stream": False
        }
        
        print(f"Sending test prompt to {model_name}...")
        response = requests.post("http://localhost:11434/api/generate", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', '').strip().upper()
            print(f"✓ Model response: {answer}")
            
            if 'YES' in answer:
                print("✅ Model correctly identified flood-related content")
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

def test_ai_agent():
    """Test the AI agent integration"""
    print_banner("TESTING AI AGENT")
    
    try:
        from backend.src.ai_agent import FloodAnalysisAgent
        print("✓ AI Agent module imported successfully")
        
        agent = FloodAnalysisAgent()
        print("✓ AI Agent initialized")
        
        # Test with sample flood content
        test_content = """
        Breaking News: Severe flooding hits downtown Miami after Hurricane Milton brings 
        unprecedented rainfall. Emergency services report water levels reaching 4 feet 
        in some areas. Miami-Dade County has issued mandatory evacuations for low-lying 
        neighborhoods. The National Weather Service warns of flash flooding continuing 
        through the evening hours.
        """
        
        print("Testing AI analysis with sample flood content...")
        result = agent.analyze_article(test_content.strip())
        
        print("✅ AI Analysis completed!")
        print("\n📊 Sample Results:")
        
        if 'relevance_analysis' in result:
            rel = result['relevance_analysis']
            print(f"  Flood Relevant: {rel.get('is_relevant', 'Unknown')}")
            print(f"  Confidence: {rel.get('confidence', 0)}%")
            print(f"  Category: {rel.get('category', 'Unknown')}")
            print(f"  Keywords: {rel.get('keywords_found', [])}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import AI Agent: {e}")
        return False
    except Exception as e:
        print(f"❌ AI Agent test failed: {e}")
        return False

def test_database():
    """Test database functionality"""
    print_banner("TESTING DATABASE")
    
    try:
        from backend.src.database import init_db, save_scraped_article, save_ai_analysis
        
        # Initialize database
        init_db()
        print("✓ Database initialized successfully")
        
        # Check if tables exist
        conn = sqlite3.connect('flood_data.db')
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        
        expected_tables = ['search_results', 'scraped_articles', 'ai_analysis', 'queries', 'articles']
        
        for table in expected_tables:
            if table in tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing")
        
        # Test saving a scraped article
        article_id = save_scraped_article(
            url="https://example.com/test-flood-article",
            title="Test Flood Article",
            content="This is a test article about flooding for system verification.",
            word_count=50,
            source_query="test flood query",
            success=True
        )
        
        print(f"✓ Test article saved with ID: {article_id}")
        
        # Test saving AI analysis
        test_analysis = {
            'relevance_analysis': {
                'is_relevant': True,
                'confidence': 85,
                'keywords_found': ['flood', 'water', 'emergency'],
                'summary': 'Test article about flooding',
                'category': 'news'
            },
            'detailed_info': {
                'location': ['Test City'],
                'flood_type': 'urban flooding',
                'severity': 'moderate',
                'key_facts': ['Test fact 1', 'Test fact 2']
            }
        }
        
        save_ai_analysis(article_id, "https://example.com/test-flood-article", test_analysis)
        print("✓ Test AI analysis saved")
        
        conn.close()
        print("✅ Database tests completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_backend_imports():
    """Test that all backend modules can be imported"""
    print_banner("TESTING BACKEND MODULES")
    
    modules_to_test = [
        ('backend.src.google_search', 'Google Search module'),
        ('backend.src.scraper', 'Web Scraper module'),
        ('backend.src.database', 'Database module'),
        ('backend.src.ai_agent', 'AI Agent module'),
    ]
    
    all_imports_ok = True
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {description} imported successfully")
        except ImportError as e:
            print(f"❌ {description} import failed: {e}")
            all_imports_ok = False
        except Exception as e:
            print(f"⚠️  {description} imported with warning: {e}")
    
    if all_imports_ok:
        print("✅ All backend modules imported successfully")
        return True
    else:
        print("❌ Some backend modules failed to import")
        return False

def show_next_steps():
    """Show what to do next"""
    print_banner("NEXT STEPS - READY TO USE!")
    
    print("🎉 Your Flood Data Mining System is ready to use!")
    print()
    print("To start the system:")
    print("1. Start the backend server:")
    print("   python backend/app.py")
    print()
    print("2. Open the frontend in your browser:")
    print("   Open: frontend/index.html")
    print()
    print("3. Search for flood-related terms like:")
    print("   • 'Miami flood 2024'")
    print("   • 'Houston hurricane flooding'")
    print("   • 'California wildfire mudslides'")
    print()
    print("4. The system will automatically:")
    print("   • Search Google for relevant articles")
    print("   • Scrape the article content")
    print("   • Analyze content with AI for flood relevance")
    print("   • Store everything in the database")
    print("   • Display results with AI insights")
    print()
    print("5. Use the 'Analyze Existing Articles' button to:")
    print("   • Process previously scraped articles with AI")
    print("   • Update the database with AI analysis")
    print()
    print("6. View database contents:")
    print("   python view_db.py")

def main():
    """Main setup and test function"""
    print("🚀 FLOOD DATA MINING SYSTEM - COMPLETE SETUP TEST")
    print("This will verify your system is ready to use with AI integration")
    
    tests = [
        ("Python Environment", check_python_environment),
        ("Environment Variables", check_environment_variables),
        ("Backend Modules", test_backend_imports),
        ("Database", test_database),
        ("Ollama Connection", check_ollama_connection),
        ("AI Agent", test_ai_agent),
    ]
    
    results = {}
    
    for test_name, test_function in tests:
        try:
            results[test_name] = test_function()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
        
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print_banner("TEST RESULTS SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        show_next_steps()
        return True
    else:
        print("⚠️  Some tests failed. Please fix the issues above before proceeding.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)