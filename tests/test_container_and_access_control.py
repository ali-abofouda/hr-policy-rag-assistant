"""Unit tests for container configuration, Docker compose, and Google OAuth access control."""

import os
import unittest
from unittest.mock import MagicMock, patch

import yaml
from src.core import config
from app import is_auth_configured, verify_access_control

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestContainerAndAccessControl(unittest.TestCase):
    """Validate Dockerfile, docker-compose orchestration, and OAuth access control logic."""

    def test_dockerfile_contents(self):
        """Verify Dockerfile contains required production Cloud Run configurations."""
        dockerfile_path = os.path.join(PROJECT_DIR, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile must exist at project root.")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check Python 3.11 base image and Cloud Run port 8080
        self.assertIn("FROM python:3.11-slim", content)
        self.assertIn("EXPOSE 8080", content)
        self.assertIn("--server.port=8080", content)
        self.assertIn("--server.headless=true", content)

        # Check pre-warming of FastEmbed BM25 sparse model
        self.assertIn("SparseTextEmbedding", content)
        self.assertIn("Qdrant/bm25", content)

    def test_dockerignore_contents(self):
        """Verify .dockerignore excludes virtualenvs and local sensitive credentials."""
        dockerignore_path = os.path.join(PROJECT_DIR, ".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path), ".dockerignore must exist at project root.")

        with open(dockerignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("hrrenv/", content)
        self.assertIn(".env", content)
        self.assertIn("__pycache__/", content)

    def test_docker_compose_orchestration(self):
        """Verify docker-compose.yml defines app, ingest, and eval microservices."""
        compose_path = os.path.join(PROJECT_DIR, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path), "docker-compose.yml must exist at project root.")

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})
        self.assertIn("app", services)
        self.assertIn("ingest", services)
        self.assertIn("eval", services)

        # Ingestion and Evaluation should be assigned to the tools profile
        self.assertIn("tools", services["ingest"].get("profiles", []))
        self.assertIn("tools", services["eval"].get("profiles", []))

    def test_allowed_employee_emails_parsing(self):
        """Verify ALLOWED_EMPLOYEE_EMAILS parses comma-separated emails into lowercase list."""
        self.assertIsInstance(config.ALLOWED_EMPLOYEE_EMAILS, list)
        self.assertIn("mentordivesh@gmail.com", config.ALLOWED_EMPLOYEE_EMAILS)

    def test_is_auth_configured_local_fallback(self):
        """Verify is_auth_configured returns False in standard local development without secrets."""
        # Without an auth section in st.secrets, returns False
        with patch("streamlit.secrets", {}):
            self.assertFalse(is_auth_configured())

    def test_verify_access_control_open_mode(self):
        """Verify verify_access_control allows access when auth is not configured."""
        with patch("app.is_auth_configured", return_value=False):
            self.assertTrue(verify_access_control())

    def test_verify_access_control_authorized_user(self):
        """Verify verify_access_control grants access for whitelisted employee email."""
        mock_user = MagicMock()
        mock_user.is_logged_in = True
        mock_user.email = "mentordivesh@gmail.com"

        with patch("app.is_auth_configured", return_value=True), \
             patch("streamlit.user", mock_user):
            self.assertTrue(verify_access_control())

    def test_deploy_env_yaml_format(self):
        """Verify deploy.env.yaml.example contains valid YAML with required RAG settings."""
        deploy_env_path = os.path.join(PROJECT_DIR, "deploy.env.yaml.example")
        self.assertTrue(os.path.exists(deploy_env_path))

        with open(deploy_env_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("QDRANT_URL", data)
        self.assertIn("GEMINI_API_KEY", data)
        self.assertIn("LANGSMITH_TRACING", data)
        self.assertIn("ALLOWED_EMPLOYEE_EMAILS", data)

    def test_streamlit_secrets_template(self):
        """Verify .streamlit/secrets.toml.example exists and specifies /oauth2callback."""
        secrets_example_path = os.path.join(PROJECT_DIR, ".streamlit", "secrets.toml.example")
        self.assertTrue(os.path.exists(secrets_example_path))

        with open(secrets_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[auth]", content)
        self.assertIn("[auth.google]", content)
        self.assertIn("/oauth2callback", content)
        self.assertIn("cookie_secret", content)

    def test_deployment_scripts_exist(self):
        """Verify automated deployment scripts exist with gcloud run deploy and callback instructions."""
        sh_path = os.path.join(PROJECT_DIR, "commands", "deploy_cloud_run.sh")
        ps1_path = os.path.join(PROJECT_DIR, "commands", "deploy_cloud_run.ps1")
        self.assertTrue(os.path.exists(sh_path))
        self.assertTrue(os.path.exists(ps1_path))

        with open(sh_path, "r", encoding="utf-8") as f:
            content_sh = f.read()
        self.assertIn("gcloud", content_sh)
        self.assertIn("oauth2callback", content_sh)
        self.assertIn("--env-vars-file", content_sh)


if __name__ == "__main__":
    unittest.main()
