try:
    from google import genai
    print("SUCCESS: 'from google import genai' worked.")
    
    if hasattr(genai, 'configure'):
        print("INFO: 'genai.configure' exists. This looks like the OLD SDK or a wrapper.")
    else:
        print("INFO: 'genai.configure' does NOT exist. This is the NEW SDK context.")

    if hasattr(genai, 'Client'):
        print("INFO: 'genai.Client' exists. This is the NEW SDK.")

except ImportError as e:
    print(f"FAILURE: 'from google import genai' failed: {e}")
