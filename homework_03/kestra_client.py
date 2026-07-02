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
        timeout: int = 15,
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

    @staticmethod
    def _normalize_flow(obj: Any) -> Any:
        ignore_keys = {
            "revision",
            "updated",
            "deleted",
        }

        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                if key in ignore_keys:
                    continue

                value = KestraClient._normalize_flow(value)

                if value in (None, "", {}, []):
                    continue

                cleaned[key] = value

            return {k: cleaned[k] for k in sorted(cleaned)}

        if isinstance(obj, list):
            return [KestraClient._normalize_flow(item) for item in obj]

        return obj

    @classmethod
    def _flows_equal(cls, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        return cls._normalize_flow(left) == cls._normalize_flow(right)

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

    def upsert_flow(self, yaml_file: str | Path) -> Dict[str, str]:
        parsed, _ = self._load_yaml(yaml_file)
        namespace = parsed["namespace"]
        flow_id = parsed["id"]

        existing = self.get_flow(namespace, flow_id)

        if existing is None:
            return self.create_flow(yaml_file)

        if self._flows_equal(existing, parsed):
            print(f"{namespace}.{flow_id} already up to date.")
            return {
                "action": "unchanged",
                "namespace": namespace,
                "flow_id": flow_id,
            }

        return self.update_flow(yaml_file)

    def register_flow(self, yaml_file: str | Path) -> Dict[str, str]:
        return self.upsert_flow(yaml_file)

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
        print(f"Execution State: {execution['state']['current']}")
        return execution