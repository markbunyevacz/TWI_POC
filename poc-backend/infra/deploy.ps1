# deploy.ps1 - agentize.eu PoC Full Infrastructure Deploy
# Covers Day 1-2 checklist: App Reg, RG, Bicep, KV secrets, validation
#
# Prerequisites:
#   - Azure CLI installed (https://aka.ms/installazurecli)
#   - az login completed
#   - Sufficient permissions: Contributor on subscription + Global Admin / App Admin in Entra ID
#
# Usage:
#   .\deploy.ps1                                    # Interactive, creates new App Registration
#   .\deploy.ps1 -BotAppId <id> -SkipAppReg        # Use existing App Registration
#   .\deploy.ps1 -TelegramBotToken <token>          # Include Telegram channel

param(
    [string]$ResourceGroup      = 'rg-agentize-poc-swedencentral',
    [string]$Location           = 'swedencentral',
    [string]$ProjectPrefix      = 'agentize-poc',
    [string]$BotAppId           = '',
    [string]$BotAppPassword     = '',
    [string]$TelegramBotToken   = '',
    [switch]$SkipAppReg,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Helpers ------------------------------------------------------------------

function Write-Step($n, $msg) {
    Write-Host "`n[$n] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg)   { Write-Host "    ✅ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    ⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    ❌ $msg" -ForegroundColor Red }

function Confirm-AzLogin {
    $account = az account show -o json 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Warn "Not logged in - running az login..."
        az login | Out-Null
        $account = az account show -o json | ConvertFrom-Json
    }
    return $account
}

# --- Banner -------------------------------------------------------------------

Write-Host ''
Write-Host '+------------------------------------------------------+' -ForegroundColor Cyan
Write-Host '|   agentize.eu PoC - Infrastructure Deploy            |' -ForegroundColor Cyan
Write-Host '|   Day 1-2 | Sweden Central | EU Data Zone Std        |' -ForegroundColor Cyan
Write-Host '+------------------------------------------------------+' -ForegroundColor Cyan

if ($WhatIf) {
    Write-Warn "WhatIf mode - no resources will be created"
}

# --- Step 0: Prerequisites ----------------------------------------------------

Write-Step 0 'Prerequisites'

$azVersion = az version --query '"azure-cli"' -o tsv 2>$null
if (-not $azVersion) {
    Write-Fail 'Azure CLI not found. Install: https://aka.ms/installazurecli'
    exit 1
}
Write-Ok "Azure CLI $azVersion"

$account = Confirm-AzLogin
Write-Ok "Subscription: $($account.name) ($($account.id))"
Write-Ok "Tenant: $($account.tenantId)"

# --- Step 1: Entra ID App Registration ---------------------------------------

Write-Step 1 'Entra ID App Registration (Bot Framework identity)'

if ($BotAppId -and ($SkipAppReg -or $BotAppPassword)) {
    Write-Ok "Using existing App Registration: $BotAppId"
    if (-not $BotAppPassword) {
        $secPwd = Read-Host '    Enter client secret for this App Registration' -AsSecureString
        $BotAppPassword = [System.Net.NetworkCredential]::new('', $secPwd).Password
    }
} else {
    Write-Host '    Creating Entra ID App Registration "agentize-poc-bot"...'

    if (-not $WhatIf) {
        $app = az ad app create `
            --display-name 'agentize-poc-bot' `
            --sign-in-audience 'AzureADMyOrg' `
            --query '{appId:appId,id:id}' `
            -o json | ConvertFrom-Json

        $BotAppId = $app.appId
        Write-Ok "App Registration created: $BotAppId"

        # Service Principal (required by Bot Service)
        az ad sp create --id $BotAppId | Out-Null
        Write-Ok 'Service Principal created'

        # Client secret — 2 year validity
        $credResult = az ad app credential reset `
            --id $BotAppId `
            --years 2 `
            --display-name 'poc-deploy' `
            --query 'password' `
            -o tsv
        $BotAppPassword = $credResult
        Write-Ok "Client secret generated (2-year validity)"

        # Grant User.Read (required by Bot Framework for identity context)
        $graphId = az ad sp list --filter "displayName eq 'Microsoft Graph'" --query "[0].id" -o tsv
        az ad app permission add `
            --id $BotAppId `
            --api 00000003-0000-0000-c000-000000000000 `
            --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope | Out-Null
        Write-Ok 'Graph User.Read permission added'

        Write-Warn 'Save these — you will need them for local .env:'
        Write-Host "    BOT_APP_ID:       $BotAppId" -ForegroundColor White
        Write-Host "    BOT_APP_PASSWORD: [stored in Key Vault after deploy]" -ForegroundColor White
    } else {
        Write-Warn '[WhatIf] Would create App Registration'
        $BotAppId = 'whatif-app-id'
        $BotAppPassword = 'whatif-password'
    }
}

# --- Step 2: Resource Group ---------------------------------------------------

Write-Step 2 "Resource Group: $ResourceGroup ($Location)"

if (-not $WhatIf) {
    az group create --name $ResourceGroup --location $Location | Out-Null
    Write-Ok "Resource group ready"
} else {
    Write-Warn "[WhatIf] Would create resource group $ResourceGroup"
}

# --- Step 3: Bicep Deployment -------------------------------------------------

Write-Step 3 'Bicep deployment (5-15 min - AI Foundry model takes longest)'

$templateFile = Join-Path $PSScriptRoot "main.bicep"

if (-not $WhatIf) {
    Write-Host '    Deploying... (tail Container App logs in another terminal to monitor)'

    $deployArgs = @(
        'deployment', 'group', 'create',
        '--resource-group', $ResourceGroup,
        '--template-file', $templateFile,
        '--parameters',
        "location=$Location",
        "projectPrefix=$ProjectPrefix",
        "botAppId=$BotAppId",
        "botAppPassword=$BotAppPassword",
        "telegramBotToken=$TelegramBotToken",
        '--query', 'properties.outputs',
        '-o', 'json'
    )

    $outputJson = az @deployArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Fail 'Bicep deployment failed. Check Azure portal for details.'
        exit 1
    }

    $outputs = $outputJson | ConvertFrom-Json
    Write-Ok 'Bicep deployment complete'

    $backendFqdn              = $outputs.backendFqdn.value
    $aiFoundryEndpoint        = $outputs.aiFoundryEndpoint.value
    $aiFoundryInferenceEp     = $outputs.aiFoundryInferenceEndpoint.value
    $cosmosAccountName        = $outputs.cosmosAccountName.value
    $storageAccountName       = $outputs.storageAccountName.value
    $keyVaultName             = $outputs.keyVaultName.value
    $keyVaultUri              = $outputs.keyVaultUri.value
    $appInsightsCs            = $outputs.appInsightsConnectionString.value
    $containerAppPrincipalId  = $outputs.containerAppPrincipalId.value

    Write-Ok "Backend FQDN: $backendFqdn"
    Write-Ok "AI Foundry:   $aiFoundryEndpoint"
    Write-Ok "Key Vault:    $keyVaultUri"
} else {
    Write-Warn "[WhatIf] Would deploy $templateFile to $ResourceGroup"
    $backendFqdn             = 'ca-agentize-poc-backend.<hash>.swedencentral.azurecontainerapps.io'
    $aiFoundryEndpoint       = "https://ai-$ProjectPrefix.cognitiveservices.azure.com/"
    $aiFoundryInferenceEp    = "https://ai-$ProjectPrefix.services.ai.azure.com/models"
    $cosmosAccountName       = "cosmos-$ProjectPrefix"
    $storageAccountName      = $ProjectPrefix.Replace('-','')
    $keyVaultName            = "kv-$ProjectPrefix"
    $keyVaultUri             = "https://kv-$ProjectPrefix.vault.azure.net/"
    $appInsightsCs           = 'InstrumentationKey=whatif'
    $containerAppPrincipalId = 'whatif-principal-id'
}

