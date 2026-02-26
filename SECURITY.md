# Security

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainer directly or use [GitHub Security Advisories](../../security/advisories)
3. Include a description of the vulnerability and steps to reproduce

## Security Considerations

This is an **educational demo** repository. When using it:

- **Never commit secrets** — The `.gitignore` excludes `.env`, `*.pem`, and `*.key` files
- **APIM subscription keys** are not used in this demo (`subscriptionRequired: false`)
- **Clean up resources** after running the lab to avoid unnecessary costs
- **Use least-privilege access** — The lab requires Contributor + RBAC Administrator roles
- **Review Bicep templates** before deploying to understand what resources are created

## Azure Security Best Practices

For production APIM deployments (beyond this demo):

- Enable subscription keys or OAuth 2.0 authentication
- Use Azure Private Link for backend APIs
- Enable Azure DDoS Protection
- Configure rate limiting and throttling policies
- Use managed identities instead of connection strings
- Enable diagnostic logging to Azure Monitor
