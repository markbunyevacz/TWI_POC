#!/usr/bin/env bash
# deploy.sh — agentize.eu PoC Infrastructure Deploy (CI/CD / Linux)
# Mirrors deploy.ps1 logic for GitHub Actions and bash environments
#
# Usage:
#   ./deploy.sh
#   BOT_APP_ID=<id> BOT_APP_PASSWORD=<pwd> ./deploy.sh
#   TELEGRAM_BOT_TOKEN=<token> ./deploy.sh

set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-agentize-poc-swedencentral}"
LOCATION="${LOCATION:-swedencentral}"
PROJECT_PREFIX="${PROJECT_PREFIX:-agentize-poc}"
BOT_APP_ID="${BOT_APP_ID:-}"
BOT_APP_PASSWORD="${BOT_APP_PASSWORD:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-ghcr.io/agentize-eu/poc-backend:latest}"
WHAT_IF="${WHAT_IF:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Helpers ──────────────────────────────────────────────────────────────────

green()  { echo -e "\033[32m    ✅ $*\033[0m"; }
yellow() { echo -e "\033[33m    ⚠️  $*\033[0m"; }
red()    { echo -e "\033[31m    ❌ $*\033[0m"; exit 1; }
step()   { echo -e "\n\033[36m[$1] $2\033[0m"; }

# ─── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo -e "\033[36m╔══════════════════════════════════════════════════╗\033[0m"
echo -e "\033[36m║   agentize.eu PoC — Infrastructure Deploy        ║\033[0m"
echo -e "\033[36m║   Day 1-2 | Sweden Central | EU Data Zone Std    ║\033[0m"
echo -e "\033[36m╚══════════════════════════════════════════════════╝\033[0m"
echo ""

[[ "$WHAT_IF" == "true" ]] && yellow "WhatIf mode — no resources will be created"

# ─── Step 0: Prerequisites ────────────────────────────────────────────────────

step 0 "Prerequisites"

az version --query '"azure-cli"' -o tsv > /dev/null 2>&1 || red "Azure CLI not found"
AZ_VER=$(az version --query '"azure-cli"' -o tsv)
green "Azure CLI $AZ_VER"

SUBSCRIPTION=$(az account show --query 'name' -o tsv 2>/dev/null || true)
if [[ -z "$SUBSCRIPTION" ]]; then
    yellow "Not logged in — running az login..."
    az login
    SUBSCRIPTION=$(az account show --query 'name' -o tsv)
fi
SUBSCRIPTION_ID=$(az account show --query 'id' -o tsv)
green "Subscription: $SUBSCRIPTION ($SUBSCRIPTION_ID)"

# ─── Step 1: Entra ID App Registration ───────────────────────────────────────

step 1 "Entra ID App Registration"

if [[ -n "$BOT_APP_ID" && -n "$BOT_APP_PASSWORD" ]]; then
    green "Using existing App Registration: $BOT_APP_ID"
else
    echo "    Creating Entra ID App Registration 'agentize-poc-bot'..."

    if [[ "$WHAT_IF" != "true" ]]; then
        APP_JSON=$(az ad app create \
            --display-name 'agentize-poc-bot' \
            --sign-in-audience 'AzureADMyOrg' \
            --query '{appId:appId}' -o json)
        BOT_APP_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['appId'])")
        green "App Registration created: $BOT_APP_ID"

        az ad sp create --id "$BOT_APP_ID" > /dev/null
        green "Service Principal created"

        BOT_APP_PASSWORD=$(az ad app credential reset \
            --id "$BOT_APP_ID" \
            --years 2 \
            --display-name 'poc-deploy' \
            --query 'password' -o tsv)
        green "Client secret generated (2-year validity)"

        az ad app permission add \
            --id "$BOT_APP_ID" \
            --api 00000003-0000-0000-c000-000000000000 \
            --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope > /dev/null
        green "Graph User.Read permission added"

        yellow "BOT_APP_ID: $BOT_APP_ID — save this"
    else
        yellow "[WhatIf] Would create App Registration"
        BOT_APP_ID="whatif-app-id"
        BOT_APP_PASSWORD="whatif-password"
    fi
fi

# ─── Step 2: Resource Group ───────────────────────────────────────────────────

step 2 "Resource Group: $RESOURCE_GROUP ($LOCATION)"

if [[ "$WHAT_IF" != "true" ]]; then
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" > /dev/null
    green "Resource group ready"
