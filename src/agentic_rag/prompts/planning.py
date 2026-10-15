PROMPT_ID = "query_planning"
PROMPT_VERSION = "v1"


def build_planning_prompt(sub_queries: str) -> str:
    return f"""
You are an execution planning system.

Your task is to convert the provided sub-queries into an
execution plan that the application can execute.

Sub-queries:
{sub_queries}

Guidelines:
1. Create exactly one execution step for each provided sub-query.
2. Every execution step must reference an existing sub_query_id.
3. Do not invent, modify, or omit sub_query_id values.
4. Select a capability that matches the information required:
   - github.search: search GitHub issues, pull requests, or repositories.
   - slack.search: search Slack messages and discussions.
   - notion.search: search Notion pages and documentation.
5. Do not invent capabilities outside the supported capabilities listed above.
6. Use an empty dependency list when a step can run independently.
7. Add a dependency only when a step genuinely requires the result
   of another step to execute.
8. Dependencies must reference existing sub_query_id values.
9. Do not create self-dependencies or circular dependencies.
10. Do not make independent steps depend on each other.
11. Keep the action specific, concise, and focused on the information
    requested by the sub-query.
12. Do not invent additional tasks or information requirements.
13. Do not include step_id. The application generates step IDs.

Follow these steps:
1. Identify the information each sub-query requires.
2. Select the appropriate capability for each sub-query.
3. Determine whether each sub-query requires results from another.
4. Build the execution steps with the appropriate dependencies.
5. Verify that every input sub-query appears exactly once and that
   all references and dependencies are valid.

Output requirements:
- Return ONLY valid JSON.
- Do not include Markdown, explanations, or text outside the JSON.
- Follow exactly this structure:

{{
  "execution_steps": [
    {{
      "sub_query_id": "sq-1",
      "action": "Search GitHub for relevant pull requests",
      "capability": "github.search",
      "depends_on_sub_query_ids": []
    }}
  ]
}}
"""
