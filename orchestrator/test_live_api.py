"""
Live Gemini API Connection & Tool Calling Test
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from agent import InfraGPTAgent


def test_live_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"[TEST] Testing Gemini with API Key: {api_key[:8]}...")
    
    agent = InfraGPTAgent(model_name="gemini-2.5-flash")
    print(f"[TEST] Live LLM Mode: {agent.is_live_llm}")

    invoked = []
    def on_tool(name, args):
        invoked.append((name, args))
        print(f"[TOOL INVOKED] {name}({args})")

    # Hindi / Hinglish prompt to test true semantic understanding
    prompt = "Bhai production namespace me check karo koi dikkat to nahi hai?"
    print(f"\n[PROMPT] {prompt}\n")
    
    response = agent.send_message(prompt, on_tool_call=on_tool)
    print("\n[AI RESPONSE (ASCII CLEAN)]:")
    print(response.encode('ascii', errors='replace').decode('ascii'))


if __name__ == "__main__":
    test_live_gemini()
