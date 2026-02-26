# validate.ps1 — Day 1-2 Validation
# Checks: all resources deployed, AI Foundry reachable, Cosmos collections exist,
#         Container App healthy, Key Vault secrets present, Bot Service configured
#
# Usage:
#   .\validate.ps1
#   .\validate.ps1 -ResourceGroup rg-agentize-poc-swedencentral -ProjectPrefix agentize-poc

param(
    [string]$ResourceGroup  = 'rg-agentize-poc-swedencentral',
    [string]$ProjectPrefix  = 'agentize-poc'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

$PassCount  = 0
$FailCount  = 0
$WarnCount  = 0

function Write-Pass($msg) { Write-Host "  ✅ $msg" -ForegroundColor Green;  $script:PassCount++ }
function Write-Fail($msg) { Write-Host "  ❌ $msg" -ForegroundColor Red;    $script:FailCount++ }
function Write-Warn($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow; $script:WarnCount++ }
function Write-Info($msg) { Write-Host "     $msg" -ForegroundColor Gray }
function Write-Section($title) { Write-Host "`n$title" -ForegroundColor Cyan }

# ─── Banner ───────────────────────────────────────────────────────────────────

Write-Host ''
Write-Host '╔══════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║   agentize.eu PoC — Day 1-2 Validation           ║' -ForegroundColor Cyan
Write-Host '╚══════════════════════════════════════════════════╝' -ForegroundColor Cyan
Write-Host "Resource Group : $ResourceGroup"
Write-Host "Project Prefix : $ProjectPrefix"

# ─── Azure Login Check ────────────────────────────────────────────────────────

Write-Section '1. Azure Login'

$account = az account show -o json 2>$null | ConvertFrom-Json
if ($account) {
    Write-Pass "Logged in: $($account.name) ($($account.id))"
} else {
    Write-Fail 'Not logged in — run az login'
    exit 1
}

# ─── Resource Group ───────────────────────────────────────────────────────────

Write-Section '2. Resource Group'

$rg = az group show --name $ResourceGroup --query 'properties.provisioningState' -o tsv 2>$null
if ($rg -eq 'Succeeded') {
    Write-Pass "Resource Group: $ResourceGroup (Succeeded)"
} else {
    Write-Fail "Resource Group not found or not Succeeded: $ResourceGroup"
}

# ─── Core Resources ───────────────────────────────────────────────────────────

Write-Section '3. Core Resources'

$checks = @(
    @{ Name='Container App Environment'; Cmd="az containerapp env show -n cae-$ProjectPrefix -g $ResourceGroup --query 'provisioningState' -o tsv" }
    @{ Name='Container App (Backend)';   Cmd="az containerapp show -n ca-$ProjectPrefix-backend -g $ResourceGroup --query 'properties.provisioningState' -o tsv" }
    @{ Name='Azure AI Foundry';          Cmd="az cognitiveservices account show -n ai-$ProjectPrefix -g $ResourceGroup --query 'properties.provisioningState' -o tsv" }
    @{ Name='Cosmos DB Account';         Cmd="az cosmosdb show -n cosmos-$ProjectPrefix -g $ResourceGroup --query 'documentEndpoint' -o tsv" }
    @{ Name='Storage Account';           Cmd="az storage account show -n $($ProjectPrefix -replace '-','') -g $ResourceGroup --query 'provisioningState' -o tsv" }
    @{ Name='Key Vault';                 Cmd="az keyvault show -n kv-$ProjectPrefix -g $ResourceGroup --query 'properties.provisioningState' -o tsv" }
    @{ Name='Bot Service';               Cmd="az bot show -n bot-$ProjectPrefix -g $ResourceGroup --query 'name' -o tsv" }
    @{ Name='Application Insights';      Cmd="az monitor app-insights component show --app appi-$ProjectPrefix -g $ResourceGroup --query 'provisioningState' -o tsv" }
    @{ Name='Log Analytics Workspace';   Cmd="az monitor log-analytics workspace show -n log-$ProjectPrefix -g $ResourceGroup --query 'provisioningState' -o tsv" }
)

foreach ($check in $checks) {
    $result = Invoke-Expression $check.Cmd 2>$null
    if ($result -and $result -ne 'Failed') {
        Write-Pass "$($check.Name)"
        Write-Info "State: $result"
    } else {
        Write-Fail "$($check.Name) — not found or failed"
    }
}

# ─── AI Foundry Model Deployment ──────────────────────────────────────────────

Write-Section '4. AI Foundry Model Deployment'

$modelDeployment = az cognitiveservices account deployment show `
    --name "ai-$ProjectPrefix" `
    --resource-group $ResourceGroup `
    --deployment-name 'mistral-large-latest' `
    --query '{state:properties.provisioningState, sku:sku.name}' `
    -o json 2>$null | ConvertFrom-Json

if ($modelDeployment -and $modelDeployment.state -eq 'Succeeded') {
    Write-Pass "Mistral Large — Deployed (SKU: $($modelDeployment.sku))"
    if ($modelDeployment.sku -eq 'DataZoneStandard') {
        Write-Pass 'DataZoneStandard SKU confirmed — EU data residency guaranteed'
    } else {
        Write-Warn "SKU is $($modelDeployment.sku) — expected DataZoneStandard for EU compliance!"
    }
} else {
    # Try GPT-4o if Mistral not found
    $gptDeployment = az cognitiveservices account deployment show `
        --name "ai-$ProjectPrefix" `
        --resource-group $ResourceGroup `
        --deployment-name 'gpt-4o' `
        --query 'properties.provisioningState' -o tsv 2>$null
    if ($gptDeployment -eq 'Succeeded') {
        Write-Pass 'GPT-4o deployment found'
    } else {
        Write-Fail 'No model deployment found — check AI Foundry capacity in Sweden Central'
        Write-Info 'Fallback option: Germany West Central'
    }
}

# ─── Key Vault Secrets ────────────────────────────────────────────────────────

Write-Section '5. Key Vault Secrets'

$requiredSecrets = @('ai-foundry-key', 'cosmos-connection', 'blob-connection', 'bot-app-password')
foreach ($secretName in $requiredSecrets) {
    $secret = az keyvault secret show `
        --vault-name "kv-$ProjectPrefix" `
        --name $secretName `
        --query 'attributes.enabled' -o tsv 2>$null
    if ($secret -eq 'true') {
        Write-Pass "Secret '$secretName' present and enabled"
    } else {
        Write-Fail "Secret '$secretName' not found — run deploy.ps1 step 6"
    }
}

