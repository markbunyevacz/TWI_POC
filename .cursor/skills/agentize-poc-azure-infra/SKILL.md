---
name: agentize-poc-azure-infra
description: Azure infrastructure guide for the agentize.eu PoC using Bicep. Covers resource group layout, VNET, Container App, AI Foundry (Data Zone Standard), Cosmos DB (MongoDB API), Blob Storage, Key Vault, App Insights, Bot Service, and Entra ID setup. Use when writing or modifying Bicep templates, deploying Azure resources, or troubleshooting infrastructure issues.
---

# Azure Infrastructure — agentize.eu PoC

## Critical Constraints

- **Region: Sweden Central ONLY** — only region with contractual EU data residency guarantee
- **AI Foundry SKU: `DataZoneStandard`** — NOT Global Standard (required for EU AI Act compliance)
- All secrets via **Key Vault references** in Container App — never hardcoded

## Resource Group Layout

```
rg-agentize-poc-swedencentral
├── vnet-agentize-poc (10.0.0.0/16)
│   ├── snet-container-apps (/23, min 256 IPs — Container Apps requirement)
│   └── snet-private-endpoints (/24)
├── cae-agentize-poc          Container App Environment (VNET-integrated, internal)
│   └── ca-agentize-poc-backend  (FastAPI, port 8000, external ingress for Bot Service)
├── ai-agentize-poc           Azure AI Foundry (AIServices kind)
│   └── mistral-large-latest  Model deployment (DataZoneStandard, 10K TPM)
├── cosmos-agentize-poc       Cosmos DB (MongoDB API, serverless)
│   └── agentize-poc-db
│       ├── conversations
│       ├── agent_state       (LangGraph checkpoints)
│       ├── audit_log
│       └── generated_documents
├── stagentizepoc             Storage Account (Standard_LRS)
│   └── pdf-output            Blob container (no public access)
├── kv-agentize-poc           Key Vault (RBAC authorization)
├── ai-agentize-poc-insights  Application Insights (web, 30d retention)
└── bot-agentize-poc          Azure Bot Service (global, S1)
    ├── MsTeamsChannel
    └── TelegramChannel (conditional: only if token provided)
```

## Bicep Parameters

```bicep
param location string = 'swedencentral'   // NEVER change for PoC
param projectPrefix string = 'agentize-poc'
param aiModel string = 'mistral-large-latest'   // allowed: 'gpt-4o'
param minReplicas int = 1                 // 1 = no cold start (~$10/mo)
param cosmosThroughputMode string = 'serverless'
param botAppId string                     // from Entra ID App Registration
@secure() param botAppPassword string
@secure() param telegramBotToken string = ''
```

## Key Bicep Patterns

### VNET + Container App Environment
```bicep
// Subnet: min /23 for Container Apps
addressPrefix: '10.0.0.0/23'
delegations: [{ name: 'Microsoft.App.environments', properties: { serviceName: 'Microsoft.App/environments' } }]

// Environment: internal=true (only VNET-reachable)
vnetConfiguration: { infrastructureSubnetId: subnet.id, internal: true }
```

### Container App Secrets (Key Vault references)
```bicep
secrets: [
  { name: 'ai-foundry-key', keyVaultUrl: '${kv.properties.vaultUri}secrets/ai-foundry-key' }
  { name: 'cosmos-connection', keyVaultUrl: '${kv.properties.vaultUri}secrets/cosmos-connection' }
  { name: 'bot-app-password', keyVaultUrl: '${kv.properties.vaultUri}secrets/bot-app-password' }
  { name: 'blob-connection', keyVaultUrl: '${kv.properties.vaultUri}secrets/blob-connection' }
]
```

### AI Foundry — Data Zone Standard (critical)
```bicep
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: { customSubDomainName: 'ai-${projectPrefix}', publicNetworkAccess: 'Enabled' }
}

resource aiDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  sku: { name: 'DataZoneStandard', capacity: 10 }  // NOT 'GlobalStandard'
  properties: { model: { format: 'MistralAI', name: aiModel, version: 'latest' } }
}
```

### Cosmos DB (MongoDB API, serverless)
```bicep
kind: 'MongoDB'
capabilities: [{ name: 'EnableServerless' }, { name: 'EnableMongo' }]
```

### Bot Service
```bicep
// location MUST be 'global' for Bot Service
location: 'global'
endpoint: 'https://${backendApp.properties.configuration.ingress.fqdn}/api/messages'
msaAppType: 'SingleTenant'
msaAppTenantId: subscription().tenantId

// Telegram channel — conditional on token
resource telegramChannel ... = if (telegramBotToken != '') { ... }
```

## Deployment

```bash
# infra/deploy.sh
az deployment group create \
  --resource-group rg-agentize-poc-swedencentral \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.json \
  --parameters botAppId=<id> botAppPassword=<secret>
```

## Day 1-2 Validation Checklist

- [ ] All resources deployed without errors
- [ ] AI Foundry: `POST .../chat/completions` returns response
- [ ] Cosmos DB: MongoDB connection string works, collections exist
- [ ] Key Vault: secrets accessible via managed identity
- [ ] Bot Service: messaging endpoint configured
- [ ] Container App: `/health` returns `{"status": "healthy"}`

## PoC vs MVP Security Notes

PoC uses `publicNetworkAccess: 'Enabled'` on all resources.
For MVP: add Private Endpoints for Cosmos DB, Blob Storage, Key Vault, AI Foundry.
