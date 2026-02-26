// ---------------------------------------------------------------------------
// Container App — Health/Echo API backend
//
// Deploys a Container Apps Environment + Container App in a given region.
// The REGION env var lets the API self-identify its location.
// ---------------------------------------------------------------------------

@description('Base name for resources')
param baseName string

@description('Azure region for this Container App')
param location string

@description('Region label set as the REGION environment variable (e.g. eastus)')
param regionLabel string

@description('Container image to deploy')
param containerImage string = 'python:3.12-slim'

@description('Log Analytics workspace ID for the environment')
param logAnalyticsId string

@description('Tags to apply to all resources')
param tags object = {}

// --- Container Apps Environment ---
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${baseName}-env-${regionLabel}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsId, '2023-09-01').customerId
        sharedKey: listKeys(logAnalyticsId, '2023-09-01').primarySharedKey
      }
    }
  }
}

// --- Container App ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-health-${regionLabel}'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'health-api'
          image: containerImage
          command: [
            'python3'
            '-c'
            'import http.server, json, os, datetime\nREGION = os.getenv("REGION", "unknown")\nclass H(http.server.BaseHTTPRequestHandler):\n  def do_GET(self):\n    self.send_response(200)\n    self.send_header("Content-Type", "application/json")\n    self.end_headers()\n    self.wfile.write(json.dumps({"status": "healthy", "region": REGION, "path": self.path, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}).encode())\n  def log_message(self, f, *a): pass\nhttp.server.HTTPServer(("0.0.0.0", 8000), H).serve_forever()\n'
          ]
          env: [
            {
              name: 'REGION'
              value: regionLabel
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// --- Outputs ---
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerAppName string = containerApp.name
output containerAppEnvName string = containerAppEnv.name
