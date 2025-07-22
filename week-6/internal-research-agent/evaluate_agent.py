import os
from agent import compiled_graph  # Your LangGraph agent
from langchain_aws import ChatBedrock
from langchain.evaluation.agents import AgentTrajectoryEvaluator
from langchain.evaluation.schema import AgentTrajectory


# AWS Bedrock Setup
os.environ["AWS_REGION"] = "us-east-1"

# Claude via Bedrock
llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    model_kwargs={"temperature": 0.0}
)

# Trajectory evaluator
evaluator = AgentTrajectoryEvaluator.from_llm(
    llm=llm,
    criteria=["correctness", "tool_use", "relevance", "conciseness"]
)

# Sample inputs
sample_inputs = [
    "What is the leave policy for new joiners?",
    "Compare our hiring trend with the industry average.",
    "Hello, how are you?",
]

results = []

for question in sample_inputs:
    print(f"\n🔍 Running agent on: {question}")
    run = compiled_graph.invoke({"input": question, "tool_outputs": {}})

    trajectory = AgentTrajectory.from_agent_action_return(run)

    eval_result = evaluator.evaluate_agent_trajectory(trajectory)
    results.append((question, eval_result))

# Save results
with open("evaluation_results.md", "w") as f:
    for q, r in results:
        f.write(f"### Question: {q}\n")
        for k, v in r.items():
            f.write(f"- **{k}**: {v}\n")
        f.write("\n---\n")

print("\n✅ Evaluation complete using `langchain==0.3.26`. Saved to `evaluation_results.md`.")
