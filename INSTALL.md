# agentize.eu PoC — Installation Guide

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-03-12 |
| **Status** | Active |
| **Owner** | agentize.eu |
| **Confidentiality** | Internal |

This guide covers every step required to go from a blank Azure subscription to a fully operational agentize.eu PoC system running in Microsoft Teams, including manual portal steps, automated deployment, CI/CD setup, and local development.

**Time estimate:** 2-4 hours for a first-time setup (Azure provisioning ~15 min, remainder is configuration).

---

## Table of Contents

- [Phase 0: Azure Account and Tenant Setup](#phase-0-azure-account-and-tenant-setup)
- [Phase 1: Local Workstation Setup](#phase-1-local-workstation-setup)
- [Phase 2: Repository Setup](#phase-2-repository-setup)
- [Phase 3: Azure Infrastructure Deployment](#phase-3-azure-infrastructure-deployment)
- [Phase 4: Post-Deployment Validation](#phase-4-post-deployment-validation)
- [Phase 5: CI/CD Pipeline Setup](#phase-5-cicd-pipeline-setup)
- [Phase 6: Microsoft Teams App Setup](#phase-6-microsoft-teams-app-setup)
- [Phase 7: Telegram Bot Setup (Optional)](#phase-7-telegram-bot-setup-optional)
- [Phase 8: Local Development Setup](#phase-8-local-development-setup)
- [Phase 9: End-to-End Verification](#phase-9-end-to-end-verification)
- [Appendix A: Troubleshooting Reference](#appendix-a-troubleshooting-reference)
- [Appendix B: Environment Variables Reference](#appendix-b-environment-variables-reference)
- [Appendix C: Azure Resource Naming Reference](#appendix-c-azure-resource-naming-reference)

---

## Phase 0: Azure Account and Tenant Setup

This phase covers manual steps that must be completed in the Azure Portal before any automated deployment.

### 0.1 Obtain an Azure Subscription

You need an active Azure subscription with billing configured. Supported subscription types:

| Type | How to Obtain | Typical Use |
|---|---|---|
| Enterprise Agreement (EA) | Contact your Microsoft account team or partner | Production / enterprise |
| Pay-As-You-Go | [azure.microsoft.com/pricing](https://azure.microsoft.com/en-us/pricing/purchase-options/pay-as-you-go) | PoC / small teams |
| MSDN / Visual Studio | Included with VS Enterprise/Professional subscriptions | Development / testing |
| Free Trial | [azure.microsoft.com/free](https://azure.microsoft.com/en-us/free/) | Evaluation (limited credits) |

**Steps:**

1. Go to [portal.azure.com](https://portal.azure.com) and sign in with your organization account.
2. Navigate to **Subscriptions** in the left menu.
3. If no subscription exists, click **+ Add** and follow the wizard for your subscription type.
4. Note the **Subscription ID** — you will need it later.

**Verification:**

```powershell
az login
az account list --output table
```

Expected output: a table listing at least one subscription with `State = Enabled`.

> **Error: "No subscriptions found"**
>
> *Cause:* Your account has no active subscription, or you are logged into the wrong tenant.
>
> *Fix:* Verify your account at portal.azure.com > Subscriptions. If using a multi-tenant setup, specify the tenant: `az login --tenant <tenant-id>`.

### 0.2 Verify Entra ID Roles

The deployment script creates an Entra ID (Azure AD) App Registration and assigns RBAC roles. Your account needs these roles:

| Role | Scope | Purpose |
|---|---|---|
| **Contributor** | Subscription | Create and manage Azure resources |
| **User Access Administrator** | Subscription | Assign RBAC roles (Key Vault, Container App) |
| **Application Administrator** *or* **Cloud Application Administrator** | Entra ID | Create App Registrations for the bot |

**Steps:**

1. Go to **portal.azure.com** > **Subscriptions** > select your subscription > **Access control (IAM)** > **View my access**.
2. Confirm you have **Contributor** and **User Access Administrator**.
3. Go to **Entra ID** > **Roles and administrators** > search for **Application Administrator**.
4. If your account is not listed, ask a Global Administrator to assign the role.

**Verification:**

```powershell
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --output table
```

> **Error: "Insufficient privileges to complete the operation"**
>
> *Cause:* Your account lacks the required Entra ID role.
>
> *Fix:* Ask a Global Administrator to assign **Application Administrator** to your account: Entra ID > Roles and administrators > Application Administrator > + Add assignments.

### 0.3 Verify Sweden Central Region Capacity

The PoC deploys AI Foundry with the `DataZoneStandard` SKU in Sweden Central for EU data residency compliance.

**Steps:**

1. Go to **portal.azure.com** > **Azure AI Foundry** (or search for "AI services").
2. Click **+ Create** and select **Sweden Central** as the region.
3. In the pricing tier dropdown, confirm that `DataZoneStandard` (or `S0`) is available.
4. Do **not** complete the wizard — cancel after verifying availability.

Alternatively, check via CLI:

```powershell
az cognitiveservices account list-skus --kind "AIServices" --location swedencentral --output table
```

> **Error: "The requested SKU is not available in the selected region"**
>
> *Cause:* Sweden Central may have capacity limits or your subscription type may not support `DataZoneStandard`.
>
> *Fix:*
> 1. Request a quota increase: portal.azure.com > Help + support > New support request > Quota > Cognitive Services.
> 2. Fallback region: `germanywestcentral` also offers EU data residency, but update the `location` parameter in `deploy.ps1` accordingly.

**Phase 0 Checkpoint:** You have an active Azure subscription with the required roles, and Sweden Central supports the AI Foundry SKU.

---

## Phase 1: Local Workstation Setup

Install the tools required to run the deployment scripts and develop locally.

### 1.1 Install Git

| Platform | Install Method |
|---|---|
| Windows | [git-scm.com/download/win](https://git-scm.com/download/win) or `winget install Git.Git` |
| macOS | `brew install git` or Xcode Command Line Tools |
| Linux | `sudo apt install git` (Debian/Ubuntu) or `sudo dnf install git` (Fedora) |

**Verification:**

```bash
git --version
```

Expected: `git version 2.40.0` or higher.

> **Error: "'git' is not recognized as an internal or external command"**
>
> *Cause:* Git is not in your PATH.
>
> *Fix:* Restart your terminal. On Windows, ensure the Git installer added Git to PATH (re-run installer and check the option). Verify with `where git` (Windows) or `which git` (macOS/Linux).

### 1.2 Install Azure CLI

| Platform | Install Method |
|---|---|
| Windows | [aka.ms/installazurecli](https://aka.ms/installazurecli) or `winget install Microsoft.AzureCLI` |
| macOS | `brew install azure-cli` |
| Linux | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |

**Verification:**

```bash
az --version
```

Expected: `azure-cli 2.60.0` or higher.

> **Error: "'az' is not recognized"**
>
> *Cause:* Azure CLI not installed or not in PATH.
>
> *Fix:* Restart your terminal after installation. On Windows, the MSI installer adds `az` to PATH automatically; if using winget, you may need to restart the shell.

> **Error: "az login" hangs or fails with browser redirect**
>
> *Cause:* Firewall or proxy blocks the authentication redirect.
>
> *Fix:* Use device code flow: `az login --use-device-code`. This prints a code to enter at [microsoft.com/devicelogin](https://microsoft.com/devicelogin).

### 1.3 Install Python 3.12

| Platform | Install Method |
|---|---|
| Windows | [python.org/downloads](https://www.python.org/downloads/) — check "Add Python to PATH" during install |
| macOS | `brew install python@3.12` |
| Linux | `sudo apt install python3.12 python3.12-venv python3.12-dev` |

**Verification:**

```bash
python --version
```

Expected: `Python 3.12.x`. On some systems, use `python3 --version`.

> **Error: Python version is 3.11 or lower**
>
> *Cause:* System Python is older; the new version is installed alongside it.
>
> *Fix:* Use `python3.12` explicitly, or on Windows, use the Python Launcher: `py -3.12 --version`. Consider using `pyenv` to manage versions.

### 1.4 Install PowerShell 7+

The deployment script `deploy.ps1` requires PowerShell 7+.

| Platform | Install Method |
|---|---|
| Windows 11 | Built-in (verify version). If older: `winget install Microsoft.PowerShell` |
| Windows 10 | `winget install Microsoft.PowerShell` |
| macOS | `brew install powershell/tap/powershell` |
| Linux | See [Microsoft docs](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-linux) |

**Verification:**

```powershell
$PSVersionTable.PSVersion
```

Expected: `7.x.x`. If you see `5.1.x`, you are running Windows PowerShell (legacy), not PowerShell 7.

> **Error: Scripts are disabled on this system**
>
> *Cause:* PowerShell execution policy blocks script execution.
>
> *Fix:* Run as Administrator: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

**Alternative:** For Linux/CI environments, use `deploy.sh` (Bash) instead of `deploy.ps1`. In that case, PowerShell 7 is not required.

### 1.5 Install Docker Desktop (Optional)

Docker is only needed if you plan to use Dev Containers for local development (Phase 8) or build container images locally.

| Platform | Install Method |
|---|---|
| Windows | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) — requires WSL 2 |
| macOS | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Linux | `sudo apt install docker.io docker-compose-v2` |

**Verification:**

```bash
docker --version
docker run hello-world
```

> **Error: "docker: Cannot connect to the Docker daemon"**
>
> *Cause:* Docker Desktop is not running, or WSL 2 is not enabled (Windows).
>
> *Fix:* Start Docker Desktop. On Windows, ensure WSL 2 is enabled: `wsl --install` from an elevated terminal, then restart.

> **Error: "WSL 2 installation is incomplete"**
>
> *Cause:* WSL kernel update required.
>
> *Fix:* Download and install the WSL 2 kernel update from [aka.ms/wsl2kernel](https://aka.ms/wsl2kernel), then restart Docker Desktop.

**Phase 1 Checkpoint:** Run all verification commands — Git, Azure CLI, Python 3.12, and PowerShell 7 should all return valid version numbers.

---

## Phase 2: Repository Setup

### 2.1 Clone the Repository

```bash
git clone https://github.com/agentize-eu/TWI_POC.git
cd TWI_POC
```

> **Error: "Repository not found" or "Permission denied (publickey)"**
>
> *Cause:* You don't have access to the repository, or SSH keys are not configured.
>
> *Fix:*
> - For HTTPS: ensure your GitHub account has been granted access. Use `git clone https://github.com/...` and enter your Personal Access Token when prompted.
> - For SSH: add your SSH key to GitHub (Settings > SSH and GPG keys) and verify with `ssh -T git@github.com`.

### 2.2 Copy Environment Template

```powershell
Copy-Item poc-backend/.env.example poc-backend/.env
```

Or on Linux/macOS:

```bash
cp poc-backend/.env.example poc-backend/.env
```

Do **not** edit the `.env` file yet — the deployment script (Phase 3) will populate it automatically with real values.

### 2.3 Copy Bicep Parameters Template

```powershell
Copy-Item poc-backend/infra/parameters.example.json poc-backend/infra/parameters.json
```

This file is used if you need to customize Bicep deployment parameters (AI model, replica count, etc.). The deployment script passes parameters directly via CLI arguments, so this step is optional for default deployments.

### 2.4 Install Pre-Commit Hooks

```bash
pip install pre-commit
pre-commit install
```

This configures the Gitleaks secret scanner to run before every commit, preventing accidental secret exposure.

**Verification:**

```bash
pre-commit run --all-files
```

Expected: `gitleaks...............Passed` (or similar).

> **Error: "'pre-commit' is not recognized"**
>
> *Cause:* `pre-commit` is not installed or not in PATH.
>
> *Fix:* Install it: `pip install pre-commit`. If pip scripts are not in PATH, use `python -m pre_commit install`.

**Phase 2 Checkpoint:** You have a local clone with `.env` and `parameters.json` template files, and pre-commit hooks installed.

---

## Phase 3: Azure Infrastructure Deployment

This phase uses the automated `deploy.ps1` script that performs 8 sub-steps: Entra ID App Registration, Resource Group creation, Bicep deployment, key retrieval, Key Vault RBAC, secret population, Container App restart, and `.env` generation.

### 3.1 Log In to Azure

```powershell
az login
```

If you have multiple subscriptions, select the correct one:

```powershell
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
az account show --output table
```

> **Error: "AADSTS50076: Due to a configuration change made by your administrator..."**
>
> *Cause:* Multi-factor authentication (MFA) or conditional access policy is blocking the login.
>
> *Fix:* Use device code flow: `az login --use-device-code`.

### 3.2 Run the Deployment Script

Navigate to the `infra` folder and run the script:

```powershell
cd poc-backend/infra
.\deploy.ps1
```

The script runs 8 steps automatically. Here is what each step does and what can go wrong:

#### Step 0: Prerequisites Check

The script verifies Azure CLI is installed and you are logged in.

> **Error: "Azure CLI not found"**
>
> *Cause:* `az` is not in PATH.
>
> *Fix:* Complete Phase 1.2 and restart your terminal.

#### Step 1: Entra ID App Registration

Creates an App Registration named `agentize-poc-bot` with a 2-year client secret, a Service Principal, and `User.Read` Graph permission.

> **Error: "Insufficient privileges to complete the operation"**
>
> *Cause:* Your account lacks the Application Administrator role in Entra ID.
>
> *Fix:* Complete Phase 0.2. Alternatively, have an admin create the App Registration manually and use: `.\deploy.ps1 -BotAppId <CLIENT_ID> -BotAppPassword <SECRET> -SkipAppReg`.

> **Error: "An App Registration with this name already exists"**
>
> *Cause:* A previous deployment attempt created the App Registration.
>
> *Fix:* Find the existing App Registration in Entra ID > App Registrations, note its Client ID, create a new secret, and run: `.\deploy.ps1 -BotAppId <CLIENT_ID> -BotAppPassword <NEW_SECRET> -SkipAppReg`.

#### Step 2: Resource Group

Creates `rg-agentize-poc-swedencentral` in Sweden Central.

> **Error: "The subscription is not registered to use namespace 'Microsoft.Resources'"**
>
> *Cause:* Resource provider not registered on the subscription.
>
> *Fix:* Register it: `az provider register --namespace Microsoft.Resources --wait`.

#### Step 3: Bicep Deployment (5-15 minutes)

Deploys all Azure resources defined in `main.bicep`: VNet, NSG, Log Analytics, Key Vault, App Insights, Container App Environment, AI Foundry (DataZoneStandard), Cosmos DB (MongoDB API), Storage Account, Container App, Bot Service with Teams channel, and RBAC assignments.

> **Error: "InvalidTemplateDeployment — The resource 'ai-agentize-poc' deployment failed with status 'Conflict'"**
>
> *Cause:* AI Foundry `DataZoneStandard` capacity is exhausted in Sweden Central.
>
> *Fix:*
> 1. Wait 30 minutes and retry — capacity may free up.
> 2. Request a quota increase via Azure Portal > Help + support.
> 3. As a last resort, switch to `germanywestcentral` (also EU Data Zone): `.\deploy.ps1 -Location germanywestcentral`.

> **Error: "The resource name 'kv-agentize-poc' is already taken"**
>
> *Cause:* Key Vault names are globally unique and a soft-deleted Key Vault with this name exists.
>
> *Fix:* Purge the soft-deleted vault: `az keyvault purge --name kv-agentize-poc --location swedencentral`. Or use a different prefix: `.\deploy.ps1 -ProjectPrefix agentize-poc2`.

> **Error: "QuotaExceeded" or "SkuNotAvailable"**
>
> *Cause:* The subscription has reached resource limits.
>
> *Fix:* Check quotas: `az vm list-usage --location swedencentral --output table`. Request an increase via the Azure Portal.

> **Error: Deployment timeout (>20 minutes without progress)**
>
> *Cause:* AI Foundry model provisioning is slow or stuck.
>
> *Fix:* Check progress in Azure Portal > Resource Groups > `rg-agentize-poc-swedencentral` > Deployments. If a specific resource is stuck, cancel and retry.

#### Step 4: Retrieve Service Keys

Retrieves the AI Foundry API key, Cosmos DB connection string, and Blob Storage connection string.

> **Error: "The resource ... was not found"**
>
> *Cause:* Step 3 (Bicep deployment) did not complete successfully.
>
> *Fix:* Re-run `.\deploy.ps1` — it will skip already-created resources and retry the failed ones.

#### Step 5: Key Vault RBAC

Assigns the **Key Vault Secrets Officer** role to your account and waits 15 seconds for RBAC propagation.

> **Error: "Role assignment already exists"**
>
> *Cause:* You already have this role from a previous deployment. This is a warning, not an error — the script continues.
>
> *Fix:* No action needed.

> **Error: Key Vault secret operations fail after this step**
>
> *Cause:* RBAC propagation took longer than 15 seconds.
>
> *Fix:* Wait 60 seconds and re-run the script, or manually set secrets: `az keyvault secret set --vault-name kv-agentize-poc --name <name> --value <value>`.

#### Step 6: Populate Key Vault Secrets

Stores 4 secrets: `ai-foundry-key`, `cosmos-connection`, `blob-connection`, `bot-app-password`.

> **Error: "Caller is not authorized to perform action on resource"**
>
> *Cause:* RBAC from Step 5 has not propagated yet.
>
> *Fix:* Wait 60 seconds and re-run the script.

#### Step 7: Container App Restart

Creates a new revision of the Container App to resolve Key Vault secret references.

> **Error: "ContainerAppOperationError — revision failed to provision"**
>
> *Cause:* The container image cannot be pulled, or Key Vault secrets are not resolvable.
>
> *Fix:*
> 1. Check container logs: `az containerapp logs show --name ca-agentize-poc-backend --resource-group rg-agentize-poc-swedencentral`.
> 2. Verify Key Vault secrets exist: `az keyvault secret list --vault-name kv-agentize-poc --output table`.
> 3. Ensure the Container App's managed identity has the **Key Vault Secrets User** role (this is assigned by the Bicep template).

#### Step 8: Generate .env File

Writes a `.env` file to `poc-backend/.env` with all connection strings and keys for local development.

### 3.3 Save Deployment Output

The script prints a summary block at the end:

```
+------------------------------------------------------+
|   Day 1-2 Deployment Complete!                       |
+------------------------------------------------------+

Resource Group : rg-agentize-poc-swedencentral
Backend URL    : https://ca-agentize-poc-backend.<hash>.swedencentral.azurecontainerapps.io
Bot Endpoint   : https://ca-agentize-poc-backend.<hash>.swedencentral.azurecontainerapps.io/api/messages
AI Foundry     : https://ai-agentize-poc.services.ai.azure.com/models
Key Vault      : https://kv-agentize-poc.vault.azure.net/
```

**Save these values.** You will need the **Backend URL** (without `https://`) for the Teams manifest, and the **Bot Endpoint** is already registered in Azure Bot Service.

### Linux / CI Alternative

For Bash environments, use `deploy.sh` instead:

```bash
cd poc-backend/infra
chmod +x deploy.sh
./deploy.sh
```

The Bash script performs the same 8 steps with identical parameters and error handling.

**Phase 3 Checkpoint:** The deployment script printed "Day 1-2 Deployment Complete!" and the `.env` file exists at `poc-backend/.env` with real values.

---

## Phase 4: Post-Deployment Validation

### 4.1 Run the Validation Script

```powershell
cd poc-backend/infra
.\validate.ps1
```

The script performs 10 automated checks:

| Check | What It Verifies |
|---|---|
| 1. Azure Login | You are authenticated |
| 2. Resource Group | `rg-agentize-poc-swedencentral` exists and is `Succeeded` |
| 3. Core Resources | Container App Env, Container App, AI Foundry, Cosmos DB, Storage, Key Vault, Bot Service, App Insights, Log Analytics |
| 4. AI Model | `gpt-4o` deployment with `DataZoneStandard` SKU |
| 5. Key Vault Secrets | All 4 secrets present and enabled |
| 6. Cosmos Collections | `conversations`, `agent_state`, `generated_documents`, `audit_log` |
| 7. Blob Storage | `pdf-output` container exists |
| 8. Container App Health | Running revision and `/health` endpoint returns `healthy` |
| 9. Bot Channels | Teams channel enabled |
| 10. AI Foundry Connectivity | REST API reachable |

### 4.2 Interpret Results

The script prints a summary:

```
  ✅ Passed :  N
  ⚠️  Warnings: N
  ❌ Failed :  N
```

- **All passed, no warnings:** proceed to Phase 5.
- **Warnings only:** typically informational (e.g., Container App still starting). Wait 60 seconds and re-run.
- **Failures:** address each failure before proceeding.

> **Error: "AI Foundry — not found or failed"**
>
> *Cause:* AI Foundry provisioning failed or the model deployment did not succeed.
>
> *Fix:* Check in Azure Portal > AI Foundry > your resource > Model deployments. If the model deployment shows "Failed", delete it and redeploy: the Bicep template handles this.

> **Error: "Container App has no running revisions"**
>
> *Cause:* Key Vault secrets are not resolvable, or the container image is unavailable.
>
> *Fix:*
> 1. Check logs: `az containerapp logs show --name ca-agentize-poc-backend --resource-group rg-agentize-poc-swedencentral --follow`.
> 2. Verify Key Vault secrets: `az keyvault secret list --vault-name kv-agentize-poc --output table`.
> 3. Restart: `az containerapp revision restart --name ca-agentize-poc-backend --resource-group rg-agentize-poc-swedencentral --revision <revision-name>`.

> **Error: "/health not reachable"**
>
> *Cause:* Container is still starting (30-60 seconds after deployment) or the app crashed on startup.
>
> *Fix:* Wait 60 seconds and retry. If it persists, check container logs for Python import errors or missing environment variables.

### 4.3 Manual Health Check

Open a browser or use curl:

```bash
curl https://ca-agentize-poc-backend.<hash>.swedencentral.azurecontainerapps.io/health
```

Expected response:

```json
{"status": "healthy", "environment": "poc"}
```

**Phase 4 Checkpoint:** `validate.ps1` reports all checks passed (warnings are acceptable), and the `/health` endpoint returns `healthy`.

---

## Phase 5: CI/CD Pipeline Setup

The project uses GitHub Actions to build Docker images and deploy to Azure Container Apps on every push to `main`.

### 5.1 Create an Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "github-actions-deploy" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-agentize-poc-swedencentral \
  --sdk-auth
```

Replace `<YOUR_SUBSCRIPTION_ID>` with your actual subscription ID (from `az account show --query id -o tsv`).

This command outputs a JSON block — **copy the entire JSON output**.

> **Error: "Insufficient privileges to complete the operation"**
>
> *Cause:* You don't have permission to create Service Principals.
>
> *Fix:* Ask an admin to run this command, or use an existing Service Principal with Contributor access to the resource group.

> **Error: "Values of identifierUris property must use a verified domain"**
>
> *Cause:* Azure CLI version mismatch.
>
> *Fix:* Update Azure CLI: `az upgrade`.

### 5.2 Add GitHub Repository Secret

1. Go to your GitHub repository > **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Name: `AZURE_CREDENTIALS`
4. Value: paste the entire JSON block from Step 5.1.
5. Click **Add secret**.

> **Error: "You don't have permission to create secrets"**
>
> *Cause:* You need Admin or Maintainer access to the repository.
>
> *Fix:* Ask the repository owner to grant you the Maintainer role, or have them add the secret.

### 5.3 Configure GitHub Container Registry Permissions

The workflow pushes Docker images to `ghcr.io`. Ensure your repository allows package writes:

1. Go to your GitHub repository > **Settings** > **Actions** > **General**.
2. Under **Workflow permissions**, select **Read and write permissions**.
3. Click **Save**.

### 5.4 Trigger the First Deployment

Push any change under `poc-backend/` to the `main` branch:

```bash
git add -A
git commit -m "trigger initial CI/CD deployment"
git push origin main
```

Monitor the workflow:

1. Go to your GitHub repository > **Actions** tab.
2. Click the running workflow to see logs.
3. The workflow builds the Docker image, pushes to GHCR, and updates the Container App.

> **Error: Workflow fails at "Login to Azure"**
>
> *Cause:* The `AZURE_CREDENTIALS` secret is missing or malformed.
>
> *Fix:* Verify the secret exists and contains valid JSON from `az ad sp create-for-rbac --sdk-auth`. Recreate if necessary.

> **Error: Workflow fails at "Build and push image to GHCR"**
>
> *Cause:* GHCR write permissions are not configured.
>
> *Fix:* Complete Step 5.3. Also verify that the workflow YAML includes `permissions: { packages: write }` (it does by default in `.github/workflows/deploy.yml`).

> **Error: Workflow fails at "Deploy to Container App"**
>
> *Cause:* The Service Principal does not have access to the resource group, or the Container App name is incorrect.
>
> *Fix:* Verify the Service Principal's role: `az role assignment list --assignee <sp-app-id> --output table`. Ensure it has Contributor on `rg-agentize-poc-swedencentral`.

**Phase 5 Checkpoint:** The GitHub Actions workflow completes successfully (green check), and the Container App runs the newly built image.

---

## Phase 6: Microsoft Teams App Setup

### 6.1 Edit the Manifest

Open `teams-app/manifest.json` and replace the two placeholders:

| Placeholder | Replace With | Where to Find It |
|---|---|---|
| `{{BOT_APP_ID}}` | Entra ID App Registration Client ID | `poc-backend/.env` > `BOT_APP_ID` |
| `{{BACKEND_FQDN}}` | Container App hostname (without `https://`) | `poc-backend/.env` or Phase 3 summary output |

There are **two occurrences** of `{{BOT_APP_ID}}` (fields `id` and `bots[0].botId`) and **one** of `{{BACKEND_FQDN}}` (field `validDomains`).

Example after replacement:

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "bots": [{
    "botId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }],
  "validDomains": ["ca-agentize-poc-backend.hash123.swedencentral.azurecontainerapps.io"]
}
```

> **Error: Teams app upload fails with "manifest validation error"**
>
> *Cause:* Invalid JSON syntax, placeholder not replaced, or `validDomains` contains `https://`.
>
> *Fix:*
> 1. Validate JSON syntax at [jsonlint.com](https://jsonlint.com).
> 2. Ensure `validDomains` contains only the hostname, without protocol prefix.
> 3. Ensure both `{{BOT_APP_ID}}` occurrences are replaced.

### 6.2 Verify Icon Files

The `teams-app/` folder already contains the required icons:

| File | Required Size | Purpose |
|---|---|---|
| `color.png` | 192x192 px | Full-color app icon |
| `outline.png` | 32x32 px | Transparent outline icon |

If you need to replace them, ensure the files match the exact required dimensions and are PNG format.

### 6.3 Create the ZIP Package

Create a ZIP file containing the four files **at the root** of the archive (not inside a subfolder):

**PowerShell:**

```powershell
Compress-Archive -Path teams-app\manifest.json, teams-app\color.png, teams-app\outline.png, teams-app\strings-en.json -DestinationPath agentize-teams-app.zip -Force
```

**Linux/macOS:**

```bash
cd teams-app
zip ../agentize-teams-app.zip manifest.json color.png outline.png strings-en.json
cd ..
```

> **Error: Teams rejects the ZIP with "InvalidArchiveError"**
>
> *Cause:* The files are inside a subfolder in the ZIP.
>
> *Fix:* Open the ZIP and verify `manifest.json` is at the root level, not inside a `teams-app/` folder.

### 6.4 Sideload into Microsoft Teams

1. Open **Microsoft Teams** (desktop or web).
2. Go to **Apps** (left sidebar) > **Manage your apps** > **Upload an app**.
3. Select **Upload a custom app**.
4. Choose the `agentize-teams-app.zip` file.
5. Click **Add** in the app details dialog.

The bot now appears in your chat list as "agentize AI".

> **Error: "Upload a custom app" option is not visible**
>
> *Cause:* Your Teams admin has disabled custom app sideloading.
>
> *Fix:* Ask your Teams administrator to enable sideloading: Microsoft Teams admin center > Teams apps > Setup policies > Global > enable "Upload custom apps". This may take up to 24 hours to propagate.

> **Error: "App package is invalid — bot ID does not match"**
>
> *Cause:* The `botId` in the manifest does not match the Entra ID App Registration.
>
> *Fix:* Verify `BOT_APP_ID` in your `.env` matches both `id` and `bots[0].botId` in `manifest.json`.

**Phase 6 Checkpoint:** The "agentize AI" bot appears in your Teams chat list and you can start a conversation with it.

---

## Phase 7: Telegram Bot Setup (Optional)

This phase is optional. Skip it if you only need Microsoft Teams.

### 7.1 Create a Bot via BotFather

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`.
3. Enter a display name (e.g., `agentize PoC Bot`).
4. Enter a username (must end in `bot`, e.g., `agentize_poc_bot`).
5. BotFather replies with a **token** in the format `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`.

**Save this token securely.** Do not commit it to version control.

> **Error: "Sorry, this username is already taken"**
>
> *Cause:* Telegram bot usernames are globally unique.
>
> *Fix:* Choose a different username, e.g., `agentize_poc_eu_bot`.

### 7.2 Deploy with the Telegram Token

If you have not yet run `deploy.ps1`, include the token:

```powershell
.\deploy.ps1 -TelegramBotToken "<YOUR_TELEGRAM_BOT_TOKEN>"
```

If you already deployed without a Telegram token, update the Container App environment variable:

```powershell
az containerapp update `
  --name ca-agentize-poc-backend `
  --resource-group rg-agentize-poc-swedencentral `
  --set-env-vars "TELEGRAM_BOT_TOKEN=<YOUR_TELEGRAM_BOT_TOKEN>"
```

And register the Telegram channel in Azure Bot Service:

```powershell
az bot telegram create `
  --name bot-agentize-poc `
  --resource-group rg-agentize-poc-swedencentral `
  --access-token "<YOUR_TELEGRAM_BOT_TOKEN>" `
  --is-validated
```

> **Error: "The access token is not valid"**
>
> *Cause:* The token is incorrect, expired, or the bot was deleted.
>
> *Fix:* Verify the token with BotFather: send `/token` and select your bot. If the token changed, regenerate it with `/revoke`.

### 7.3 Verify Telegram Channel

```powershell
az bot telegram show --name bot-agentize-poc --resource-group rg-agentize-poc-swedencentral
```

Then open Telegram, search for your bot by username, and send a test message.

**Phase 7 Checkpoint:** The Telegram bot responds to messages (or you consciously skipped this phase).

---

## Phase 8: Local Development Setup

This phase sets up your local machine to run the backend for development and debugging.

### 8.1 Create a Virtual Environment

```bash
cd poc-backend
python -m venv .venv
```

Activate it:

| Platform | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (CMD) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

### 8.2 Install Dependencies

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

> **Error: "Failed building wheel for weasyprint" or "cairo / pango not found"**
>
> *Cause:* WeasyPrint requires system-level libraries for PDF rendering.
>
> *Fix by platform:*
>
> **Windows:**
> ```
> # Install GTK3 runtime from https://github.com/nickvdp/weasyprint-win
> # Or use MSYS2: pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-cairo
> ```
>
> **macOS:**
> ```bash
> brew install pango cairo libffi gdk-pixbuf
> ```
>
> **Linux (Debian/Ubuntu):**
> ```bash
> sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi-dev libgdk-pixbuf2.0-0
> ```

> **Error: "pip install -e .[dev]" fails with "no pyproject.toml found"**
>
> *Cause:* You are not in the `poc-backend` directory.
>
> *Fix:* Ensure your working directory is `poc-backend/`, not the project root.

### 8.3 Verify Environment Variables

The `.env` file should have been generated by `deploy.ps1` in Phase 3. Verify it exists and has real values:

```powershell
Get-Content .env | Select-String "AI_FOUNDRY_ENDPOINT"
```

If the `.env` file contains placeholder values (e.g., `your_ai_foundry_key_here`), you need to re-run `deploy.ps1` or manually populate it with values from Azure Portal / Key Vault.

### 8.4 Run Locally

```bash
cd poc-backend
uvicorn app.main:app --reload --port 8000
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Open [http://localhost:8000/health](http://localhost:8000/health) to verify.

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the Swagger UI (only available when `ENVIRONMENT=poc` or `ENVIRONMENT=development`).

> **Error: "ModuleNotFoundError: No module named 'app'"**
>
> *Cause:* Running uvicorn from the wrong directory.
>
> *Fix:* Ensure you are in the `poc-backend/` directory, not `poc-backend/app/`.

> **Error: "Address already in use: port 8000"**
>
> *Cause:* Another process is using port 8000.
>
> *Fix:* Use a different port: `uvicorn app.main:app --reload --port 8001`. Or find and kill the conflicting process.

> **Error: "RuntimeError: COSMOS_CONNECTION is empty"**
>
> *Cause:* The `.env` file is missing or has placeholder values.
>
> *Fix:* Verify `.env` exists in `poc-backend/` and contains real connection strings from the deployment.

### 8.5 Alternative: Dev Container Setup

If you have Docker installed and use VS Code or Cursor:

1. Open the project root folder in your editor.
2. When prompted "Reopen in Container", click **Yes**.
3. Alternatively: open the Command Palette (`Ctrl+Shift+P`) > **Dev Containers: Reopen in Container**.
4. The container installs Python 3.12, Azure CLI, and all pip dependencies automatically.

The Dev Container forwards port 8000 and 27017 (for local MongoDB if needed).

> **Error: Dev Container build fails at "docker buildx"**
>
> *Cause:* Docker buildx plugin is not installed or Docker Desktop is not running.
>
> *Fix:* Use the fallback configuration: rename `.devcontainer/devcontainer.fallback.json` to `.devcontainer/devcontainer.json` and rebuild. Or run the repair script: `.devcontainer/devcontainer-repair.ps1`.

### 8.6 Run Tests

```bash
cd poc-backend
pytest tests/ -v
```

Expected: all tests pass. Target coverage is 80% for new code.

> **Error: Tests fail with "COSMOS_CONNECTION" errors**
>
> *Cause:* Some integration tests require a real Cosmos DB connection.
>
> *Fix:* Ensure `.env` is populated, or run only unit tests: `pytest tests/ -v -k "not integration"`.

**Phase 8 Checkpoint:** The backend runs locally at `http://localhost:8000/health` and returns `{"status": "healthy"}`.

---

## Phase 9: End-to-End Verification

This phase verifies the complete flow: user message in Teams -> LLM generation -> human review -> PDF output.

### 9.1 Health Check

```bash
curl https://<BACKEND_FQDN>/health
```

Expected: `{"status": "healthy", "environment": "poc"}`.

### 9.2 Start a Conversation

In Microsoft Teams, open the **agentize AI** bot and send:

```
Szia! Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról.
```

### 9.3 Verify the Review Card

The bot should respond with:
1. A processing message: `⏳ Feldolgozom a kérésedet...`
2. An **Adaptive Card** showing the generated draft with:
   - The EU AI Act label: `⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.`
   - Two buttons: **✅ Jóváhagyom a vázlatot** and **✏️ Szerkesztés kérem**

> **Error: Bot does not respond at all**
>
> *Cause:* Bot messaging endpoint is unreachable, or the Entra App Registration is misconfigured.
>
> *Fix:*
> 1. Verify the messaging endpoint: Azure Portal > Bot Service > `bot-agentize-poc` > Configuration > Messaging endpoint should be `https://<BACKEND_FQDN>/api/messages`.
> 2. Check Container App logs for errors.
> 3. Verify the `/health` endpoint is reachable.

> **Error: Bot responds with an error message instead of a card**
>
> *Cause:* AI Foundry call failed, or environment variables are missing.
>
> *Fix:* Check Container App logs: `az containerapp logs show --name ca-agentize-poc-backend --resource-group rg-agentize-poc-swedencentral --follow`. Look for `AI Foundry` or `LLM` errors.

### 9.4 Test the Revision Loop

Click **✏️ Szerkesztés kérem** on the review card. Enter a revision request, e.g.:

```
A 3. lépésben add hozzá a hőmérséklet ellenőrzést.
```

A new Adaptive Card should appear with the updated draft.

### 9.5 Test Approval and PDF Generation

1. Click **✅ Jóváhagyom a vázlatot** on the review card.
2. A **Final Approval Card** appears with `⚠️ AI által generált tartalom` warning.
3. Click **✅ Ellenőriztem és jóváhagyom**.
4. The bot responds with `⏳ PDF generálás folyamatban...`.
5. A **Result Card** appears with a **📥 PDF letöltés** button.

> **Error: PDF generation fails or times out**
>
> *Cause:* Blob Storage connection is invalid, WeasyPrint rendering fails, or the Jinja2 template has errors.
>
> *Fix:*
> 1. Check Container App logs for `weasyprint` or `blob` errors.
> 2. Verify Blob Storage connection: `az storage container list --connection-string "<BLOB_CONNECTION>" --output table`.
> 3. Verify the `pdf-output` container exists.

### 9.6 Verify PDF Content

Download the PDF and verify:

- The document title and content match the generated draft.
- The footer contains: `agentize.eu — AI által generált tartalom — {page}/{pages}`.
- The approval box (green) is present with the approver name and timestamp.

> **Error: PDF downloads but content is empty or corrupted**
>
> *Cause:* Blob SAS URL expired, or the PDF was not uploaded correctly.
>
> *Fix:* Check the Blob container directly in Azure Portal > Storage Account > Containers > `pdf-output`. Verify the file exists and is non-zero size.

**Phase 9 Checkpoint:** You completed a full conversation cycle: message -> draft review -> revision -> approval -> PDF download. The system is operational.

---

## Appendix A: Troubleshooting Reference

A quick-reference table for the most common issues across all phases.

| Symptom | Phase | Cause | Fix |
|---|---|---|---|
| `az login` hangs | 0, 3 | MFA / proxy / firewall | Use `az login --use-device-code` |
| "Insufficient privileges" on App Registration | 3 | Missing Application Administrator role | Phase 0.2 — ask admin to assign the role |
| AI Foundry deployment `Conflict` | 3 | DataZoneStandard capacity exhausted | Wait and retry, request quota, or use `germanywestcentral` |
| Key Vault name already taken | 3 | Soft-deleted vault with same name | `az keyvault purge --name kv-agentize-poc --location swedencentral` |
| Container App not healthy | 4 | KV secrets unresolved or image pull failure | Check container logs and KV secret list |
| `/health` endpoint unreachable | 4 | Container still starting | Wait 60s and retry |
| GitHub Actions: "Login to Azure" fails | 5 | `AZURE_CREDENTIALS` secret missing/invalid | Recreate SP and update GitHub secret |
| Teams: "Upload custom app" not visible | 6 | Admin disabled sideloading | Teams admin center > Setup policies > enable sideloading |
| Teams: "bot ID does not match" | 6 | `botId` in manifest is wrong | Match `BOT_APP_ID` from `.env` |
| Bot not responding in Teams | 9 | Messaging endpoint misconfigured | Azure Portal > Bot Service > Configuration > verify endpoint URL |
| PDF generation fails | 9 | Blob connection invalid or WeasyPrint error | Check logs for `blob` / `weasyprint` errors |
| WeasyPrint build fails locally | 8 | Missing system libraries (pango, cairo) | Install platform-specific packages (see Phase 8.2) |
| `ModuleNotFoundError: app` | 8 | Running uvicorn from wrong directory | Run from `poc-backend/`, not `poc-backend/app/` |
| Cosmos DB connection refused | 8 | `.env` has placeholder connection string | Re-run `deploy.ps1` or copy from Key Vault |
| Telegram token invalid | 7 | Token changed or bot deleted | Regenerate via BotFather `/token` |
| Pre-commit hook fails | 2 | Gitleaks detects a secret in staged files | Remove the secret from code; use `.env` or Key Vault |
| Dev Container build fails | 8 | Docker buildx issue | Use fallback config or run `devcontainer-repair.ps1` |

---

## Appendix B: Environment Variables Reference

All variables are defined in `poc-backend/app/config.py` and loaded from `poc-backend/.env` via pydantic-settings.

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_FOUNDRY_ENDPOINT` | Yes | `""` | Azure AI Foundry inference endpoint URL |
| `AI_FOUNDRY_KEY` | Yes | `""` | Azure AI Foundry API key |
| `AI_MODEL` | No | `gpt-4o` | Model deployment name (e.g., `gpt-4o`, `Mistral-Large-3`) |
| `AI_TEMPERATURE` | No | `0.3` | LLM temperature (keep <= 0.3 per EU AI Act rule) |
| `AI_MAX_TOKENS` | No | `4000` | Maximum tokens per LLM completion |
| `COSMOS_CONNECTION` | Yes | `""` | Cosmos DB (MongoDB API) connection string |
| `COSMOS_DATABASE` | No | `agentize-poc-db` | Cosmos DB database name |
| `BLOB_CONNECTION` | Yes | `""` | Azure Blob Storage connection string |
| `BLOB_CONTAINER` | No | `pdf-output` | Blob container name for generated PDFs |
| `KEY_VAULT_URL` | No | `""` | Azure Key Vault URL (optional — secrets injected via Container App) |
| `KEY_VAULT_URI` | No | `""` | Azure Key Vault URI (alias for `KEY_VAULT_URL`) |
| `BOT_APP_ID` | Yes | `""` | Entra ID App Registration Client ID |
| `BOT_APP_PASSWORD` | Yes | `""` | Entra ID App Registration Client Secret |
| `TELEGRAM_BOT_TOKEN` | No | `""` | Telegram bot token from BotFather |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | `""` | Application Insights connection string for telemetry |
| `ENVIRONMENT` | No | `poc` | Environment name (`poc`, `development`, `production`) |
| `LOG_LEVEL` | No | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

**Variables marked "Yes" are required for the application to function.** The deployment script (`deploy.ps1`) populates all of them automatically.

---

## Appendix C: Azure Resource Naming Reference

All resources follow the `{type}-{projectPrefix}` naming convention with `projectPrefix = agentize-poc`.

| Resource Type | Resource Name | Location | Purpose |
|---|---|---|---|
| Resource Group | `rg-agentize-poc-swedencentral` | Sweden Central | All PoC resources |
| Virtual Network | `vnet-agentize-poc` | Sweden Central | Network isolation |
| Network Security Group | `nsg-agentize-poc` | Sweden Central | Network security rules |
| Log Analytics Workspace | `log-agentize-poc` | Sweden Central | Centralized logging |
| Application Insights | `appi-agentize-poc` | Sweden Central | APM and telemetry |
| Key Vault | `kv-agentize-poc` | Sweden Central | Secret management |
| Container App Environment | `cae-agentize-poc` | Sweden Central | Container hosting platform |
| Container App | `ca-agentize-poc-backend` | Sweden Central | FastAPI backend |
| Azure AI Foundry | `ai-agentize-poc` | Sweden Central | LLM inference (DataZoneStandard) |
| Cosmos DB Account | `cosmos-agentize-poc` | Sweden Central | MongoDB API database |
| Storage Account | `stagentizepoc` | Sweden Central | Blob storage for PDFs |
| Bot Service | `bot-agentize-poc` | Global | Bot Framework registration |

**Key Vault Secrets:**

| Secret Name | Contents |
|---|---|
| `ai-foundry-key` | AI Foundry API key |
| `cosmos-connection` | Cosmos DB MongoDB connection string |
| `blob-connection` | Blob Storage connection string |
| `bot-app-password` | Entra ID App Registration client secret |

**Cosmos DB Collections** (in database `agentize-poc-db`):

| Collection | Purpose |
|---|---|
| `conversations` | Chat conversation state |
| `agent_state` | LangGraph agent checkpoints |
| `generated_documents` | Metadata for generated PDFs |
| `audit_log` | EU AI Act compliance audit trail |
