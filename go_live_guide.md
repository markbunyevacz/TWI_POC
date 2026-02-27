# Agentize.eu PoC — Deployment & Go-Live Guide

This guide covers the exact steps required to deploy the PoC infrastructure, configure the application, set up the CI/CD pipeline, and run the system live in Microsoft Teams.

## Prerequisites
Before you start, make sure you have:
1. **Azure CLI** installed locally (`az --version`).
2. An active **Azure Subscription** where you have *Contributor* and *User Access Administrator* roles (to create resources and assign roles).
3. Sufficient privileges in **Entra ID** (formerly Azure AD) to create App Registrations (e.g., *Application Administrator*).
4. **Git** and a GitHub account with admin access to the repository.

---

## Step 1: Deploy Azure Infrastructure

We have a PowerShell script that automates the Bicep deployment, creates the Entra ID App Registration, configures the Azure Key Vault, and generates your local `.env` file.

1. Open your terminal (PowerShell).
2. Log in to Azure:
   ```powershell
   az login
   ```
3. Navigate to the `infra` folder:
   ```powershell
   cd poc-backend/infra
   ```
4. Run the deployment script. It will automatically create an Entra ID App Registration for the bot, deploy the resources to `swedencentral`, and wire up the Key Vault.
   ```powershell
   .\deploy.ps1
   ```
   *Note: This process takes about 10-15 minutes, mostly because provisioning the AI Foundry model takes time.*

5. When the script finishes, it will print a **Summary** block. **Save these values**, especially the `Backend URL` and `Bot Endpoint`. It will also automatically generate a `.env` file in the `poc-backend/` folder for local development.

---

## Step 2: Configure GitHub Actions (CI/CD)

The code relies on GitHub Actions to build the Docker container and push it to Azure Container Apps whenever you push to the `main` branch.

1. **Create an Azure Service Principal for GitHub Actions:**
   Run this in your terminal to create a credential for GitHub:
   ```bash
   az ad sp create-for-rbac --name "github-actions-deploy" --role contributor --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-agentize-poc-swedencentral --sdk-auth
   ```
   *Copy the entire JSON block output.*

2. **Add Secrets to GitHub:**
   - Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
   - Click **New repository secret**.
   - Name: `AZURE_CREDENTIALS`
   - Value: *Paste the JSON block from the previous step.*

3. **Ensure GitHub Container Registry (GHCR) Access:**
   The workflow will use `GITHUB_TOKEN` to push to `ghcr.io`. Make sure your repository has GitHub Actions permissions configured to allow package writes (Settings -> Actions -> General -> Workflow permissions -> Read and write permissions).

4. **Trigger the Deployment:**
   Commit and push your code to the `main` branch. Go to the **Actions** tab in GitHub to watch the Docker image build and deploy to your Azure Container App.

---

## Step 3: Configure Microsoft Teams App Manifest

To use the bot in Teams, you need to package the Manifest file.

1. Open `teams-app/manifest.json`.
2. Replace the placeholders with the actual values:
   - Replace `{{BOT_APP_ID}}` with the Client ID of the Entra ID App Registration created in Step 1 (you can find this in your generated `poc-backend/.env` under `BOT_APP_ID`). **There are two places to replace this.**
   - Replace `{{BACKEND_FQDN}}` with the backend URL from Step 1 (e.g., `ca-agentize-poc-backend.something.swedencentral.azurecontainerapps.io`). Do not include `https://`.
3. Create a ZIP file containing:
   - `manifest.json`
   - `color.png` (Included 192x192 logo)
   - `outline.png` (Included 32x32 transparent logo)
   *Make sure these files are at the root of the ZIP file, not inside a folder.*

---

## Step 4: Sideload into Microsoft Teams

1. Open Microsoft Teams.
2. Go to **Apps** (on the left sidebar) -> **Manage your apps** -> **Upload an app** -> **Upload a custom app**.
3. Select the ZIP file you created in Step 3.
4. Click **Add**. The bot will now appear in your chat list.

---

## Step 5: End-to-End Validation (The Demo)

Now you can run the live demo!

1. **Start the conversation:**
   In Teams, send a message to the bot:
   > "Szia! Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról."

2. **Verify Generation & Review Card:**
   The bot should reply with "⏳ Feldolgozom a kérésedet...", followed by an Adaptive Card showing the draft. Verify that the EU AI Act warning (`⚠️ AI által generált tartalom`) is visible.

3. **Test the Revision Loop:**
   Click **✏️ Szerkesztés kérem**, type something like *"A 3. lépésben add hozzá a hőmérséklet ellenőrzést"*, and submit. Ensure a new card arrives with the updated text.

4. **Test Approval & PDF Generation:**
   Click **✅ Jóváhagyom a vázlatot**. On the final warning card, click **✅ Ellenőriztem és jóváhagyom**. 
   The bot will reply with "⏳ PDF generálás folyamatban...", and then give you a **Result Card**.

5. **Verify the Output:**
   Click **📥 PDF letöltés**. Verify the downloaded PDF contains the correct text, the EU AI Act footer, and the green approval box.

**Congratulations! The PoC is live.**