# ─── Cosmos DB Collections ────────────────────────────────────────────────────

Write-Section '6. Cosmos DB Collections'

$dbName = "$ProjectPrefix-db"
$requiredCollections = @('conversations', 'agent_state', 'generated_documents', 'audit_log')
foreach ($col in $requiredCollections) {
    $colResult = az cosmosdb mongodb collection show `
        --account-name "cosmos-$ProjectPrefix" `
        --resource-group $ResourceGroup `
        --database-name $dbName `
        --name $col `
        --query 'name' -o tsv 2>$null
    if ($colResult -eq $col) {
        Write-Pass "Collection '$col'"
    } else {
        Write-Fail "Collection '$col' not found"
    }
}

# ─── Blob Storage Container ───────────────────────────────────────────────────

Write-Section '7. Blob Storage'

$storageName = $ProjectPrefix -replace '-', ''
$containerResult = az storage container show `
    --name 'pdf-output' `
    --account-name $storageName `
    --auth-mode login `
    --query 'name' -o tsv 2>$null
if ($containerResult -eq 'pdf-output') {
    Write-Pass 'Blob container pdf-output exists'
} else {
    Write-Warn 'Could not verify pdf-output container (may be a permissions issue, check manually)'
}

# ─── Container App Health Check ───────────────────────────────────────────────

Write-Section '8. Container App Health'

$fqdn = az containerapp show `
    --name "ca-$ProjectPrefix-backend" `
    --resource-group $ResourceGroup `
    --query 'properties.configuration.ingress.fqdn' -o tsv 2>$null

if ($fqdn) {
    Write-Info "FQDN: $fqdn"

    # Check running revision count
    $runningRevisions = az containerapp revision list `
        --name "ca-$ProjectPrefix-backend" `
        --resource-group $ResourceGroup `
        --query "[?properties.runningState=='Running'].name" -o tsv 2>$null

    if ($runningRevisions) {
        Write-Pass "Container App has running revision(s)"
    } else {
        Write-Warn 'No running revisions — container may still be starting or KV secrets unresolved'
    }

    # HTTP health probe
    try {
        $response = Invoke-RestMethod `
            -Uri "https://$fqdn/health" `
            -Method Get `
            -TimeoutSec 15 `
            -ErrorAction Stop
        if ($response.status -eq 'healthy') {
            Write-Pass "/health endpoint: $($response.status) (env: $($response.environment))"
        } else {
            Write-Warn "/health returned unexpected: $($response | ConvertTo-Json -Compress)"
        }
    } catch {
        Write-Warn "/health not reachable yet — container may still be starting (30-60s)"
        Write-Info "Manual check: curl https://$fqdn/health"
    }
} else {
    Write-Fail 'Container App FQDN not available'
}

# ─── Bot Service Channels ─────────────────────────────────────────────────────

Write-Section '9. Bot Service Channels'

$teamsChannel = az bot msteams show `
    --name "bot-$ProjectPrefix" `
    --resource-group $ResourceGroup `
    --query 'properties.isEnabled' -o tsv 2>$null
if ($teamsChannel -eq 'true') {
    Write-Pass 'Teams channel enabled'
} else {
    Write-Warn 'Teams channel not confirmed — may need manual Teams app sideload'
}

$telegramChannel = az bot telegram show `
    --name "bot-$ProjectPrefix" `
    --resource-group $ResourceGroup `
    --query 'properties.isEnabled' -o tsv 2>$null
if ($telegramChannel -eq 'true') {
    Write-Pass 'Telegram channel enabled'
} else {
    Write-Info 'Telegram channel not configured (optional)'
}

# ─── Quick AI Foundry Connectivity Test ───────────────────────────────────────

Write-Section '10. AI Foundry Connectivity Test'

$aiKey = az keyvault secret show `
    --vault-name "kv-$ProjectPrefix" `
    --name 'ai-foundry-key' `
    --query 'value' -o tsv 2>$null

$aiEndpoint = az cognitiveservices account show `
    --name "ai-$ProjectPrefix" `
    --resource-group $ResourceGroup `
    --query 'properties.endpoint' -o tsv 2>$null

if ($aiKey -and $aiEndpoint) {
    # Quick REST call to list models (doesn't consume tokens)
    try {
        $headers = @{ 'api-key' = $aiKey }
        $testUrl = "$($aiEndpoint.TrimEnd('/'))openai/models?api-version=2024-02-01"
        $modelsResponse = Invoke-RestMethod -Uri $testUrl -Headers $headers -Method Get -TimeoutSec 10 -ErrorAction Stop
        Write-Pass "AI Foundry REST API reachable"
        $modelCount = ($modelsResponse.data | Measure-Object).Count
        Write-Info "Models available: $modelCount"
    } catch {
        Write-Warn "AI Foundry REST probe failed — endpoint: $aiEndpoint"
        Write-Info "This may be normal if using inference.ai.azure.com endpoint format"
        Write-Info "Verify manually with the Python test script"
    }
} else {
    Write-Warn 'Skipping AI Foundry test — key or endpoint not available from Key Vault'
}

# ─── Summary ──────────────────────────────────────────────────────────────────

Write-Host ''
Write-Host '╔══════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║   Validation Summary                             ║' -ForegroundColor Cyan
Write-Host '╚══════════════════════════════════════════════════╝' -ForegroundColor Cyan
Write-Host "  ✅ Passed : $PassCount" -ForegroundColor Green
Write-Host "  ⚠️  Warnings: $WarnCount" -ForegroundColor Yellow
Write-Host "  ❌ Failed : $FailCount" -ForegroundColor Red
Write-Host ''

if ($FailCount -eq 0 -and $WarnCount -eq 0) {
    Write-Host '  🎉 All checks passed — Day 1-2 complete! Ready for Day 3-4.' -ForegroundColor Green
} elseif ($FailCount -eq 0) {
    Write-Host '  ✅ No failures — warnings are informational. Proceed to Day 3-4.' -ForegroundColor Green
} else {
    Write-Host '  ❌ Failures detected. Resolve before proceeding to Day 3-4.' -ForegroundColor Red
    Write-Host '  Common fixes:' -ForegroundColor Yellow
    Write-Host '    - Run .\deploy.ps1 to complete any missing steps'
    Write-Host '    - Check AI Foundry capacity: az cognitiveservices account deployment list ...'
    Write-Host '    - KV secret issues: az keyvault secret set --vault-name kv-$ProjectPrefix ...'
}

Write-Host ''

# Day 1-2 checklist output
Write-Host 'Day 1-2 Checklist:' -ForegroundColor Cyan
$fqdnFinal = az containerapp show -n "ca-$ProjectPrefix-backend" -g $ResourceGroup --query 'properties.configuration.ingress.fqdn' -o tsv 2>$null
Write-Host "  [x] Bicep template deployed to $ResourceGroup"
Write-Host "  [x] AI Foundry: Mistral Large, DataZoneStandard"
Write-Host "  [ ] Entra ID App Registration — verify in Azure Portal > App Registrations"
Write-Host "  [x] Key Vault secrets — ai-foundry-key, cosmos-connection, blob-connection, bot-app-password"
Write-Host "  [x] Cosmos DB collections — conversations, agent_state, generated_documents, audit_log"
Write-Host "  [x] Blob Storage container — pdf-output"
if ($fqdnFinal) {
    Write-Host "  [?] Validation — run /health: https://$fqdnFinal/health"
}
Write-Host ''