# --- Step 4: Retrieve Generated Service Keys ----------------------------------

Write-Step 4 'Retrieving service keys for Key Vault storage'

if (-not $WhatIf) {
    # AI Foundry API key
    $aiFoundryKey = az cognitiveservices account keys list `
        --name "ai-$ProjectPrefix" `
        --resource-group $ResourceGroup `
        --query 'key1' -o tsv
    Write-Ok 'AI Foundry key retrieved'

    # Cosmos DB connection string (MongoDB API)
    $cosmosConnection = az cosmosdb keys list `
        --name $cosmosAccountName `
        --resource-group $ResourceGroup `
        --type 'connection-strings' `
        --query 'connectionStrings[0].connectionString' -o tsv
    Write-Ok 'Cosmos DB connection string retrieved'

    # Blob Storage connection string
    $blobConnection = az storage account show-connection-string `
        --name $storageAccountName `
        --resource-group $ResourceGroup `
        --query 'connectionString' -o tsv
    Write-Ok 'Blob Storage connection string retrieved'
} else {
    Write-Warn '[WhatIf] Would retrieve AI Foundry key, Cosmos connection, Blob connection'
    $aiFoundryKey    = 'whatif-ai-key'
    $cosmosConnection = 'mongodb://whatif'
    $blobConnection  = 'DefaultEndpointsProtocol=https;AccountName=whatif'
}

