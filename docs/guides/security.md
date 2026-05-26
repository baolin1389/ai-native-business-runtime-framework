# Security Guide

## Overview

This guide covers security best practices for using the AI Business Runtime Framework in production environments.

## API Key Management

### Environment Variables

**Never** store API keys in configuration files or source code.

```bash
# Set API keys as environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Or use a secrets manager
export OPENAI_API_KEY=$(vault read -field=key secret/openai)
```

### Using Secrets Managers

#### AWS Secrets Manager

```python
import boto3

def get_secret(secret_name):
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]
```

#### HashiCorp Vault

```bash
export OPENAI_API_KEY=$(vault kv get -field=key secret/openai)
```

#### Environment File (Development Only)

For local development, use a `.env` file (never commit this):

```bash
# .env (add to .gitignore)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Load with:
```bash
set -a && source .env && set +a
```

## Input Validation

### Sanitizing User Input

All user-provided data should be validated before use:

```python
from runtime.validators import InputValidator

validator = InputValidator()

# Validate string input
clean_prompt = validator.sanitize_string(user_prompt, max_length=10000)

# Validate JSON context
clean_context = validator.validate_json(user_context, allowed_keys=["key1", "key2"])

# Validate numeric values
timeout = validator.validate_number(user_timeout, min=1, max=3600)
```

### Preventing Prompt Injection

```python
def sanitize_prompt(prompt):
    """Remove potential prompt injection patterns."""
    dangerous_patterns = [
        "ignore previous instructions",
        "ignore system prompt",
        "disregard all previous",
        "# Instructions:",
        "You are now",
    ]
    
    sanitized = prompt
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "[filtered]", ignore_case=True)
    
    return sanitized
```

## Workflow Security

### Sandboxing Tasks

Run untrusted tasks in isolated environments:

```yaml
tasks:
  - id: untrusted_task
    type: function
    config:
      module: user_code
      function: run_user_script
      sandbox:
        enabled: true
        timeout: 30
        memory_limit: 256MB
        network_access: false
```

### Task Permissions

```yaml
tasks:
  - id: safe_task
    type: prompt
    config:
      prompt: "{{user_input}}"
      permissions:
        read_only: true
        no_file_system: true
        no_network: false
```

## Network Security

### TLS Configuration

Ensure all external connections use TLS:

```yaml
mcp_adapter:
  transport:
    ssl_verify: true
    ssl_cert: /path/to/ca-bundle.crt
```

### Proxy Configuration

Route traffic through secure proxies:

```yaml
network:
  proxy:
    enabled: true
    http_proxy: http://proxy.company.com:8080
    https_proxy: http://proxy.company.com:8080
    no_proxy: localhost,127.0.0.1
```

## Data Protection

### Sensitive Data Handling

```python
class SecureWorkflow:
    def mask_sensitive(self, data):
        """Mask sensitive fields in output."""
        sensitive_fields = ["password", "api_key", "secret", "token"]
        
        masked = data.copy()
        for field in sensitive_fields:
            if field in masked:
                masked[field] = "********"
        
        return masked
    
    def redact_logs(self, log_data):
        """Remove sensitive data from logs."""
        import re
        # Redact API keys
        log_data = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-********', log_data)
        # Redact tokens
        log_data = re.sub(r'token["\']?\s*:\s*["\']?[a-zA-Z0-9-]+', 'token": "********"', log_data)
        return log_data
```

### Data Encryption

```yaml
security:
  encryption:
    enabled: true
    key_env: DATA_ENCRYPTION_KEY
    
  # At-rest encryption for workflow data
  storage:
    encrypted: true
    key_id: aws/ssm/encryption-key
```

## Audit Logging

### Enabling Audit Logs

```yaml
security:
  audit:
    enabled: true
    level: detailed
    destination: file
    path: /var/log/ai-runtime/audit.log
    
  # What to audit
  audit_include:
    - workflow_execution
    - task_completion
    - authentication
    - configuration_change
    - errors
```

### Audit Log Format

```json
{
  "timestamp": "2026-05-25T10:30:00.000Z",
  "event_type": "workflow_execution",
  "workflow_id": "wf-12345",
  "user": "admin@company.com",
  "action": "start",
  "metadata": {
    "workflow_name": "customer-analysis",
    "source_ip": "192.168.1.100"
  }
}
```

## Rate Limiting

### Per-User Rate Limits

```yaml
security:
  rate_limiting:
    enabled: true
    
    # Per-user limits
    per_user:
      requests_per_minute: 60
      workflows_per_hour: 100
      concurrent_workflows: 5
      
    # Global limits
    global:
      requests_per_minute: 1000
```

## Authentication

### API Token Authentication

```yaml
security:
  authentication:
    type: token
    token_header: X-API-Key
    token_env: API_AUTH_TOKEN
    
  # Or OAuth
  authentication:
    type: oauth
    provider: azure
    client_id_env: OAUTH_CLIENT_ID
    tenant_id: your-tenant-id
```

### Role-Based Access Control

```yaml
security:
  rbac:
    enabled: true
    
    roles:
      admin:
        - workflow:*
        - system:*
        - config:*
        
      operator:
        - workflow:run
        - workflow:list
        - workflow:logs
        
      viewer:
        - workflow:list
        - workflow:inspect
```

## Compliance

### Data Residency

```yaml
security:
  data_residency:
    enabled: true
    region: us-east-1
    allowed_regions:
      - us-east-1
      - us-west-2
```

### Data Retention

```yaml
security:
  retention:
    logs: 90days
    workflow_data: 30days
    audit_logs: 1year
    
  # Auto-delete after retention period
  auto_cleanup: true
```

## Security Checklist

Before deploying to production:

- [ ] API keys stored in environment variables or secrets manager
- [ ] TLS/SSL enabled for all external connections
- [ ] Input validation implemented for all user inputs
- [ ] Sensitive data masked in logs and outputs
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] Authentication required for API access
- [ ] Role-based access control implemented
- [ ] Workflow sandboxing for untrusted code
- [ ] Data retention policies configured
- [ ] Security scanning completed on custom plugins
- [ ] Dependencies audited for vulnerabilities

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public GitHub issue
2. Email security@company.com with details
3. Allow time for assessment and fix
4. We will credit researchers (with permission)

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Guide](https://docs.python.org/3/tutorial/stdlib.html#crypto)
- [MCP Security Considerations](./mcp-adapter.md#security)
- [MCP Deployment Isolation](../security/deployment-isolation.md)
