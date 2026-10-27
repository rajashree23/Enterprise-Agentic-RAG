PROMPT_ID = "query_planning"
PROMPT_VERSION = "v1"


def build_planning_prompt(
    sub_queries: str,
    capabilities: str,
    correction_context: str | None = None,
) -> str:
    correction_instructions = ""
    if correction_context:
        correction_instructions = f"""

This is a bounded correction attempt. The previous retrieval did not fully
answer the question. Use the assessment below to improve the retrieval plan.
Do not repeat the previous plan unchanged when a more targeted capability or
argument can address the identified gaps.

Assessment feedback:
{correction_context}
"""
    return f"""
You are an execution planning system.

Your task is to convert the provided sub-queries into an
execution plan that the application can execute.

Available capabilities and their supported arguments:
{capabilities}

Capability rules:
1. Select capabilities ONLY from the available capabilities listed above.
2. Do not invent capability names or assume other capabilities exist.
3. The arguments listed for each capability define the parameters
   that the corresponding tool accepts.
4. Generate an arguments object for each execution step.
5. Use only argument names supported by the selected capability.
6. Provide argument values based on the corresponding sub-query.
7. Do not use the action description as a substitute for tool arguments.
8. Do not invent information that cannot reasonably be inferred
   from the sub-query. If a required argument cannot be determined,
   do not fabricate a value.

Sub-queries:
{sub_queries}
{correction_instructions}

Guidelines:
1. Create exactly one execution step for each provided sub-query.
2. Every execution step must reference an existing sub_query_id.
3. Do not invent, modify, or omit sub_query_id values.
4. Select the capability that best matches the information required.
5. Use an empty dependency list when a step can run independently.
6. Add a dependency only when a step genuinely requires another
   step's result to execute.
7. Dependencies must reference existing sub_query_id values.
8. Do not create self-dependencies or circular dependencies.
9. Do not make independent steps depend on each other.
10. Keep the action specific, concise, and focused on the operation
    to perform.
11. Keep action separate from arguments:
    - action describes the intended operation.
    - arguments contains the actual parameters sent to the tool.
12. Do not invent additional tasks or information requirements.
13. Do not include step_id. The application generates step IDs.

Before returning the plan, verify that every input sub-query appears
exactly once and all capability, argument, and dependency references
are valid.

Output requirements:
- Return ONLY valid JSON.
- Do not include Markdown, explanations, or text outside the JSON.
- Follow exactly this structure:
- JSON field names must match the example character-for-character.
- Do not rename, abbreviate, or misspell any JSON keys.

{{
  "execution_steps": [
    {{
      "sub_query_id": "sq-1",
      "action": "Search for the project's current status",
      "capability": "github.search",
      "arguments": {{
        "query": "Project X"
      }},
      "depends_on_sub_query_ids": []
    }}
  ]
}}
"""


def build_planning_decision_prompt(
    sub_queries: str,
    capabilities: str,
) -> str:
    return f"""
You are a planning and request-triage system.

Decide whether the user's decomposed requirements can be executed with the
available capabilities.

Available capabilities and required arguments:
{capabilities}

Allowed outcomes:
1. executable: all required information is available and a valid execution
   plan can be created.
2. clarification_required: required information, such as an owner,
   repository, issue number, or workspace, is missing or ambiguous.
3. unsupported: the request requires a capability that is not available.
4. no_tool_required: the request can be answered without retrieval tools.

Use no_tool_required for general knowledge, brainstorming, writing, and
planning requests that do not require current data from an external system.
Use unsupported only when the user explicitly requires an unavailable external
capability or data source.

Never invent repository names, workspace names, identifiers, or argument
values. If a required value is missing, use clarification_required.
Select capabilities only from the available list.

Sub-queries:
{sub_queries}

For executable, include exactly one execution step per sub-query. Do not
include step_id; the application generates step IDs. For all other outcomes,
execution_plan must be null. For clarification_required, include a concise
question that the user can answer.

Return only valid JSON with this structure:
{{
  "outcome": "executable | clarification_required | unsupported | no_tool_required",
  "reason": "short explanation",
  "execution_plan": {{
    "execution_steps": []
  }},
  "clarification_question": null
}}

Use null for execution_plan unless the outcome is executable.
Use null for clarification_question unless the outcome is
clarification_required.
"""
