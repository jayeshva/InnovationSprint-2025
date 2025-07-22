import os
import json
from typing import List, Dict, Any
from agent import compiled_graph 
from textwrap import shorten

from agentevals.trajectory.llm import (
    create_trajectory_llm_as_judge,
    TRAJECTORY_ACCURACY_PROMPT,
)

# 🧠 AWS Bedrock Model
os.environ["AWS_REGION"] = "us-east-1"

trajectory_evaluator = create_trajectory_llm_as_judge(
    prompt=TRAJECTORY_ACCURACY_PROMPT,
    model="bedrock:anthropic.claude-3-sonnet-20240229-v1:0",
)

# ✅ Test cases
test_cases = [
    {
        "input": "What is the leave policy for new joiners?",
        "expected_tools": ["HRPolicyRAG", "WebSearch"],
        "category": "policy_inquiry"
    },
    {
        "input": "Hello, how are you?",
        "expected_tools": [],
        "category": "greeting"
    },
    {
        "input": "Can you share the travel reimbursement policy?",
        "expected_tools": ["HRPolicyRAG"],
        "category": "policy_inquiry"
    },
]


def run_agent(question: str) -> List[Dict[str, Any]]:
    """Run the agent and collect trajectory in OpenAI messages format."""
    result = compiled_graph.invoke({"input": question, "tool_outputs": {}})
    outputs = [{"role": "user", "content": question}]
    
    used_tools = []

    for step in result.get("intermediate_steps", []):
        if "tool" in step:
            tool_name = step["tool"]
            used_tools.append(tool_name)
            outputs.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(step.get("args", {}))
                    }
                }]
            })
        if "output" in step:
            outputs.append({"role": "tool", "content": step["output"]})
    
    outputs.append({"role": "assistant", "content": result.get("output", "")})
    return outputs, used_tools

def match_tools(expected: List[str], used: List[str]) -> str:
    expected_set = set(expected)
    used_set = set(used)
    if not expected and not used:
        return "Not applicable"
    elif expected_set == used_set:
        return "Exact match"
    elif expected_set.issubset(used_set):
        return "Superset (extra tools)"
    elif used_set.issubset(expected_set):
        return "Subset (some tools missing)"
    else:
        return "Mismatch"

def main():
    results = []
    print("🚀 Starting Agent Evaluation (agentevals + Tool Match)")

    for test in test_cases:
        print(f"Running agent for: {test['input']}")
        trajectory, used_tools = run_agent(test["input"])
        eval_result = trajectory_evaluator(outputs=trajectory)
        tool_match_result = match_tools(test["expected_tools"], used_tools)
        
        results.append({
            "test_case": test,
            "trajectory": trajectory,
            "used_tools": used_tools,
            "evaluation": eval_result,
            "tool_match": tool_match_result
        })
        print("Evaluation result:", eval_result)

    # Save full result JSON
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Create Markdown report

    with open("evaluation_results.md", "w", encoding="utf-8") as f:
        f.write("## ✅ Agent Evaluation Report\n\n")
        
        for idx, item in enumerate(results, 1):
           test = item["test_case"]
           eval = item["evaluation"]
           correctness = str(eval.get("correctness", eval.get("score", "-")))
           latency = str(eval.get("latency", "-"))
           halluc = str(eval.get("hallucination_rate", "-"))
           tool_use = str(eval.get("tool_usage_success", "-"))
           tool_match = item.get("tool_match", "-")

           last_response = [msg["content"] for msg in item["trajectory"] if msg["role"] == "assistant"]
           output_str = shorten(last_response[-1], width=120, placeholder="...") if last_response else ""

           f.write(f"### 🔹 Test Case #{idx}\n")
           f.write(f"- **Input**: {test['input']}\n")
           f.write(f"- **Expected Tools**: {', '.join(test['expected_tools']) if test['expected_tools'] else '*(None)*'}\n")
           f.write(f"- **Category**: {test['category']}\n")
           f.write(f"- **Correctness**: ✅ {correctness}\n")
           f.write(f"- **Latency**: {latency}\n")
           f.write(f"- **Hallucination**: {halluc}\n")
           f.write(f"- **Tool Usage Success**: {tool_use}\n")
           f.write(f"- **Tool Match**: {tool_match}\n")
           f.write(f"- **Output**: {output_str}\n\n")
           f.write("---\n\n")
    

    print("\n✅ Evaluation complete. Saved to `evaluation_results.md` and `evaluation_results.json`.")

if __name__ == "__main__":
    main()
