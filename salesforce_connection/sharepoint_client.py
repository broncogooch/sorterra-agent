import os
import msal
import json
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.token_response import TokenResponse
from office365.sharepoint.files.file import File

class SharePointSorter:
    def __init__(self, site_url, client_id, thumbprint=None, private_key_path=None, client_secret=None, tenant_id=None):
        """
        Connects to SharePoint using MSAL (Modern Auth) or Client Secret (Legacy).
        
        Recommended: use `thumbprint` and `private_key_path` for Certificate Authentication.
        """
        self.site_url = site_url
        
        if thumbprint and private_key_path:
            # CERTIFICATE AUTH via MSAL
            # This is more robust for modern Tenants
            self._use_msal = True
            self.client_id = client_id
            self.thumbprint = thumbprint
            self.private_key_path = private_key_path
            
            # Determine Tenant ID or Authority
            # Use 'common' if not provided, but for Cert auth specific tenant is better
            self.tenant_id = tenant_id if tenant_id else "common"
            
            self.context = ClientContext(site_url).with_access_token(self._acquire_token)
        else:
            # SECRET AUTH (Legacy / Dev)
            self._use_msal = False
            self.context = ClientContext(site_url).with_client_credentials(client_id, client_secret)

    # =========================================================================
    # AUTHENTICATION
    # =========================================================================

    def _acquire_token(self):
        """
        Acquires a Bearer token using MSAL with a Self-Signed Certificate.
        This provides a secure, non-interactive way to authenticate as an Application.
        """
        # Read Private Key
        with open(self.private_key_path, 'r') as f:
            private_key = f.read()

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential={
                "thumbprint": self.thumbprint,
                "private_key": private_key
            }
        )

        # Build Scope
        # e.g. https://contoso.sharepoint.com/.default
        sharepoint_host = "https://" + self.site_url.split('/')[2]
        scope = [f"{sharepoint_host}/.default"]
        
        result = app.acquire_token_for_client(scopes=scope)
        
        if "access_token" in result:
            expires_in = result.get('expires_in', 3599)
            return TokenResponse(result['access_token'], result.get('token_type', 'Bearer'), expiresIn=expires_in)
        else:
            raise Exception(f"Could not acquire token: {result.get('error_description')}")


    # =========================================================================
    # BASIC OPERATIONS
    # =========================================================================

    def msg_web_title(self):
        try:
            web = self.context.web
            self.context.load(web)
            self.context.execute_query()
            return web.title
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"Server Response: {e.response.text}")
            raise e

    # =========================================================================
    # FILE & FOLDER OPERATIONS
    # =========================================================================

    def get_files_in_folder(self, folder_url):
        """
        Returns a collection of File objects in the specified folder.
        """
        root_web = self.context.web
        self.context.load(root_web)
        self.context.execute_query()
        
        # Resolve folder
        folder = self.context.web.get_folder_by_server_relative_url(folder_url)
        files = folder.files
        self.context.load(files)
        self.context.execute_query()
        return files

    def create_folder(self, folder_url):
        """
        Ensures a folder exists at the specified path.
        If it does not exist, it creates it.
        """
        self.context.web.ensure_folder_path(folder_url).execute_query()
        # print(f"Ensured folder exists: {folder_url}") # Optional log

    def move_file(self, source_file_url, dest_folder_url):
        """
        Moves a file to the destination folder.
        Handles flat namespace (flattening subfolder names if present in filename).
        """
        file = self.context.web.get_file_by_server_relative_url(source_file_url)
        file_name = source_file_url.split('/')[-1]
        
        if dest_folder_url.endswith('/'):
            dest_folder_url = dest_folder_url[:-1]
            
        dest_path = f"{dest_folder_url}"
        
        # Verify strict flat path - ensure no extra info in file_name (like paths)
        if '/' in file_name:
             # print(f"Warning: Filename {file_name} contains slashes. Flattening.")
             file_name = file_name.split('/')[-1]
             dest_path = f"{dest_folder_url}"
        
        print(f"Moving {source_file_url} -> {dest_path}")
        file.moveto(dest_path, 1).execute_query()

    def scan_folder_structure(self, folder_url):
        """
        Returns a dictionary representing the folder structure (Names of files and subfolders).
        """
        root = {}
        
        ctx = self.context
        web = ctx.web
        
        # Get the main folder
        folder = web.get_folder_by_server_relative_url(folder_url)
        # Expand Folders and Files explicitly
        ctx.load(folder, ["Folders", "Files", "Name"])
        ctx.execute_query()
        
        root['name'] = folder.name
        root['files'] = [f.name for f in folder.files]
        root['folders'] = []
        
        for sub_folder in folder.folders:
             root['folders'].append(sub_folder.name)
             
        return root

    def set_folder_color(self, folder_url, color_hex="6"):
        """
        Sets the folder color using Modern SharePoint APIs.
        Colors: 0=Yellow, 1=DarkRed, 2=DarkOrange, 3=DarkGreen, 4=LightBlue, 5=LightTeal, 6=Blue (Default)
        """
        try:
            import requests
            
            # Ensure we have a token
            token_response = self._acquire_token()
            token = token_response.accessToken
            
            # Method 1: Modern API stampcolor
            api_endpoint = f"{self.site_url}/_api/foldercoloring/stampcolor(DecodedUrl='{folder_url}')"
            
            try:
                color_int = int(color_hex)
            except:
                color_int = 0
            
            payload = {
                "coloringInformation": {
                    "ColorHex": str(color_int)
                }
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json;odata=verbose",
                "Accept": "application/json;odata=verbose"
            }
            
            # print(f"Attempting to set color via {api_endpoint}...")
            response = requests.post(api_endpoint, headers=headers, json=payload)
            
            if response.status_code == 204 or response.status_code == 200:
                print(f"Set folder color for {folder_url} to {color_hex}")
                return
            else:
                print(f"Modern API failed ({response.status_code}). Body: {response.text}")

        except Exception as e:
            print(f"Failed to set folder color: {e}")

    def scan_folder_structure(self, folder_url):
        """
        Returns a dictionary representing the folder structure.
        """
        root = {}
        
        ctx = self.context
        web = ctx.web
        
        # Get the main folder
        folder = web.get_folder_by_server_relative_url(folder_url)
        # Expand Folders and Files explicitly
        ctx.load(folder, ["Folders", "Files", "Name"])
        ctx.execute_query()
        
        root['name'] = folder.name
        root['files'] = [f.name for f in folder.files]
        root['folders'] = []
        
        for sub_folder in folder.folders:
             root['folders'].append(sub_folder.name)
             
        return root

    def set_folder_color(self, folder_url, color_hex="6"):
        """
        Sets the folder color.
        Attempts Modern API (stampcolor) first, then Legacy (vti_colorhex).
        """
        try:
            import requests
            
            # Ensure we have a token
            token_response = self._acquire_token()
            token = token_response.accessToken
            
            # Method 1: Modern API stampcolor
            # Pass DecodedUrl in the URL as function parameter
            # e.g. _api/foldercoloring/stampcolor(DecodedUrl='/sites/Site/Shared Documents/Folder')
            api_endpoint = f"{self.site_url}/_api/foldercoloring/stampcolor(DecodedUrl='{folder_url}')"
            
            # Try integer for ColorHex
            try:
                color_int = int(color_hex)
            except:
                color_int = 0
            
            payload = {
                "coloringInformation": {
                    #"DecodedUrl": folder_url, # Moved to URL
                    "ColorHex": str(color_int)
                }
            }
            # Wait, some docs say just the fields, some say nested. 
            # Let's try sending BOTH payloads if one fails? 
            # Or better, print the failure message to know WHY 400.
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json;odata=verbose",
                "Accept": "application/json;odata=verbose"
            }
            
            print(f"Attempting to set color via {api_endpoint}...")
            response = requests.post(api_endpoint, headers=headers, json=payload)
            
            if response.status_code == 204 or response.status_code == 200:
                print(f"Set folder color for {folder_url} to {color_hex} (Modern API)")
                return
            else:
                print(f"Modern API failed ({response.status_code}). Body: {response.text}")
                # Don't fallback purely blindly, but let's keep it.

            # Method 2: Legacy vti_colorhex
            # Get folder list item
            folder = self.context.web.get_folder_by_server_relative_url(folder_url)
            list_item = folder.list_item_all_fields
            list_item.set_property("vti_colorhex", str(color_hex))
            list_item.update()
            self.context.execute_query()
            print(f"Set folder color for {folder_url} to {color_hex} (Legacy API)")

        except Exception as e:
            print(f"Failed to set folder color: {e}")

    # =========================================================================
    # PERMISSION MANAGEMENT
    # =========================================================================

    def get_folder_permissions(self, folder_url):
        """
        Retrieves the role assignments for a folder.
        Returns a list of dictionaries with 'principal_id' and 'role_def_ids'.
        """
        folder = self.context.web.get_folder_by_server_relative_url(folder_url)
        item = folder.list_item_all_fields
        role_assignments = item.role_assignments
        
        # Load PrincipalId explicitly.
        # RoleDefinitionBindings is a collection, need to ensure it's loaded.
        self.context.load(role_assignments, ["PrincipalId", "RoleDefinitionBindings"])
        self.context.execute_query()
        
        permissions = []
        for ra in role_assignments:
            # We access PrincipalId directly (property getter uses backing dict)
            principal_id = ra.principal_id
            
            # RoleDefinitionBindings are loaded via Include
            role_ids = [r.id for r in ra.role_definition_bindings]
            
            # Note: We cannot get the Principal Title easily without expanding Member (which causes 401).
            # So logging will use ID only.
            
            permissions.append({
                "principal_id": principal_id,
                "role_def_ids": role_ids,
                "principal_title": f"Principal {principal_id}" 
            })
            
        return permissions

    def apply_unique_permissions(self, file_url, permissions):
        """
        Breaks inheritance on the file and applies the provided permissions.
        unique_permissions: List of dicts with 'principal_id' and 'role_def_ids'
        """
        file = self.context.web.get_file_by_server_relative_url(file_url)
        item = file.listItemAllFields
        
        # Break inheritance: copy_role_assignments=False (start clean), clear_subscopes=True
        item.break_role_inheritance(False, True)
        self.context.execute_query()
        print(f"Broken inheritance for {file_url}")
        
        # Apply new permissions
        for perm in permissions:
            principal_id = perm['principal_id']
            role_def_ids = perm['role_def_ids']
            
            # Add each role definition individually using ID
            for rid in role_def_ids:
                item.role_assignments.add_role_assignment(principal_id, rid)
                
            print(f"Added permissions for Principal ID: {principal_id}")
            
        self.context.execute_query()
        print(f"Applied permissions to {file_url}")
