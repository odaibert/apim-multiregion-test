// ---------------------------------------------------------------------------
// Main orchestrator — APIM Multi-Region Failover Lab
//
// Deploys: Monitoring → Container Apps (2 regions) → APIM Premium (multi-region)
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

@description('Base name prefix for all resources')
param baseName string

@description('Primary Azure region')
param primaryLocation string = 'eastus'

@description('Secondary Azure region')
param secondaryLocation string = 'westus2'

@description('Publisher email for APIM')
param publisherEmail string

@description('Container image for the health API')
param containerImage string = 'python:3.12-slim'

@description('Tags applied to every resource')
param tags object = {
  project: 'apim-multiregion-test'
  purpose: 'demo'
}

// ---------------------------------------------------------------------------
// 1. Monitoring (Log Analytics + Application Insights)
// ---------------------------------------------------------------------------
module monitoring '../../modules/monitoring/log-analytics.bicep' = {
  name: 'monitoring-deployment'
  params: {
    baseName: baseName
    location: primaryLocation
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// 2a. Container App — Primary region (East US)
// ---------------------------------------------------------------------------
module containerAppPrimary '../../modules/container-app/health-api.bicep' = {
  name: 'container-app-primary'
  params: {
    baseName: baseName
    location: primaryLocation
    regionLabel: 'eastus'
    containerImage: containerImage
    logAnalyticsId: monitoring.outputs.logAnalyticsId
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// 2b. Container App — Secondary region (West US 2)
// ---------------------------------------------------------------------------
module containerAppSecondary '../../modules/container-app/health-api.bicep' = {
  name: 'container-app-secondary'
  params: {
    baseName: baseName
    location: secondaryLocation
    regionLabel: 'westus2'
    containerImage: containerImage
    logAnalyticsId: monitoring.outputs.logAnalyticsId
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// 3. Azure API Management Premium (multi-region)
// ---------------------------------------------------------------------------
module apim '../../modules/apim/apim-premium.bicep' = {
  name: 'apim-deployment'
  params: {
    baseName: baseName
    primaryLocation: primaryLocation
    secondaryLocation: secondaryLocation
    publisherEmail: publisherEmail
    appInsightsInstrumentationKey: monitoring.outputs.appInsightsInstrumentationKey
    appInsightsId: monitoring.outputs.appInsightsId
    primaryBackendUrl: containerAppPrimary.outputs.containerAppUrl
    secondaryBackendUrl: containerAppSecondary.outputs.containerAppUrl
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

// APIM
output apimName string = apim.outputs.apimName
output apimGatewayUrl string = apim.outputs.apimGatewayUrl
output apimPrimaryRegionalUrl string = apim.outputs.apimPrimaryRegionalUrl
output apimSecondaryRegionalUrl string = apim.outputs.apimSecondaryRegionalUrl

// Container Apps
output primaryContainerAppUrl string = containerAppPrimary.outputs.containerAppUrl
output secondaryContainerAppUrl string = containerAppSecondary.outputs.containerAppUrl
output primaryContainerAppName string = containerAppPrimary.outputs.containerAppName
output secondaryContainerAppName string = containerAppSecondary.outputs.containerAppName

// Monitoring
output logAnalyticsName string = monitoring.outputs.logAnalyticsName
output appInsightsName string = monitoring.outputs.appInsightsName
