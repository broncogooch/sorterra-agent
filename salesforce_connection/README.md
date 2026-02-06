# Salesforce Connection Package

This folder contains the tools, credentials, and instructions needed to connect your Agent (or Salesforce integration) to the SharePoint File Sorter.

## Contents

### 1. Credentials
*   **`private_key.pem`**: The private key used to sign authentication requests. Keep this SECURE.
*   **`selfsigned.crt`**: The public certificate (uploaded to Azure).

### 2. Tools
*   **`agent_tools.py`**: Python functions for the agent (`move_document`, `secure_move_document`, etc.).
*   **`sharepoint_client.py`**: The core logic library used by `agent_tools.py`.
*   **`requirements.txt`**: Python dependencies.

### 3. Instructions
*   **`agent_workflows.md`**: Guide on how the agent should think and act (Look -> Sort -> Act).
*   **`aws_setup_guide.md`**: Instructions for configuring the AWS/Azure environment.

## Quick Start
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set Environment Variables (see `aws_setup_guide.md`).
3.  Import `agent_tools` in your script:
    ```python
    from agent_tools import list_folder_contents
    files = list_folder_contents("/sites/YourSite/Shared Documents")
    ```
