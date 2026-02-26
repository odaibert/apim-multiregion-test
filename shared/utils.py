"""
Shared utilities for the APIM multi-region failover demo.

Used by both the Jupyter notebook and the Streamlit dashboard.
"""

import json
import subprocess
import time
from datetime import datetime, timezone

import requests


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------

def generate_resource_name(prefix: str, suffix: str = "") -> str:
    """Generate a unique resource name with a timestamp-based suffix."""
    if not suffix:
        suffix = datetime.now(timezone.utc).strftime("%m%d%H%M")
    return f"{prefix}-{suffix}".lower()


# ---------------------------------------------------------------------------
# Azure CLI wrapper
# ---------------------------------------------------------------------------

def run_az_cli(command: str, parse_json: bool = True):
    """Run an Azure CLI command and return the parsed output.

    Args:
        command: The full az CLI command string (without the leading 'az').
        parse_json: If True, parse stdout as JSON. Otherwise return raw text.

    Returns:
        Parsed JSON object or raw string output.

    Raises:
        RuntimeError: If the command exits with a non-zero status.
    """
    full_cmd = f"az {command}"
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"az CLI error (exit {result.returncode}):\n"
            f"  Command: {full_cmd}\n"
            f"  Stderr:  {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        return None
    if parse_json:
        return json.loads(result.stdout)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Region health checks
# ---------------------------------------------------------------------------

def check_region_health(
    regional_url: str,
    path: str = "/health",
    timeout: float = 10.0,
) -> dict:
    """Hit a regional APIM gateway endpoint and return health + latency.

    Args:
        regional_url: The regional gateway base URL
            (e.g. https://myapim-eastus-01.regional.azure-api.net).
        path: API path to probe (default /health).
        timeout: Request timeout in seconds.

    Returns:
        dict with keys: status, status_code, latency_ms, region, body, error.
    """
    url = f"{regional_url.rstrip('/')}/multiregion-health-api{path}"
    start = time.perf_counter()
    try:
        resp = requests.get(url, timeout=timeout)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        return {
            "status": "healthy" if resp.status_code == 200 else "unhealthy",
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "region": body.get("region", "unknown") if isinstance(body, dict) else "unknown",
            "body": body,
            "error": None,
        }
    except requests.exceptions.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "unreachable",
            "status_code": None,
            "latency_ms": latency_ms,
            "region": "unknown",
            "body": None,
            "error": str(exc),
        }


def check_default_gateway(
    gateway_url: str,
    path: str = "/health",
    timeout: float = 10.0,
) -> dict:
    """Hit the default (load-balanced) APIM gateway and return response info."""
    url = f"{gateway_url.rstrip('/')}/multiregion-health-api{path}"
    start = time.perf_counter()
    try:
        resp = requests.get(url, timeout=timeout)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        return {
            "status": "healthy" if resp.status_code == 200 else "unhealthy",
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "region": body.get("region", "unknown") if isinstance(body, dict) else "unknown",
            "body": body,
            "error": None,
        }
    except requests.exceptions.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "unreachable",
            "status_code": None,
            "latency_ms": latency_ms,
            "region": "unknown",
            "body": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Gateway management
# ---------------------------------------------------------------------------

def toggle_gateway(
    apim_name: str,
    resource_group: str,
    location: str,
    disable: bool,
    is_primary: bool = False,
) -> str:
    """Enable or disable an APIM regional gateway.

    For the **secondary** (additionalLocations) region, uses:
        az apim update --set additionalLocations[0].disableGateway={true|false}

    For the **primary** region, uses the REST API directly because the az CLI
    does not expose disableGateway on the primary location through --set.

    Args:
        apim_name: Name of the APIM instance.
        resource_group: Resource group name.
        location: Azure region display name (e.g. "West US 2").
        disable: True to disable, False to enable.
        is_primary: Whether this is the primary region.

    Returns:
        Status message string.
    """
    action = "Disabling" if disable else "Enabling"
    flag = "true" if disable else "false"

    if not is_primary:
        # Secondary region — use az apim update (with retry for ServiceLocked)
        cmd = (
            f'apim update --name {apim_name} '
            f'--resource-group {resource_group} '
            f'--set "additionalLocations[0].disableGateway={flag}"'
        )
        for attempt in range(5):
            try:
                run_az_cli(cmd, parse_json=False)
                return f"{action} gateway in {location} — done."
            except RuntimeError as e:
                if "ServiceLocked" in str(e) or "transitioning" in str(e):
                    wait = 30 * (attempt + 1)
                    print(f"   APIM is transitioning, retrying in {wait}s (attempt {attempt+2}/5)...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Failed to {action.lower()} {location} after 5 retries (service still locked).")
    else:
        # Primary region — use REST API
        # Get the current config first
        apim_config = run_az_cli(
            f"apim show --name {apim_name} --resource-group {resource_group}"
        )
        # Update disableGateway on primary
        apim_config["disableGateway"] = disable

        # Get access token and subscription ID
        token = run_az_cli("account get-access-token --query accessToken -o tsv", parse_json=False)
        sub_id = run_az_cli("account show --query id -o tsv", parse_json=False)

        url = (
            f"https://management.azure.com/subscriptions/{sub_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.ApiManagement/service/{apim_name}"
            f"?api-version=2023-09-01-preview"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "location": apim_config["location"],
            "sku": apim_config["sku"],
            "properties": {
                "publisherEmail": apim_config.get("publisherEmail", ""),
                "publisherName": apim_config.get("publisherName", ""),
                "disableGateway": disable,
                "additionalLocations": apim_config.get("additionalLocations", []),
            },
        }
        resp = requests.put(url, headers=headers, json=payload, timeout=60)
        if resp.status_code in (200, 201, 202):
            return f"{action} primary gateway in {location} — accepted (may take a few minutes)."
        else:
            raise RuntimeError(
                f"REST API error ({resp.status_code}): {resp.text}"
            )


def send_traffic_burst(
    gateway_url: str,
    num_requests: int = 20,
    path: str = "/echo",
) -> list[dict]:
    """Send multiple requests to the default gateway and record which region served each.

    Returns:
        List of dicts with keys: request_num, region, latency_ms, status_code.
    """
    results = []
    for i in range(num_requests):
        url = f"{gateway_url.rstrip('/')}/multiregion-health-api{path}"
        start = time.perf_counter()
        try:
            resp = requests.get(url, timeout=15)
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            body = resp.json() if resp.ok else {}
            results.append({
                "request_num": i + 1,
                "region": body.get("region", "unknown"),
                "latency_ms": latency_ms,
                "status_code": resp.status_code,
            })
        except requests.exceptions.RequestException:
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            results.append({
                "request_num": i + 1,
                "region": "error",
                "latency_ms": latency_ms,
                "status_code": None,
            })
    return results
