"""
Test Script for ChatGPT Integration
Run this to verify the OpenAI API integration is working correctly
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from apps.authentication.models import Students, InternalExam
from apps import db

from apps import create_app
from apps.config import config_dict

app = create_app(config_dict["Debug"])

def test_openai_connection():
    """Test if OpenAI API key is configured and valid"""
    print("=" * 60)
    print("Testing OpenAI Connection")
    print("=" * 60)
    
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("\nPlease set it using:")
        print("  Windows: $env:OPENAI_API_KEY='your_key_here'")
        print("  Linux/Mac: export OPENAI_API_KEY='your_key_here'")
        return False
    
    if not api_key.startswith('sk-'):
        print("❌ Invalid API key format (should start with 'sk-')")
        return False
    
    print(f"✅ API Key found: {api_key[:15]}...{api_key[-4:]}")
    
    # Test actual connection
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Simple test request
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test successful' if you can read this."}],
            max_tokens=10
        )
        
        print(f"✅ OpenAI API connection successful!")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API Error: {str(e)}")
        return False

def test_database():
    """Test if database has required data"""
    print("\n" + "=" * 60)
    print("Testing Database")
    print("=" * 60)
    
    from apps.config import config_dict
    app = create_app(config_dict["Debug"])
    
    with app.app_context():
        # Check Students table
        student_count = Students.query.count()
        print(f"📊 Students in database: {student_count}")
        
        if student_count == 0:
            print("⚠️  Warning: No students found in database")
        else:
            print("✅ Students table populated")
        
        # Check InternalExam table
        exam_count = InternalExam.query.count()
        print(f"📊 Internal exam records: {exam_count}")
        
        if exam_count == 0:
            print("⚠️  Warning: No exam records found")
        else:
            print("✅ InternalExam table populated")
        
        # Check for sample data
        if exam_count > 0:
            sample = InternalExam.query.first()
            print(f"\n   Sample record:")
            print(f"   - Student ID: {sample.student_id}")
            print(f"   - English: {sample.eng_currPct}%")
            print(f"   - Maths: {sample.maths_currPct}%")
            print(f"   - Science: {sample.sci_currPct}%")
        
        return student_count > 0 and exam_count > 0

def test_endpoint():
    """Test the interpretation endpoint"""
    print("\n" + "=" * 60)
    print("Testing API Endpoint")
    print("=" * 60)
    
    from apps.config import config_dict
    app = create_app(config_dict["Debug"])
    # app = create_app()
    
    with app.app_context():
        # Get a sample student
        sample = InternalExam.query.first()
        
        if not sample:
            print("⚠️  Cannot test endpoint - no exam data available")
            return False
        
        print(f"Testing with Student ID: {sample.student_id}")
        
        with app.test_client() as client:
            response = client.get(f'/api/interpret_performance?student_id={sample.student_id}')
            
            if response.status_code == 200:
                data = response.get_json()
                print("✅ Endpoint working!")
                print(f"\n   AI Interpretation:")
                print(f"   {'-' * 55}")
                
                interpretation = data.get('interpretation', '')
                # Wrap text nicely
                words = interpretation.split()
                line = "   "
                for word in words:
                    if len(line) + len(word) + 1 > 60:
                        print(line)
                        line = "   " + word
                    else:
                        line += " " + word if line != "   " else word
                if line.strip():
                    print(line)
                
                print(f"   {'-' * 55}")
                return True
            else:
                data = response.get_json()
                print(f"❌ Endpoint error: {data.get('error', 'Unknown error')}")
                return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "ChatGPT Integration Test" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test 1: OpenAI Connection
    openai_ok = test_openai_connection()
    
    # Test 2: Database
    db_ok = test_database()
    
    # Test 3: Endpoint (only if previous tests passed)
    endpoint_ok = False
    if openai_ok and db_ok:
        endpoint_ok = test_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"{'✅' if openai_ok else '❌'} OpenAI API Connection")
    print(f"{'✅' if db_ok else '❌'} Database Setup")
    print(f"{'✅' if endpoint_ok else '❌'} API Endpoint")
    
    if openai_ok and db_ok and endpoint_ok:
        print("\n🎉 All tests passed! Integration is ready to use.")
        print("\nNext steps:")
        print("1. Add the AI interpretation button to your templates")
        print("2. Include ai_interpretation.js in your HTML")
        print("3. See CHATGPT_INTEGRATION.md for details")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
    
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
