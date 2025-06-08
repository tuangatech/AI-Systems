import json
import re
import logging

logger = logging.getLogger(__name__)
MAX_CHARS = 10000  # Define this according to your needs

def extract_json(text):
    """
    Extracts the LAST VALID JSON object from a string.
    Handles nested braces properly.
    """
    text = text[-MAX_CHARS:]
    
    # Find all potential JSON objects by looking for { and matching }
    json_objects = []
    
    # Find all opening brace positions
    for start_idx in range(len(text)):
        if text[start_idx] == '{':
            # Count braces from this position to find the matching closing brace
            brace_count = 0
            for end_idx in range(start_idx, len(text)):
                if text[end_idx] == '{':
                    brace_count += 1
                elif text[end_idx] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found matching closing brace
                        json_candidate = text[start_idx:end_idx+1]
                        json_objects.append(json_candidate)
                        break
    
    print(f"Found {len(json_objects)} JSON candidates")
    for i, candidate in enumerate(json_objects):
        print(f"Candidate {i}: {candidate[:100]}...")
    
    # Try to parse JSON objects from last to first
    for json_candidate in reversed(json_objects):
        try:
            parsed = json.loads(json_candidate)
            print(f"Successfully parsed JSON: {json_candidate}")
            return parsed
        except json.JSONDecodeError as e:
            print(f"Failed to parse: {json_candidate[:50]}... Error: {e}")
            continue
    
    print("No valid JSON objects found.")
    return None

# Simple fallback approach
def extract_json_simple(text):
    """
    Simple approach: find all complete JSON objects using regex
    """
    text = text[-MAX_CHARS:]
    
    # Find all potential JSON starts
    candidates = []
    
    # Look for all opening braces and find their matching closing braces
    for start_idx in range(len(text)):
        if text[start_idx] == '{':
            brace_count = 0
            for end_idx in range(start_idx, len(text)):
                if text[end_idx] == '{':
                    brace_count += 1
                elif text[end_idx] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        candidate = text[start_idx:end_idx+1]
                        candidates.append((start_idx, end_idx, candidate))
                        break
    
    # Filter out nested objects - keep only outermost ones
    outermost_candidates = []
    for i, (start1, end1, candidate1) in enumerate(candidates):
        is_nested = False
        for j, (start2, end2, candidate2) in enumerate(candidates):
            if i != j and start2 < start1 and end1 < end2:
                # candidate1 is nested inside candidate2
                is_nested = True
                break
        if not is_nested:
            outermost_candidates.append(candidate1)
    
    # print(f"Simple approach found {len(candidates)} total candidates")
    # print(f"Simple approach found {len(outermost_candidates)} outermost candidates")
    # for i, candidate in enumerate(outermost_candidates):
    #     print(f"Simple outermost candidate {i}: {candidate[:200]}...")
    
    # Try to parse from last to first
    for candidate in reversed(outermost_candidates):
        try:
            result = json.loads(candidate)
            return result
        except json.JSONDecodeError as e:
            print(f"Simple approach failed to parse: {e}")
            continue
    
    return None

# Test the function with your example
if __name__ == "__main__":
    test_string = '''            }
            }
            {"intent": "screen", "sector": "technology", "limit": 3, "metrics": ["peRatio", "pbRatio", "freeCashFlowYield"], "filters": {"price_under": 50, "dividendYield_gt": 0}}
            {"intent": "screen", "sector": "technology", "limit": 3, "metrics": ["peRatio", "'''
    
    print("Input string:")
    print(repr(test_string))
    print("\n")
    
    # result = extract_json(test_string)
    # print("Final Result:", result)
    
    # Let's also try the simpler regex approach
    print("\n--- Trying simpler approach ---")
    result2 = extract_json_simple(test_string)
    print("Simple approach result:", result2)