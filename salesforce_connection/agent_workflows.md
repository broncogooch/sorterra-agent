# Agent Workflows for SharePoint

This document describes how an AI Agent should interact with the SharePoint File Sorter tools (`agent_tools.py`).

## Core Concepts
The agent operates in a **Loop**:
1.  **Look**: Inspect the incoming file queue.
2.  **Sort**: Decide where a file should go based on its content or metadata (handled by the agent's reasoning).
3.  **Act**: Move the file, potentially securing it or creating new folders.

## Tool References
All tools are available in `agent_tools.py`.

### 1. The "Look" Phase
**Goal**: Understand what work needs to be done.

*   **`list_folder_contents(folder_url)`**: Use this to see the "Inbox".
    *   *Agent Thought*: "I see 5 files in `/sites/Site/Shared Documents/Upload Folder`."
*   **`get_folder_hierarchy(folder_url)`**: Use this to understand the existing filing cabinet structure.
    *   *Agent Thought*: "I need to know what folders already exist in the user's library so I don't create duplicates."

### 2. The "Sort" Phase (Internal Reasoning)
**Goal**: Decide the destination.

*   *Agent Thought*: "File `invoice_123.pdf` belongs in 'Finance/Invoices'."
*   *Agent Thought*: "File `performance_review.docx` is sensitive. It came from 'Secure Uploads' and must stay secure."

### 3. The "Act" Phase
**Goal**: Execute the move.

#### Scenario A: Standard Move
For regular files that inherit permissions from their destination.
*   **Tool**: `move_document(file_url, dest_folder)`
*   *Example*: Moving a public newsletter to a "Newsletters" folder.

#### Scenario B: Secure Move (The "Secure Uploads" Workflow)
For files that have strict permission requirements (e.g., HR, Legal, Finance) where the file MUST retain specific access rules regardless of the destination folder's settings.
*   **Tool**: `secure_move_document(file_url, dest_folder, source_permissions_folder)`
*   *Key*: You must know the "Source Folder" that defines the correct permissions (e.g., `/sites/Site/Shared Documents/Secure Uploads`).

#### Scenario C: Organization
If the destination doesn't exist or needs to be highlighted.
*   **Tool**: `create_directory(folder_url, color_hex="1")`
*   *Color Codes*:
    *   `0`: Yellow (Default)
    *   `1`: Dark Red (Important/Testing)
    *   `2`: Dark Orange
    *   `3`: Dark Green
    *   `6`: Blue

## Example Agent Script (Mental Model)

```python
# 1. Check Inbox
inbox = "/sites/Sorterra/Shared Documents/Upload Folder"
files = list_folder_contents(inbox)

for file in files:
    # 2. Decide Destination
    if "Confidential" in file['name']:
        # 3. Act Securely
        secure_move_document(
            file['serverRelativeUrl'],
            "/sites/Sorterra/Shared Documents/Confidential",
            "/sites/Sorterra/Shared Documents/Secure Uploads" # Template for permissions
        )
    else:
        # 3. Act Normally
        move_document(
            file['serverRelativeUrl'],
            "/sites/Sorterra/Shared Documents/General"
        )
```
