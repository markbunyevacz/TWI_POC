// main.bicep — agentize.eu PoC Infrastructure
// Region: Sweden Central | EU Data Zone Standard
// Deploy: az deployment group create -g <rg> -f main.bicep -p @parameters.json

targetScope = 'resourceGroup'

// ─── Parameters ───────────────────────────────────────────────────────────────

@description('Azure region — Sweden Central for EU Data Zone Standard guarantee')
param location string = 'swedencentral'

@description('Project prefix for all resource names')
param projectPrefix string = 'agentize-poc'

@description('AI Foundry model — DataZoneStandard deployment, NOT GlobalStandard')
@allowed(['mistral-large-latest', 'gpt-4o'])
param aiModel string = 'mistral-large-latest'

@description('Container App min replicas (1 = no cold start, ~$10/mo extra)')
@minValue(0)
@maxValue(5)
param minReplicas int = 1

@description('Cosmos DB throughput mode (serverless for PoC)')
@allowed(['serverless', 'provisioned'])
param cosmosThroughputMode string = 'serverless'

@description('Bot Entra ID App Registration client ID')
param botAppId string

@description('Bot Entra ID App Registration client secret')
@secure()
param botAppPassword string

@description('Telegram Bot Token from @BotFather — empty = skip channel')
@secure()
param telegramBotToken string = ''

@description('Container image reference — override for specific tag post-build')
param containerImage string = 'ghcr.io/agentize-eu/poc-backend:latest'

// ─── Variables ────────────────────────────────────────────────────────────────

// Storage account names cannot contain hyphens
var storageAccountName = replace(replace('st${projectPrefix}', '-', ''), '_', '')

// Built-in role: Key Vault Secrets User
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// Determine AI model format for AI Foundry deployment
var aiModelFormat = contains(aiModel, 'gpt') ? 'OpenAI' : 'MistralAI'

// ─── Log Analytics Workspace ──────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${projectPrefix}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ─── Network Security Group ───────────────────────────────────────────────────

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'nsg-${projectPrefix}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPSInbound'
        properties: {
          priority: 100
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'AllowBotServiceInbound'
        properties: {
          priority: 110
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: 'AzureBotService'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          protocol: '*'
          access: 'Deny'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

// ─── Virtual Network ──────────────────────────────────────────────────────────

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: 'vnet-${projectPrefix}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'snet-container-apps'
        // Minimum /23 required for Container Apps Environment (256 IPs)
        properties: {
          addressPrefix: '10.0.0.0/23'
          networkSecurityGroup: { id: nsg.id }
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.0.2.0/24'
          networkSecurityGroup: { id: nsg.id }
        }
      }
    ]
  }
}

// ─── Key Vault ────────────────────────────────────────────────────────────────

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${projectPrefix}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled' // PoC: open. MVP: Disabled + Private Endpoint
  }
}

// ─── Application Insights ─────────────────────────────────────────────────────

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${projectPrefix}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 30
    DisableIpMasking: false // PII masking: keep IP masking enabled (false = masked)
  }
}

// ─── Container App Environment ────────────────────────────────────────────────

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${projectPrefix}'
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: vnet.properties.subnets[0].id
      // internal: false → public IP required so Bot Service can call /api/messages
      // MVP hardening: flip to true + Azure Front Door / Private Endpoint
      internal: false
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ─── Azure AI Foundry ─────────────────────────────────────────────────────────
// CRITICAL: kind=AIServices, DataZoneStandard SKU = contractual EU data residency
// Sweden Central is the primary EU region with this guarantee

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: 'ai-${projectPrefix}'
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: 'ai-${projectPrefix}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// DataZoneStandard = EU data residency. NOT GlobalStandard.
resource aiModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: aiFoundry
  name: aiModel
  sku: {
    name: 'DataZoneStandard'
    capacity: 10 // 10K TPM — sufficient for PoC demo load
  }
  properties: {
    model: {
      format: aiModelFormat
      name: aiModel
      version: 'latest'
    }
  }
}

// ─── Cosmos DB (MongoDB API) ──────────────────────────────────────────────────

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'cosmos-${projectPrefix}'
  location: location
  kind: 'MongoDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      { locationName: location, failoverPriority: 0, isZoneRedundant: false }
    ]
    capabilities: cosmosThroughputMode == 'serverless'
      ? [{ name: 'EnableServerless' }, { name: 'EnableMongo' }]
      : [{ name: 'EnableMongo' }]
    publicNetworkAccess: 'Enabled'
    apiProperties: { serverVersion: '7.0' }
    // Serverless mode does not support zone redundancy — acceptable for PoC
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: '${projectPrefix}-db'
  properties: {
    resource: { id: '${projectPrefix}-db' }
  }
}

// conversations: active chat sessions, 90-day TTL
resource conversationsCol 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases/collections@2023-11-15' = {
  parent: cosmosDb
  name: 'conversations'
  properties: {
    resource: {
      id: 'conversations'
      indexes: [
        { key: { keys: ['_id'] } }
        { key: { keys: ['conversation_id'] }, options: { unique: true } }
        { key: { keys: ['tenant_id', 'user_id'] } }
        { key: { keys: ['last_activity'] }, options: { expireAfterSeconds: 7776000 } }
      ]
    }
    options: {}
  }
}

// agent_state: LangGraph checkpoints — managed by LangGraph checkpointer
resource agentStateCol 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases/collections@2023-11-15' = {
  parent: cosmosDb
  name: 'agent_state'
  properties: {
    resource: {
      id: 'agent_state'
      indexes: [
        { key: { keys: ['_id'] } }
        { key: { keys: ['thread_id'] } }
        { key: { keys: ['checkpoint_id'] } }
        { key: { keys: ['created_at'] } }
      ]
    }
    options: {}
  }
}

