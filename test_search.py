#!/usr/bin/env python3
"""
Test script for unified search functionality
Run this to test both OpenAI and Google search providers
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the search function
try:
    from tool_executor import execute_web_search, PREFERRED_SEARCH_PROVIDER
    print(f"✅ Successfully imported search functions")
    print(f"📋 Current search provider: {PREFERRED_SEARCH_PROVIDER}")
except ImportError as e:
    print(f"❌ Failed to import search functions: {e}")
    sys.exit(1)

def test_search_provider(provider_name, test_query="Latest news about Dubai taxi services"):
    """Test a specific search provider"""
    print(f"\n🔍 Testing {provider_name.upper()} search...")
    print(f"Query: {test_query}")
    print("-" * 50)
    
    # Temporarily set the provider for this test
    original_provider = os.environ.get("PREFERRED_SEARCH_PROVIDER", "openai")
    os.environ["PREFERRED_SEARCH_PROVIDER"] = provider_name
    
    # Reload the module to pick up the new environment variable
    import importlib
    import tool_executor
    importlib.reload(tool_executor)
    
    system_instruction = "You are an AI assistant. Provide a brief, factual answer based on search results."
    
    try:
        result = tool_executor.execute_web_search(test_query, system_instruction, f"test_{provider_name}")
        print(f"✅ {provider_name.upper()} Result:")
        print(result[:300] + "..." if len(result) > 300 else result)
        return True
    except Exception as e:
        print(f"❌ {provider_name.upper()} Error: {e}")
        return False
    finally:
        # Restore original provider
        os.environ["PREFERRED_SEARCH_PROVIDER"] = original_provider
        importlib.reload(tool_executor)

def main():
    print("🚀 Starting Search Provider Tests")
    print("=" * 50)
    
    # Test query
    test_query = "What are the latest developments in Dubai's transportation sector?"
    
    # Test OpenAI
    openai_success = test_search_provider("openai", test_query)
    
    # Test Google
    google_success = test_search_provider("google", test_query)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"OpenAI Search: {'✅ PASSED' if openai_success else '❌ FAILED'}")
    print(f"Google Search: {'✅ PASSED' if google_success else '❌ FAILED'}")
    
    # Environment check
    print(f"\n🔧 Environment Configuration")
    print("=" * 50)
    print(f"PREFERRED_SEARCH_PROVIDER: {os.getenv('PREFERRED_SEARCH_PROVIDER', 'NOT SET')}")
    print(f"OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"GOOGLE_API_KEY: {'✅ Set' if os.getenv('GOOGLE_API_KEY') else '❌ Missing'}")
    
    if openai_success and google_success:
        print("\n🎉 All tests passed! Your unified search system is working correctly.")
        print("💡 You can now switch between providers by changing PREFERRED_SEARCH_PROVIDER in your .env file")
    elif openai_success:
        print("\n⚠️  OpenAI search works, but Google search failed.")
        print("💡 Check your Google API key and the new google-genai library installation")
    elif google_success:
        print("\n⚠️  Google search works, but OpenAI search failed.")
        print("💡 Check your OpenAI API key")
    else:
        print("\n❌ Both search providers failed. Check your API keys and internet connection.")

if __name__ == "__main__":
    main()