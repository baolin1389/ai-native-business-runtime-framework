# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Problem: `ai-runtime: command not found`

**Solution:**
1. Verify installation:
   ```bash
   pip show ai-runtime
   ```

2. Check PATH includes pip's bin directory:
   ```bash
   echo $PATH
   # Add to PATH if needed:
   export PATH="$HOME/Library/Python/X.X/bin:$PATH"
   ```

3. Reinstall:
   ```bash
   pip install --force-reinstall ai-runtime
   ```

#### Problem: Python version mismatch

**Error:** `Python 3.10+ is required`

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.10+ via pyenv
pyenv install 3.10.12
pyenv local 3.10.12
```

---

### Configuration Issues

#### Problem: API key not found

**Error:** `API key environment variable OPENAI_API_KEY is not set`

**Solution:**
```bash
# Set the environment variable
export OPENAI_API_KEY="sk-..."

# Verify it's set
echo $OPENAI_API_KEY

# For permanent setup, add to shell profile
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
```

#### Problem: Configuration file not loading

**Solution:**
1. Check config file location:
   ```bash
   ai-runtime config show --effective
   ```

2. Validate YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('~/.ai-runtime/config.yaml'))"
   ```

3. Check file permissions:
   ```bash
   ls -la ~/.ai-runtime/config.yaml
   # Should be readable: -rw-r--r--
   ```

---

### Workflow Execution Issues

#### Problem: Workflow validation fails

**Error:** `ValidationError: Task 'xyz' has unknown type 'promptt'`

**Solution:**
1. Check task type spelling (typo in example: `promptt` vs `prompt`)
2. Verify task type is supported:
   ```bash
   ai-runtime workflow validate my-workflow.yaml --verbose
   ```

#### Problem: Dependency cycle detected

**Error:** `DependencyCycleError: Cycle detected: task_a -> task_b -> task_c -> task_a`

**Solution:**
Review your `depends_on` configuration to remove circular dependencies:

```yaml
# Wrong - creates cycle
task_a:
  depends_on: [task_c]
task_b:
  depends_on: [task_a]
task_c:
  depends_on: [task_b]

# Correct - no cycles
task_a:
task_b:
  depends_on: [task_a]
task_c:
  depends_on: [task_b]
```

#### Problem: Task timeout

**Error:** `TaskTimeoutError: Task 'my-task' exceeded timeout of 300s`

**Solution:**
1. Increase timeout in workflow config:
   ```yaml
   tasks:
     - id: my-task
       type: prompt
       config:
         timeout: 600  # 10 minutes
   ```

2. Or set global default:
   ```bash
   ai-runtime config set execution.default_timeout 600
   ```

---

### Provider/API Issues

#### Problem: Rate limit exceeded

**Error:** `RateLimitError: API rate limit exceeded (60 requests/minute)`

**Solution:**
1. Wait and retry (rate limits reset typically after 1 minute)
2. Add delay between requests:
   ```yaml
   config:
     rate_limit:
       requests_per_minute: 30  # Reduce request rate
   ```
3. Use a model with higher rate limits

#### Problem: Authentication failed

**Error:** `AuthenticationError: Invalid API key`

**Solution:**
1. Verify API key is correct:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. Check key hasn't expired or been revoked
3. Ensure no extra spaces in environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."  # No spaces around =
   ```

#### Problem: Model not found

**Error:** `ModelNotFoundError: Model 'gpt-5' not found`

**Solution:**
Use correct model name:
```yaml
# Correct model names
model: gpt-4o
model: gpt-4o-mini
model: claude-3-5-sonnet-20241022
model: gemini-1.5-flash
```

---

### Runtime Issues

#### Problem: Out of memory

**Error:** `MemoryError: Task exceeded memory limit`

**Solution:**
1. Process data in smaller batches
2. Increase memory limit in config:
   ```yaml
   resources:
     memory_limit: 4GB
   ```
3. Use streaming for large responses

#### Problem: Disk space exhausted

**Solution:**
1. Clean up old data:
   ```bash
   rm -rf ~/.ai-runtime/data/*
   ```

2. Reduce cache size:
   ```yaml
   resources:
     disk_cache_size: 500MB
   ```

---

### Debugging

#### Enable Verbose Logging

```bash
# Run with verbose output
ai-runtime workflow run my-workflow.yaml --verbose

# Set log level
export AI_RUNTIME_LOG_LEVEL=DEBUG
ai-runtime workflow run my-workflow.yaml
```

#### View Logs

```bash
# View recent logs
ai-runtime logs

# Follow logs in real-time
ai-runtime logs --follow

# Filter logs by workflow
ai-runtime logs --workflow my-workflow
```

#### Inspect Execution State

```bash
# View running workflows
ai-runtime workflow list --status running

# Inspect specific workflow
ai-runtime workflow inspect <workflow-id>

# View task details
ai-runtime workflow tasks <workflow-id>
```

---

### Getting Help

If issues persist:

1. **Check documentation:** Review relevant guides in `/docs/guides/`
2. **Search existing issues:** Check GitHub issues for similar problems
3. **Enable debug mode:**
   ```bash
   export AI_RUNTIME_LOG_LEVEL=DEBUG
   ai-runtime workflow run my-workflow.yaml 2>&1 | tee debug.log
   ```
4. **Contact support:** Include debug log and:
   - Output of `ai-runtime version`
   - Output of `ai-runtime config show --effective`
   - Minimal reproduction case

---

## Error Code Reference

| Code | Name | Description |
|------|------|-------------|
| 1 | GeneralError | Unspecified error |
| 2 | InvalidArguments | Invalid command arguments |
| 3 | WorkflowExecutionError | Workflow execution failed |
| 4 | ConfigurationError | Invalid configuration |
| 5 | ConnectionError | Cannot connect to service |
| 6 | AuthenticationError | Authentication failed |
| 7 | RateLimitError | Rate limit exceeded |
| 8 | TimeoutError | Operation timed out |
| 9 | ValidationError | Validation failed |
| 10 | DependencyCycleError | Circular dependencies detected |
