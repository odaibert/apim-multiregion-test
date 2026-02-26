# Multi-Region Failover Lab

> **Prove your APIM Premium gateway survives a region failure — with real Azure infrastructure, not slides.**

## What This Lab Does

This self-contained Jupyter notebook deploys an Azure API Management **Premium** instance across **two regions** (East US + West US 2), with a lightweight health/echo API backend in each region. You then run failover scenarios using the official `disableGateway` mechanism and observe traffic shift in real time.

## Architecture

![Architecture Diagram](../docs/images/architecture.jpeg)

## What Gets Deployed

| Resource | Region | Purpose |
|----------|--------|---------|
| APIM Premium (1 unit) | East US | Primary API gateway |
| APIM Additional Location (1 unit) | West US 2 | Secondary API gateway |
| Container App + Environment | East US | Health API backend (`REGION=eastus`) |
| Container App + Environment | West US 2 | Health API backend (`REGION=westus2`) |
| Log Analytics + App Insights | East US | Observability |

## Notebook Cells

| Cell | Name | What It Does |
|------|------|-------------|
| 0️⃣ | Initialize | Set variables, generate unique resource names |
| 1️⃣ | Verify Azure CLI | Confirm `az login` and subscription |
| 2️⃣ | Deploy Infrastructure | Provision all resources via Bicep (~30-45 min for APIM Premium) |
| 3️⃣ | Retrieve Outputs | Get gateway URLs and Container App FQDNs |
| 4️⃣ | Test Default Gateway | Send requests to the load-balanced gateway |
| 5️⃣ | Test Regional Endpoints | Hit each regional gateway directly |
| 6️⃣ | Region Health Summary | Check health on both regional URLs |
| 7️⃣ | Simulate Failure — Disable Secondary | Disable West US 2 gateway, verify all traffic goes to East US |
| 8️⃣ | Simulate Failure — Disable Primary | Re-enable secondary, disable East US, verify failover to West US 2 |
| 9️⃣ | Restore All Gateways | Re-enable both regions, verify normal routing |
| 🔟 | Launch Dashboard | Start the Streamlit dashboard for visual monitoring |
| 🗑️ | Clean Up | Delete the resource group and all resources |

## Prerequisites

- Python 3.12+
- VS Code with Jupyter extension
- Azure Subscription with Contributor + RBAC Administrator roles
- Azure CLI installed and signed in (`az login`)

## Getting Started

1. Open `multi-region-failover.ipynb` in VS Code
2. Click **Run All** or step through each cell
3. The notebook guides you through deployment, testing, and cleanup

> ⚠️ **Cost warning:** APIM Premium costs ~$2.80/hour per unit. This lab deploys 2 units total. Run the cleanup cell when done.

## Failure Simulation Details

The lab uses the **`disableGateway`** property — the official Azure mechanism for DR drills:

```bash
# Disable secondary region gateway
az apim update --name <apim-name> --resource-group <rg-name> \
  --set "additionalLocations[0].disableGateway=true"

# Re-enable
az apim update --name <apim-name> --resource-group <rg-name> \
  --set "additionalLocations[0].disableGateway=false"
```

When a gateway is disabled:
- The regional endpoint returns 404
- The default gateway automatically routes around the disabled region
- No data is lost — the remaining region(s) continue serving requests

## References

- 📖 [Deploy APIM to multiple regions](https://learn.microsoft.com/azure/api-management/api-management-howto-deploy-multi-region)
- 📖 [Disable routing to a regional gateway](https://learn.microsoft.com/azure/api-management/api-management-howto-deploy-multi-region#disable-routing-to-a-regional-gateway)
- 📖 [Reliability in API Management](https://learn.microsoft.com/azure/reliability/reliability-api-management)
