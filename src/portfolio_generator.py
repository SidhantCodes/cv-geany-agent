import io
import zipfile
import logging
import requests
from typing import Optional

from src.models import Portfolio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortfolioGenerator:
    """
    Handles fetching a web template from a GitHub repository, injecting data,
    and creating a downloadable zip archive.
    """
    def __init__(self, github_repo: str, github_token: str, branch: str = "main"):
        if not all([github_repo, github_token]):
            raise ValueError("GITHUB_REPO and GITHUB_TOKEN are required.")
        
        if '/' not in github_repo:
            raise ValueError("GITHUB_REPO must be in the format 'owner/repo-name'.")

        self.repo_owner, self.repo_name = github_repo.split('/')
        self.github_token = github_token
        self.branch = branch
        self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/zipball/{self.branch}"

        self._validate_config()

    def _validate_config(self):
        """Validate that the repository exists and is accessible."""
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        repo_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        try:
            response = requests.get(repo_url, headers=headers, timeout=10)
            if response.status_code == 404:
                raise ValueError(f"Repository {self.repo_owner}/{self.repo_name} not found or not accessible")
            elif response.status_code == 403:
                raise ValueError("GitHub token doesn't have access to the repository")
            elif response.status_code != 200:
                raise ValueError(f"GitHub API error: {response.status_code}")
                
            # Check if branch exists
            branch_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/branches/{self.branch}"
            branch_response = requests.get(branch_url, headers=headers, timeout=10)
            if branch_response.status_code == 404:
                raise ValueError(f"Branch '{self.branch}' not found in repository")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Cannot validate GitHub repository: {str(e)}")

    def _get_template_zip(self) -> bytes:
        """Downloads the repository zip archive from GitHub."""
        logger.info(f"Downloading template from GitHub: {self.repo_owner}/{self.repo_name}")
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Portfolio-Generator/1.0"
        }
        
        try:
            response = requests.get(self.api_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if 'application/zip' not in content_type and 'application/octet-stream' not in content_type:
                raise Exception(f"Expected zip file but got content-type: {content_type}")
                
            return response.content
            
        except requests.exceptions.Timeout:
            raise Exception("GitHub API request timed out")
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response else 'N/A'
            error_detail = ""
            
            if status_code == 403:
                error_detail = "Access forbidden. Check your GitHub token permissions."
            elif status_code == 404:
                error_detail = f"Repository or branch not found: {self.repo_owner}/{self.repo_name}:{self.branch}"
            elif status_code == 401:
                error_detail = "Authentication failed. Check your GitHub token."
            else:
                error_detail = f"HTTP {status_code}: {str(e)}"
                
            logger.error(f"Failed to download from GitHub: {error_detail}")
            raise Exception(f"Could not retrieve portfolio template from GitHub. {error_detail}")

    def _find_root_directory(self, zip_file: zipfile.ZipFile) -> Optional[str]:
        """Find the root directory in the GitHub zip file."""

        all_files = [item.filename for item in zip_file.infolist() if not item.is_dir()]
        if not all_files:
            return None

        first_components = []
        for file_path in all_files:
            parts = file_path.split('/')
            if len(parts) > 1:
                first_components.append(parts[0] + '/')
        
        if not first_components:
            return None
            
        from collections import Counter
        common_root = Counter(first_components).most_common(1)[0][0]
        return common_root

    def generate_zip(self, portfolio_data: Portfolio) -> bytes:
        """
        Generates a zip file containing the GitHub template and the user's data.json.
        """
        logger.info(f"Starting zip generation for portfolio: {portfolio_data.name}")

        try:
            # 1. Download the template zip from GitHub
            template_zip_bytes = self._get_template_zip()
            template_zip_io = io.BytesIO(template_zip_bytes)

            # 2. Create a new zip file in memory to build our final package
            output_zip_io = io.BytesIO()

            with zipfile.ZipFile(template_zip_io, 'r') as template_zip:
                try:
                    template_zip.testzip()
                except zipfile.BadZipFile:
                    raise Exception("Downloaded template is not a valid zip file")
                    
                with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                    # Find the root directory
                    root_dir = self._find_root_directory(template_zip)
                    if root_dir:
                        logger.info(f"Identified root directory in template zip: {root_dir}")
                    else:
                        logger.warning("No root directory found, copying files as-is")

                    # 3. Copy files from the template zip to the new zip
                    files_copied = 0
                    for item in template_zip.infolist():
                        if item.is_dir():
                            continue
                        
                        try:
                            file_content = template_zip.read(item.filename)

                            if root_dir and item.filename.startswith(root_dir):
                                new_path = item.filename.replace(root_dir, '', 1)
                            else:
                                new_path = item.filename

                            if new_path:
                                logger.debug(f"Adding '{new_path}' to the new archive.")
                                output_zip.writestr(new_path, file_content)
                                files_copied += 1
                                
                        except Exception as e:
                            logger.warning(f"Skipping file '{item.filename}' due to error: {e}")

                    if files_copied == 0:
                        raise Exception("No files were copied from the template repository")

                    logger.info("Adding data.json to the archive.")
                    json_data_string = portfolio_data.model_dump_json(indent=4)
                    output_zip.writestr('data.json', json_data_string)

            logger.info(f"Zip archive created successfully with {files_copied} template files + data.json")
            output_zip_io.seek(0)
            return output_zip_io.getvalue()
            
        except Exception as e:
            logger.error(f"Zip generation failed: {str(e)}")
            raise Exception(f"Portfolio generation failed: {str(e)}")