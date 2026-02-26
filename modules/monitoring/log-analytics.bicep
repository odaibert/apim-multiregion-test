// ---------------------------------------------------------------------------
// Log Analytics workspace + Application Insights
// ---------------------------------------------------------------------------

@description('Base name for monitoring resources')
param baseName string

@description('Azure region for deployment')
param location string = resourceGroup().location

@description('Tags to apply to all resources')
param tags object = {}

// --- Log Analytics Workspace ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${baseName}-law'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// --- Application Insights ---
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-ai'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// --- Outputs ---
output logAnalyticsId string = logAnalytics.id
output logAnalyticsName string = logAnalytics.name
output appInsightsId string = appInsights.id
output appInsightsName string = appInsights.name
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString
