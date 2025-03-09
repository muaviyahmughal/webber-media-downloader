import time
from groq import Groq
import json
import hashlib
import os
from pathlib import Path

class CodeAnalyzer:
    """Analyze code using Groq's Qwen2.5-Coder model with caching"""
    
    def __init__(self):
        self.client = Groq(api_key="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")
        self.model = "mixtral-8x7b-32768"  # Using Mixtral for code analysis
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_key(self, code, file_type):
        """Generate a cache key from code and file type"""
        content = f"{code}{file_type}{self.model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key):
        """Get cached analysis if available"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            print("Using cached analysis...")
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def _cache_response(self, cache_key, response):
        """Cache the analysis response"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(response, f)
    
    def analyze_code(self, code, file_type):
        """Analyze code with caching support"""
        cache_key = self._get_cache_key(code, file_type)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached
            
        print(f"Analyzing {file_type} code using {self.model}...")
        prompt = f"""Analyze this {file_type} code and suggest improvements. Format your response exactly as shown:

ANALYSIS
[Write your detailed analysis here, including:
- Code structure and organization
- Potential issues or bugs
- Performance considerations
- Best practices violations
- Security concerns]

IMPROVED CODE
[Provide the complete improved version here with all suggested changes implemented]

Here's the code to analyze:

{code}
"""
        try:
            print("Sending request to Groq API...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a code analysis expert. Analyze code and respond in this exact format:

ANALYSIS
[Analysis should include:
- Code structure review
- Best practices evaluation
- Performance considerations
- Potential bugs or issues
- Security concerns (if any)
- Suggested improvements]

IMPROVED CODE
[Complete improved version with all suggested changes]"""},
                    {"role": "user", "content": f"Analyze this {file_type} code:\n{code}"}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Extract response content
            response_text = response.choices[0].message.content
            
            # Extract just the improved code part (skip the "```python" marks if present)
            response_text = response_text.replace("```python", "").replace("```", "")
            
            # Parse response into analysis and improved code
            parts = response_text.split("\nIMPROVED CODE\n")
            if len(parts) == 2:
                analysis = parts[0].replace("ANALYSIS\n", "").strip()
                improved_code = parts[1].strip()
            else:
                # Try alternative format that might be in the response
                parts = response_text.split("\nHere is an improved version")
                if len(parts) == 2:
                    analysis = parts[0].replace("ANALYSIS\n", "").strip()
                    improved_code = parts[1].split(":", 1)[1].strip() if ":" in parts[1] else parts[1].strip()
                else:
                    analysis = response_text.strip()
                    improved_code = code  # Keep original if parsing fails
                
            result = {
                "analysis": analysis,
                "improved_code": improved_code
            }
            
            # Cache the result
            self._cache_response(cache_key, result)
            return result
            
        except Exception as e:
            print(f"Analysis failed: {str(e)}")
            return {
                "analysis": f"Error analyzing code: {str(e)}",
                "improved_code": code  # Return original code on error
            }

def test_analyzer():
    """Test the code analyzer with a simple example"""
    
    analyzer = CodeAnalyzer()
    
    test_code = """
def process_user_data(user_input):
    # Process user input and return results
    result = []
    for i in range(len(user_input)):
        item = user_input[i]
        if item:
            result.append(item.strip().lower())
    
    if len(result) > 0:
        return result
    else:
        return None
    """
    
    print("\nTesting code analysis...")
    print("Sample code:")
    print("-" * 40)
    print(test_code)
    print("-" * 40)
    
    start_time = time.time()
    try:
        result = analyzer.analyze_code(test_code, "python")
        elapsed = time.time() - start_time
        
        print("\nAnalysis Results:")
        print("=" * 40)
        print("Analysis:")
        print(result["analysis"])
        print("\nImproved Code:")
        print(result["improved_code"])
        print("=" * 40)
        print(f"\nCompleted in {elapsed:.1f}s")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    print("Testing Groq code analysis...")
    test_analyzer()
