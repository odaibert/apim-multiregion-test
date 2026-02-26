// ---------------------------------------------------------------------------
// Azure API Management — Premium SKU with multi-region
//
// Deploys APIM Premium in a primary region and adds a secondary region via
// additionalLocations.  Configures Application Insights logging and creates
// a Health API with region-based backend routing policy.
// ---------------------------------------------------------------------------

@description('Base name for the APIM instance')
param baseName string

@description('Primary region')
param primaryLocation string

@description('Secondary region')
param secondaryLocation string

@description('Publisher email for APIM')
param publisherEmail string

@description('Publisher name for APIM')
param publisherName string = 'APIM Multi-Region Demo'

@description('Application Insights instrumentation key')
param appInsightsInstrumentationKey string

@description('Application Insights resource ID')
param appInsightsId string

@description('Backend URL for primary region Container App')
param primaryBackendUrl string

@description('Backend URL for secondary region Container App')
param secondaryBackendUrl string

@description('Tags to apply to all resources')
param tags object = {}

// --- APIM Premium instance ---
resource apim 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: '${baseName}-apim'
  location: primaryLocation
  tags: tags
  sku: {
    name: 'Premium'
    capacity: 1
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    additionalLocations: [
      {
        location: secondaryLocation
        sku: {
          name: 'Premium'
          capacity: 1
        }
        disableGateway: false
      }
    ]
  }
}

// --- Application Insights logger ---
resource apimLogger 'Microsoft.ApiManagement/service/loggers@2023-09-01-preview' = {
  parent: apim
  name: 'app-insights-logger'
  properties: {
    loggerType: 'applicationInsights'
    resourceId: appInsightsId
    credentials: {
      instrumentationKey: appInsightsInstrumentationKey
    }
  }
}

// --- Diagnostics (send all API traffic to App Insights) ---
resource apimDiagnostics 'Microsoft.ApiManagement/service/diagnostics@2023-09-01-preview' = {
  parent: apim
  name: 'applicationinsights'
  properties: {
    loggerId: apimLogger.id
    alwaysLog: 'allErrors'
    sampling: {
      samplingType: 'fixed'
      percentage: 100
    }
  }
}

// --- Named values for backend URLs ---
resource namedValuePrimary 'Microsoft.ApiManagement/service/namedValues@2023-09-01-preview' = {
  parent: apim
  name: 'backend-url-primary'
  properties: {
    displayName: 'backend-url-primary'
    value: primaryBackendUrl
    secret: false
  }
}

resource namedValueSecondary 'Microsoft.ApiManagement/service/namedValues@2023-09-01-preview' = {
  parent: apim
  name: 'backend-url-secondary'
  properties: {
    displayName: 'backend-url-secondary'
    value: secondaryBackendUrl
    secret: false
  }
}

// --- Health API ---
resource healthApi 'Microsoft.ApiManagement/service/apis@2023-09-01-preview' = {
  parent: apim
  name: 'multiregion-health-api'
  properties: {
    displayName: 'Multi-Region Health API'
    description: 'Health/echo API for multi-region failover demo'
    path: 'multiregion-health-api'
    protocols: [
      'https'
    ]
    subscriptionRequired: false
    serviceUrl: primaryBackendUrl  // default backend; policy overrides per region
  }
}

// --- API Policy (region-based routing) ---
resource healthApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-09-01-preview' = {
  parent: healthApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '<policies>\r\n  <inbound>\r\n    <base />\r\n    <choose>\r\n      <when condition="@(context.Deployment.Region.Replace(&quot; &quot;, &quot;&quot;).ToLower() == &quot;${toLower(primaryLocation)}&quot;)">\r\n        <set-backend-service base-url="${primaryBackendUrl}" />\r\n      </when>\r\n      <when condition="@(context.Deployment.Region.Replace(&quot; &quot;, &quot;&quot;).ToLower() == &quot;${toLower(secondaryLocation)}&quot;)">\r\n        <set-backend-service base-url="${secondaryBackendUrl}" />\r\n      </when>\r\n      <otherwise>\r\n        <set-backend-service base-url="${primaryBackendUrl}" />\r\n      </otherwise>\r\n    </choose>\r\n  </inbound>\r\n  <backend>\r\n    <base />\r\n  </backend>\r\n  <outbound>\r\n    <base />\r\n  </outbound>\r\n  <on-error>\r\n    <base />\r\n  </on-error>\r\n</policies>'
  }
}

// --- Operations ---
resource opHealth 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: healthApi
  name: 'get-health'
  properties: {
    displayName: 'Health Check'
    method: 'GET'
    urlTemplate: '/health'
    description: 'Returns region identity and health status'
  }
}

resource opEcho 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: healthApi
  name: 'get-echo'
  properties: {
    displayName: 'Echo'
    method: 'GET'
    urlTemplate: '/echo'
    description: 'Returns request metadata and region info'
  }
}

resource opRoot 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: healthApi
  name: 'get-root'
  properties: {
    displayName: 'Service Info'
    method: 'GET'
    urlTemplate: '/'
    description: 'Returns service information'
  }
}

resource opStatus 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: healthApi
  name: 'get-status'
  properties: {
    displayName: 'Status'
    method: 'GET'
    urlTemplate: '/status'
    description: 'Simple status probe'
  }
}

// --- Outputs ---
output apimName string = apim.name
output apimGatewayUrl string = apim.properties.gatewayUrl
output apimPrimaryRegionalUrl string = 'https://${apim.name}-${replace(toLower(primaryLocation), ' ', '')}-01.regional.azure-api.net'
output apimSecondaryRegionalUrl string = 'https://${apim.name}-${replace(toLower(secondaryLocation), ' ', '')}-01.regional.azure-api.net'