else
    yellow "[WhatIf] Would create resource group $RESOURCE_GROUP"
fi

# ─── Step 3: Bicep Deployment ─────────────────────────────────────────────────

step 3 "Bicep deployment (5-15 min)"

TEMPLATE_FILE="$SCRIPT_DIR/main.bicep"

if [[ "$WHAT_IF" != "true" ]]; then
    OUTPUTS=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$TEMPLATE_FILE" \
        --parameters \
            location="$LOCATION" \
            projectPrefix="$PROJECT_PREFIX" \
            botAppId="$BOT_APP_ID" \
            botAppPassword="$BOT_APP_PASSWORD" \
            telegramBotToken="$TELEGRAM_BOT_TOKEN" \
            containerImage="$CONTAINER_IMAGE" \
        --query 'properties.outputs' \
        -o json)

    BACKEND_FQDN=$(echo "$OUTPUTS"              | python3 -c "import sys,json; print(json.load(sys.stdin)['backendFqdn']['value'])")
    AI_FOUNDRY_ENDPOINT=$(echo "$OUTPUTS"       | python3 -c "import sys,json; print(json.load(sys.stdin)['aiFoundryEndpoint']['value'])")
    AI_FOUNDRY_INFERENCE_EP=$(echo "$OUTPUTS"   | python3 -c "import sys,json; print(json.load(sys.stdin)['aiFoundryInferenceEndpoint']['value'])")
    COSMOS_ACCOUNT=$(echo "$OUTPUTS"            | python3 -c "import sys,json; print(json.load(sys.stdin)['cosmosAccountName']['value'])")
    STORAGE_ACCOUNT=$(echo "$OUTPUTS"           | python3 -c "import sys,json; print(json.load(sys.stdin)['storageAccountName']['value'])")
    KV_NAME=$(echo "$OUTPUTS"                   | python3 -c "import sys,json; print(json.load(sys.stdin)['keyVaultName']['value'])")
    KV_URI=$(echo "$OUTPUTS"                    | python3 -c "import sys,json; print(json.load(sys.stdin)['keyVaultUri']['value'])")
    APP_INSIGHTS_CS=$(echo "$OUTPUTS"           | python3 -c "import sys,json; print(json.load(sys.stdin)['appInsightsConnectionString']['value'])")

    green "Bicep deployment complete"
    green "Backend FQDN: $BACKEND_FQDN"
    green "AI Foundry:   $AI_FOUNDRY_ENDPOINT"
else
    yellow "[WhatIf] Would deploy $TEMPLATE_FILE"
    BACKEND_FQDN="ca-$PROJECT_PREFIX-backend.<hash>.$LOCATION.azurecontainerapps.io"
    AI_FOUNDRY_ENDPOINT="https://ai-$PROJECT_PREFIX.cognitiveservices.azure.com/"
    AI_FOUNDRY_INFERENCE_EP="https://ai-$PROJECT_PREFIX.services.ai.azure.com/models"
    COSMOS_ACCOUNT="cosmos-$PROJECT_PREFIX"
    STORAGE_ACCOUNT="${PROJECT_PREFIX//-/}"
    KV_NAME="kv-$PROJECT_PREFIX"
    KV_URI="https://kv-$PROJECT_PREFIX.vault.azure.net/"
    APP_INSIGHTS_CS="InstrumentationKey=whatif"
fi

# ─── Step 4: Retrieve Service Keys ───────────────────────────────────────────

step 4 "Retrieving service keys"