// generated_documents: approved TWI docs with PDF references
resource generatedDocsCol 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases/collections@2023-11-15' = {
  parent: cosmosDb
  name: 'generated_documents'
  properties: {
    resource: {
      id: 'generated_documents'
      indexes: [
        { key: { keys: ['_id'] } }
        { key: { keys: ['tenant_id', 'created_at'] } }
        { key: { keys: ['conversation_id'] } }
      ]
    }
    options: {}
  }
}

// audit_log: immutable event trail (EU AI Act compliance)
resource auditLogCol 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases/collections@2023-11-15' = {
  parent: cosmosDb
  name: 'audit_log'
  properties: {
    resource: {
      id: 'audit_log'
      indexes: [
        { key: { keys: ['_id'] } }
        { key: { keys: ['tenant_id', 'created_at'] } }
        { key: { keys: ['event_type'] } }
      ]
    }
    options: {}
  }
}

// ─── Storage Account ──────────────────────────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Enabled'
    allowBlobPublicAccess: false // PDF blobs served via SAS tokens only
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

resource pdfOutputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'pdf-output'
  properties: { publicAccess: 'None' }
}

// ─── Container App (FastAPI + LangGraph Backend) ──────────────────────────────
// System-assigned managed identity → Key Vault Secrets User (role assigned below)
// Secrets use Key Vault references — resolved at container start, not deploy time
// Container may fail to start until secrets are populated by deploy.ps1 step 6

resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-${projectPrefix}-backend'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'ai-foundry-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/ai-foundry-key'
          identity: 'system'
        }
        {
          name: 'cosmos-connection'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/cosmos-connection'
          identity: 'system'
        }
        {
          name: 'bot-app-password'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/bot-app-password'
          identity: 'system'
        }
        {
          name: 'blob-connection'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/blob-connection'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: containerImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'AI_FOUNDRY_ENDPOINT', value: '${aiFoundry.properties.endpoint}' }
            { name: 'AI_FOUNDRY_KEY', secretRef: 'ai-foundry-key' }
            { name: 'COSMOS_CONNECTION', secretRef: 'cosmos-connection' }
            { name: 'COSMOS_DATABASE', value: '${projectPrefix}-db' }
            { name: 'BOT_APP_ID', value: botAppId }
            { name: 'BOT_APP_PASSWORD', secretRef: 'bot-app-password' }
            { name: 'BLOB_CONNECTION', secretRef: 'blob-connection' }
            { name: 'BLOB_CONTAINER', value: 'pdf-output' }
            { name: 'AI_MODEL', value: aiModel }
            { name: 'ENVIRONMENT', value: 'poc' }
            { name: 'LOG_LEVEL', value: 'INFO' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 15
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: { metadata: { concurrentRequests: '20' } }
          }
        ]
      }
    }
  }
}

// ─── RBAC: Container App → Key Vault Secrets User ────────────────────────────
// Grants the Container App's system identity read access to KV secrets
// Implicit dependency on backendApp via principalId reference

resource kvSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, backendApp.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ─── Azure Bot Service ────────────────────────────────────────────────────────

resource botService 'Microsoft.BotService/botServices@2022-09-15' = {
  name: 'bot-${projectPrefix}'
  location: 'global' // Bot Service is always a global resource
  kind: 'azurebot'
  sku: { name: 'S1' }
  properties: {
    displayName: 'agentize.eu PoC Bot'
    description: 'Enterprise AI Platform PoC — TWI document generation'
    endpoint: 'https://${backendApp.properties.configuration.ingress.fqdn}/api/messages'
    msaAppId: botAppId
    msaAppType: 'SingleTenant'
    msaAppTenantId: subscription().tenantId
    isStreamingSupported: false
  }
}

resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: botService
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    channelName: 'MsTeamsChannel'
    properties: { isEnabled: true }
  }
}

// Telegram channel is optional — skip if token not provided
resource telegramChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = if (!empty(telegramBotToken)) {
  parent: botService
  name: 'TelegramChannel'
  location: 'global'
  properties: {
    channelName: 'TelegramChannel'
    properties: {
      accessToken: telegramBotToken
      isEnabled: true
    }
  }
}

// ─── Outputs ──────────────────────────────────────────────────────────────────

@description('Backend Container App FQDN — used as Bot messaging endpoint base')
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn

@description('Bot messaging endpoint — register this in Azure Bot Service + Teams manifest')
output botEndpoint string = 'https://${backendApp.properties.configuration.ingress.fqdn}/api/messages'

@description('AI Foundry Cognitive Services endpoint')
output aiFoundryEndpoint string = aiFoundry.properties.endpoint

@description('AI Foundry inference endpoint for azure-ai-inference SDK')
output aiFoundryInferenceEndpoint string = 'https://${aiFoundry.name}.services.ai.azure.com/models'

@description('Cosmos DB account name — needed to retrieve connection strings')
output cosmosAccountName string = cosmosAccount.name

@description('Storage account name — needed to retrieve connection strings')
output storageAccountName string = storageAccount.name

@description('Key Vault URI')
output keyVaultUri string = keyVault.properties.vaultUri

@description('Key Vault name')
output keyVaultName string = keyVault.name

@description('Application Insights connection string — also in KV for reference')
output appInsightsConnectionString string = appInsights.properties.ConnectionString

@description('Container App system-assigned managed identity principal ID')
output containerAppPrincipalId string = backendApp.identity.principalId

@description('Teams App manifest validDomains entry')
output backendHostname string = backendApp.properties.configuration.ingress.fqdn
