import os
from pathlib import Path
from typing import Any, Dict, Optional
import requests
import yaml
from dotenv import load_dotenv

load_dotenv()


class KestraClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 50,
    ):
        self.base_url = (base_url or os.getenv("KESTRA_URL", "http://127.0.0.1:8080")).rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()
        self.session.auth = (
            username or os.environ["KESTRA_USER"],
            password or os.environ["KESTRA_PASSWORD"],
        )

    # ------------------------
    # Internal helpers
    # ------------------------

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        response = self.session.request(
            method=method,
            url=self._url(endpoint),
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _load_yaml(path: str | Path) -> tuple[Dict[str, Any], str]:
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)

        if not isinstance(parsed, dict):
            raise ValueError(f"YAML file {path} must contain a flow object")

        if "namespace" not in parsed or "id" not in parsed:
            raise ValueError(f"YAML file {path} must contain 'namespace' and 'id'")

        return parsed, content

    # ------------------------
    # Flow helpers
    # ------------------------

    def get_flow(self, namespace: str, flow_id: str) -> Optional[Dict[str, Any]]:
        response = self.session.get(
            self._url(f"/api/v1/main/flows/{namespace}/{flow_id}"),
            timeout=self.timeout,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()



    def generate_flow(self,
                      user_prompt: str,
                      provider_id: str,
                      namespace: str,
                      output_dir: str,
                      conversation_id: str = ""):
        """
        Generate a Kestra flow using AI, save it locally, and register it.

        Returns:
            Path to the generated YAML file.
        """

        payload = {
            "conversationId": conversation_id,
            "userPrompt": user_prompt,
            "yaml": "",
            "namespace": namespace,
            "providerId": provider_id,
        }

        response = self._request(
            "POST",
            f"/api/v1/main/ai/generate/flow",
            headers={
                "Accept": "application/yaml",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        flow_yaml = response.text

        parsed = yaml.safe_load(flow_yaml)

        flow_id = parsed["id"]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"{flow_id}_kestra.yaml"

        file_path.write_text(flow_yaml, encoding="utf-8")

        self.register_flow(str(file_path))

        return file_path

    def create_flow(self, yaml_file: str | Path) -> Dict[str, str]:
        parsed, content = self._load_yaml(yaml_file)
        namespace = parsed["namespace"]
        flow_id = parsed["id"]

        self._request(
            "POST",
            "/api/v1/main/flows",
            headers={"Content-Type": "application/x-yaml"},
            data=content,
        )

        print(f"Registered {namespace}.{flow_id}")
        return {
            "action": "created",
            "namespace": namespace,
            "flow_id": flow_id,
        }

    def update_flow(self, yaml_file: str | Path) -> Dict[str, str]:
        parsed, content = self._load_yaml(yaml_file)
        namespace = parsed["namespace"]
        flow_id = parsed["id"]

        self._request(
            "PUT",
            f"/api/v1/main/flows/{namespace}/{flow_id}",
            headers={"Content-Type": "application/x-yaml"},
            data=content,
        )

        print(f"Updated {namespace}.{flow_id}")
        return {
            "action": "updated",
            "namespace": namespace,
            "flow_id": flow_id,
        }

    def register_flow(self, yaml_file):
        parsed, content = self._load_yaml(yaml_file)

        namespace = parsed["namespace"]
        flow_id = parsed["id"]

        response = self.session.get(
            f"{self.base_url}/api/v1/main/flows/{namespace}/{flow_id}"
        )

        if response.status_code == 404:
            self._request(
                "POST",
                "/api/v1/main/flows",
                headers={"Content-Type": "application/x-yaml"},
                data=content,
            )
            print(f"Registered {namespace}.{flow_id}")
        else:
            print(f'Flow {namespace}.{flow_id} already exists')
        
    # ------------------------
    # Execution helpers
    # ------------------------

    def execute_flow(
        self,
        namespace: str,
        flow_id: str,
        inputs: Optional[Dict[str, Any]] = None,
        wait: bool = True,
    ) -> Dict[str, Any]:
        response = self._request(
            "POST",
            f"/api/v1/main/executions/{namespace}/{flow_id}",
            params={"wait": str(wait).lower()},
            data=inputs or {},
        )

        execution = response.json()
        return execution
    
    from typing import Optional


    def get_execution_logs(self,
                       execution_id: str,
                        level: str = "INFO",
                        task_run_id: Optional[str] = None,
                        attempt: Optional[int] = None):
        """
        Retrieve logs for a Kestra execution.

        Args:
            execution_id: Execution ID.
            level: Minimum log level (default: INFO).
                Valid values: TRACE, DEBUG, INFO, WARN, ERROR
            task_run_id: Filter logs for a specific task run.
            attempt: Filter by execution attempt.

        Returns:
            List of log entries.
        """

        params = {
            "minLevel": level.upper(),
        }

        if task_run_id:
            params["taskRunId"] = task_run_id

        if attempt is not None:
            params["attempt"] = attempt

        response = self._request(
            "GET",
            f"/api/v1/main/logs/{execution_id}",
            params=params,
        )

        return response.json()