if [[ "$WHAT_IF" != "true" ]]; then
    AI_FOUNDRY_KEY=$(az cognitiveservices account keys list \
        --name "ai-$PROJECT_PREFIX" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'key1' -o tsv)
    green "AI Foundry key retrieved"

    COSMOS_CONNECTION=$(az cosmosdb keys list \
        --name "$COSMOS_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --type 'connection-strings' \
        --query 'connectionStrings[0].connectionString' -o tsv)
    green "Cosmos DB connection string retrieved"

    BLOB_CONNECTION=$(az storage account show-connection-string \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'connectionString' -o tsv)
    green "Blob Storage connection string retrieved"
else
    yellow "[WhatIf] Would retrieve service keys"
    AI_FOUNDRY_KEY="whatif-ai-key"
    COSMOS_CONNECTION="mongodb://whatif"
    BLOB_CONNECTION="DefaultEndpointsProtocol=https;AccountName=whatif"
fi

# ─── Step 5: Grant Deployer Key Vault Access ──────────────────────────────────

step 5 "Granting deployer Key Vault Secrets Officer access"

if [[ "$WHAT_IF" != "true" ]]; then
    CURRENT_USER_OID=$(az ad signed-in-user show --query 'id' -o tsv 2>/dev/null || \
        az account show --query 'user.name' -o tsv)

    KV_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KV_NAME"

    az role assignment create \
        --assignee "$CURRENT_USER_OID" \
        --role 'Key Vault Secrets Officer' \
        --scope "$KV_SCOPE" > /dev/null 2>&1 || yellow "Role may already exist — continuing"
    green "Key Vault Secrets Officer role assigned"

    echo "    Waiting 15s for RBAC propagation..."
    sleep 15
else
    yellow "[WhatIf] Would assign Key Vault Secrets Officer"
fi

# ─── Step 6: Populate Key Vault Secrets ──────────────────────────────────────

step 6 "Populating Key Vault secrets ($KV_NAME)"

if [[ "$WHAT_IF" != "true" ]]; then
    declare -A SECRETS=(
        ["ai-foundry-key"]="$AI_FOUNDRY_KEY"
        ["cosmos-connection"]="$COSMOS_CONNECTION"
        ["blob-connection"]="$BLOB_CONNECTION"
        ["bot-app-password"]="$BOT_APP_PASSWORD"
    )

    for SECRET_NAME in "${!SECRETS[@]}"; do
        az keyvault secret set \
            --vault-name "$KV_NAME" \
            --name "$SECRET_NAME" \
            --value "${SECRETS[$SECRET_NAME]}" > /dev/null
        green "Secret stored: $SECRET_NAME"
    done
else
    yellow "[WhatIf] Would store 4 secrets in Key Vault"
fi

# ─── Step 7: Restart Container App ───────────────────────────────────────────

step 7 "Restarting Container App to resolve Key Vault secrets"

if [[ "$WHAT_IF" != "true" ]]; then
    az containerapp update \
        --name "ca-$PROJECT_PREFIX-backend" \
        --resource-group "$RESOURCE_GROUP" \
        --revision-suffix "kvsecrets" > /dev/null
    green "Container App updated — new revision starting (allow 30-60s)"
else
    yellow "[WhatIf] Would restart Container App"
fi

# ─── Step 8: Write .env ───────────────────────────────────────────────────────

step 8 "Writing .env for local development"

ENV_PATH="$(dirname "$SCRIPT_DIR")/.env"
cat > "$ENV_PATH" <<EOF
# .env — agentize.eu PoC Local Development
# Generated by deploy.sh on $(date -u +"%Y-%m-%d %H:%M UTC")
# DO NOT COMMIT — verify .gitignore covers .env

AI_FOUNDRY_ENDPOINT=$AI_FOUNDRY_INFERENCE_EP
AI_FOUNDRY_KEY=$AI_FOUNDRY_KEY
AI_MODEL=mistral-large-latest
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=4000

COSMOS_CONNECTION=$COSMOS_CONNECTION
COSMOS_DATABASE=$PROJECT_PREFIX-db

BLOB_CONNECTION=$BLOB_CONNECTION
BLOB_CONTAINER=pdf-output

BOT_APP_ID=$BOT_APP_ID
BOT_APP_PASSWORD=$BOT_APP_PASSWORD

TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN

APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_CS

ENVIRONMENT=poc
LOG_LEVEL=INFO
EOF

green ".env written to $ENV_PATH"
yellow ".env contains secrets — ensure .gitignore covers it"

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo -e "\033[32m╔══════════════════════════════════════════════════╗\033[0m"
echo -e "\033[32m║   Day 1-2 Deployment Complete!                   ║\033[0m"
echo -e "\033[32m╚══════════════════════════════════════════════════╝\033[0m"
echo ""
echo "Resource Group : $RESOURCE_GROUP"
echo "Backend URL    : https://$BACKEND_FQDN"
echo "Bot Endpoint   : https://$BACKEND_FQDN/api/messages"
echo "AI Foundry     : $AI_FOUNDRY_INFERENCE_EP"
echo "Key Vault      : $KV_URI"
echo ""
echo -e "\033[33mNext steps:\033[0m"
echo "  1. Run ./validate.sh (or validate.ps1) to verify resources"
echo "  2. Register bot endpoint: https://$BACKEND_FQDN/api/messages"
echo "  3. Start Day 3-4: Backend Core development"
echo ""