# --- Step 5: Grant Deployer Key Vault Access ----------------------------------

Write-Step 5 'Granting deployer Key Vault Secrets Officer access'

if (-not $WhatIf) {
    $currentUserOid = az ad signed-in-user show --query 'id' -o tsv
    $subscriptionId = az account show --query 'id' -o tsv
    $kvScope = "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.KeyVault/vaults/$keyVaultName"

    az role assignment create `
        --assignee $currentUserOid `
        --role 'Key Vault Secrets Officer' `
        --scope $kvScope | Out-Null
    Write-Ok 'Key Vault Secrets Officer role assigned to current user'

    # Brief wait for RBAC propagation
    Write-Host '    Waiting 15s for RBAC propagation...' -NoNewline
    Start-Sleep 15
    Write-Host ' done'
} else {
    Write-Warn '[WhatIf] Would assign Key Vault Secrets Officer to current user'
}

# --- Step 6: Populate Key Vault Secrets --------------------------------------

Write-Step 6 "Populating Key Vault secrets ($keyVaultName)"

if (-not $WhatIf) {
    $secrets = @{
        'ai-foundry-key'    = $aiFoundryKey
        'cosmos-connection' = $cosmosConnection
        'blob-connection'   = $blobConnection
        'bot-app-password'  = $BotAppPassword
    }

    foreach ($name in $secrets.Keys) {
        az keyvault secret set `
            --vault-name $keyVaultName `
            --name $name `
            --value $secrets[$name] | Out-Null
        Write-Ok "Secret stored: $name"
    }
} else {
    Write-Warn '[WhatIf] Would store 4 secrets in Key Vault'
}

# --- Step 7: Restart Container App -------------------------------------------

Write-Step 7 'Restarting Container App to resolve Key Vault secrets'

if (-not $WhatIf) {
    # Create a new revision to force secret resolution
    az containerapp update `
        --name "ca-$ProjectPrefix-backend" `
        --resource-group $ResourceGroup `
        --revision-suffix "kvsecrets" | Out-Null
    Write-Ok 'Container App updated - new revision starting'
    Write-Host '    (Allow 30-60s for container to become healthy)'
} else {
    Write-Warn '[WhatIf] Would restart Container App'
}

# --- Step 8: Generate .env for local development ------------------------------

Write-Step 8 'Generating .env file for local development'

$envContent = @"
# .env - agentize.eu PoC Local Development
# Generated by deploy.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm')
# DO NOT COMMIT - add .env to .gitignore

# Azure AI Foundry
AI_FOUNDRY_ENDPOINT=$aiFoundryInferenceEp
AI_FOUNDRY_KEY=$aiFoundryKey
AI_MODEL=mistral-large-latest
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=4000

# Cosmos DB (MongoDB API)
COSMOS_CONNECTION=$cosmosConnection
COSMOS_DATABASE=$ProjectPrefix-db

# Blob Storage
BLOB_CONNECTION=$blobConnection
BLOB_CONTAINER=pdf-output

# Bot Framework
BOT_APP_ID=$BotAppId
BOT_APP_PASSWORD=$BotAppPassword

# Telegram (optional)
TELEGRAM_BOT_TOKEN=$TelegramBotToken

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=$appInsightsCs

# App
ENVIRONMENT=poc
LOG_LEVEL=INFO
"@

$envPath = Join-Path (Split-Path $PSScriptRoot) '.env'
$envContent | Out-File -FilePath $envPath -Encoding utf8 -NoNewline
Write-Ok ".env written to: $envPath"
Write-Warn '.env contains secrets - verify .gitignore covers it'

# --- Summary ------------------------------------------------------------------

Write-Host ''
Write-Host '+------------------------------------------------------+' -ForegroundColor Green
Write-Host '|   Day 1-2 Deployment Complete!                       |' -ForegroundColor Green
Write-Host '+------------------------------------------------------+' -ForegroundColor Green
Write-Host ''
Write-Host "Resource Group : $ResourceGroup"
Write-Host "Backend URL    : https://$backendFqdn"
Write-Host "Bot Endpoint   : https://$backendFqdn/api/messages"
Write-Host "AI Foundry     : $aiFoundryInferenceEp"
Write-Host "Key Vault      : $keyVaultUri"
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Run .\validate.ps1 to verify all resources are healthy'
Write-Host '  2. Register bot endpoint in Azure Bot Service (if not already)'
Write-Host "     Endpoint: https://$backendFqdn/api/messages"
Write-Host '  3. Sideload Teams app manifest (Day 5-6)'
Write-Host '  4. Start Day 3-4: Backend Core development'
Write-Host ''
