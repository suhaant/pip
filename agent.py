import time
import anthropic
from tools import TOOL_DEFINITIONS, dispatch_tool

# --- API Key ---
API_KEY = "xxx"  # Replace with your actual key

client = anthropic.Anthropic(api_key=API_KEY)

# --- Agent mission prompt ---
SYSTEM_PROMPT = """
You are an autonomous safety manager for an industrial assembly line.

Your mission: minimize injury risk across all stations.

You have access to tools to query violation logs, shift schedules, and production quotas.
Use them proactively to investigate safety status — do not wait to be asked.

Your investigation process:
1. Start by checking violations across all zones
2. Identify which zone has the most violations or a spike
3. Investigate that zone fur ther — check its shift schedule and production quotas
4. Form a hypothesis about the root cause
5. If you find an actionable insight, send a recommendation to the appropriate person
6. Be specific: name the zone, the pattern, the likely cause, and the recommended action

Think step by step. Use multiple tool calls to build a complete picture before concluding.
"""

# --- Run one agent investigation cycle ---
def run_agent():
    print("\n" + "="*60)
    print("🤖 Agent investigation starting...")
    print("="*60)

    messages = [
        {"role": "user", "content": "Begin your safety investigation now."}
    ]

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages
        )

        # Add assistant response to message history
        messages.append({"role": "assistant", "content": response.content})

        # Check stop reason
        if response.stop_reason == "end_turn":
            # No more tool calls — print final response
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n📋 Agent conclusion:\n{block.text}")
            break

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"\n🔧 Calling: {tool_name}({tool_input})")
                    result = dispatch_tool(tool_name, tool_input)

                    if isinstance(result, list):
                        print(f"   → {len(result)} records returned")
                    else:
                        print(f"   → {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            # Add tool results to message history
            messages.append({"role": "user", "content": tool_results})

    print("\n" + "="*60)
    print("✅ Investigation complete.")
    print("="*60)


# --- Main loop ---
if __name__ == "__main__":
    print("🚀 Safety Agent started. Running every 5 minutes.")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            run_agent()
            print("\n⏳ Next investigation in 5 minutes...")
            time.sleep(300)
        except KeyboardInterrupt:
            print("\n🛑 Agent stopped.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Retrying in 60 seconds...")
            time.sleep(60)