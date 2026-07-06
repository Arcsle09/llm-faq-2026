For the homework, I completed the same tasks programmatically through the Kestra REST API instead of relying on the UI. The API-first approach maps closely to the UI workflow while making the process reproducible and suitable for automation. Kestra exposes endpoints for AI-assisted flow generation, flow registration and updates, execution, log retrieval, and execution monitoring, allowing the entire workflow lifecycle to be scripted.

The overall workflow I implemented was:

Generate a flow using AI Copilot
Call POST /api/v1/main/ai/generate/flow
Provide the natural language prompt and AI provider (for example, gemini-legacy)
Receive the generated YAML.
Save the generated YAML locally
Store the YAML under a local flows/ directory.
Parse the YAML to extract the namespace and flow ID.
Register or update the flow
If the flow does not exist, register it through the Flow API.
If it already exists and the YAML has changed, update it instead of recreating it.
Execute the flow
Trigger the registered flow through the Execution API.
Supply runtime inputs when required.
Monitor execution
Query execution status.
Retrieve execution logs through the Logs API for debugging and verification.

Using the REST APIs provided several advantages over the UI:

Automation: Entire homework can be rerun from a single Python script or notebook.
Reproducibility: The same sequence of API calls can be executed repeatedly without manual intervention.
Version control: Generated YAML files are stored locally and can be committed to Git.
Integration: The workflow can be incorporated into CI/CD pipelines or other Python applications.
Observability: Execution status and logs can be retrieved programmatically for automated validation and debugging.

While the homework demonstrates these features through the Kestra UI, the REST API provides equivalent functionality and is more appropriate for production scenarios where workflows are generated, deployed, executed, and monitored automatically rather than manually. Kestra is designed to support both UI-driven and API-driven orchestration, making it straightforward to transition from experimentation to automation.