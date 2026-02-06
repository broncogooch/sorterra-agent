# SharePoint & AWS Permission Setup Guide

To enable your AWS Agent (Lambda) to access SharePoint, you need to configure permissions in **Microsoft Azure** (to allow access) and **AWS** (to store credentials).

## Part 1: Microsoft Azure (Granting Access)

The "Identity" of your agent is defined in Azure Active Directory (Entra ID).

1.  **Go to Azure Portal** (portal.azure.com).
2.  Navigate to **App Registrations**.
3.  Select your App (e.g., "SharePoint Sorter").
4.  **API Permissions**:
    *   Click **API Permissions** -> **Add a permission**.
    *   Select **SharePoint** -> **Application permissions**.
    *   Check **Sites.FullControl.All** (easiest for full access) OR **Sites.Selected** (if you want to restrict to specific sites).
    *   **IMPORTANT**: Click **Grant admin consent for [Your Tenant]**. without this, the permissions do nothing.
5.  **Certificates & Secrets**:
    *   Click **Certificates & secrets** -> **Certificates** tab.
    *   Click **Upload certificate**.
    *   Upload your `selfsigned.crt` file.
    *   Note the **Thumbprint** value. You will need this for AWS.

## Part 2: AWS Lambda (Configuring the Agent)

Your AWS Lambda function needs the credentials to "log in" as the Azure App.

### Option A: Environment Variables ( Simplest)
When configuring your Lambda function:

1.  Go to **Configuration** -> **Environment variables**.
2.  Add the following keys:
    *   `SHAREPOINT_SITE_URL`: `https://yourdomain.sharepoint.com/sites/YourSite`
    *   `CLIENT_ID`: (From Azure App Overview)
    *   `TENANT_ID`: (From Azure App Overview)
    *   `THUMBPRINT`: (From Azure Certificates tab)
    *   `PRIVATE_KEY_PATH`: `/var/task/private_key.pem`
        *   *Note*: This assumes you included `private_key.pem` in the root of your uploaded .zip file.

### Option B: AWS Secrets Manager (More Secure)
Instead of putting the private key in the zip file, you can store it in AWS Secrets Manager.
*   **Step**: Create a secret (e.g., `SharePointPrivateKey`).
*   **Step**: Update your Python code to fetch this secret at runtime instead of reading a file.
*   *(For this project, we are currently using Option A for simplicity: uploading the key file).*

## Part 3: Deploying the Code
1.  **Prepare the Zip**:
    *   Select `lambda_function.py`, `agent_tools.py`, `sharepoint_client.py`.
    *   Select your `private_key.pem`.
    *   Select the `site-packages` folder (containing `msal`, `office365`, etc.).
    *   Zip them all together.
2.  **Upload to Lambda**:
    *   Go to your Lambda function -> **Code** tab.
    *   **Upload from** -> **.zip file**.

## Summary of Identity
*   **Who is the Agent?**: It is the Azure App Registration.
*   **How does it prove it?**: Using the Certificate (Private Key in AWS + Public Key in Azure).
*   **What can it do?**: Whatever permissions (Sites.FullControl.All) you granted in Azure.
