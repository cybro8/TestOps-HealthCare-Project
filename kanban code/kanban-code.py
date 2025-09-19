import requests
from requests.auth import HTTPBasicAuth
import json

# ----------------- CONFIGURATION -----------------
organization = "evertz-test"       # Azure DevOps organization name
project = "tand-test"        # Azure DevOps project name
pat = "Uwz88lx87zPkjTjlQVsU6O1MEitaoFAGAnXUmaiV0pumntvhjfFYJQQJ99BIACAAAAAAAAAAAAASAZDO3N87"   # Personal Access Token
api_version = "7.0"                  # API version

# Test case details
test_case_title = "another test case"
test_case_description = "This is a test case created using Python script and REST API."
test_case_area_path = "tand-test"  # Typically the project name
test_case_iteration_path = "tand-test\\Sprint 1"  # Optional

# ----------------- API ENDPOINT -----------------
url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$Test%20Case?api-version={api_version}"

# ----------------- PAYLOAD -----------------
payload = [
    {
        "op": "add",
        "path": "/fields/System.Title",
        "value": test_case_title
    },
    {
        "op": "add",
        "path": "/fields/System.Description",
        "value": test_case_description
    },
    {
        "op": "add",
        "path": "/fields/System.AreaPath",
        "value": test_case_area_path
    },
    {
        "op": "add",
        "path": "/fields/System.IterationPath",
        "value": test_case_iteration_path
    }
]

# ----------------- HEADERS -----------------
headers = {
    "Content-Type": "application/json-patch+json"
}

# ----------------- MAKE REQUEST -----------------
response = requests.post(
    url,
    auth=HTTPBasicAuth("", pat),  # Username can be blank; PAT used as password
    headers=headers,
    data=json.dumps(payload)
)

# ----------------- RESPONSE -----------------
if response.status_code == 200 or response.status_code == 201:
    print("Test case created successfully!")
    print("Response:")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"Failed to create test case. Status Code: {response.status_code}")
    print("Response:")
    print(response.text)
