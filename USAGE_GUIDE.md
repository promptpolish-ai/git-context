# git-context Usage Guide

## Basic Usage

```bash
# Show project structure + git info
git-context

# Full context for AI assistants (includes file contents)
git-context --files

# Custom depth (default: 4)
git-context --depth 3

# Output to file
git-context --files -o ai-context.txt

# JSON output for tools and scripts
git-context --json

# Any repo, anywhere
git-context --dir /path/to/project
```

## AI Prompt Templates

### For Claude/Codex
```
Read this repo context and help me understand the architecture:
[paste git-context output here]
```

### For ChatGPT/Copilot
```
Analyze this codebase and suggest improvements:
[paste git-context output here]
```

## Examples

### Get context for PR review
```bash
git-context --log 50 --files > pr-context.txt
```

### Quick project overview
```bash
git-context --depth 2
```

## Support
ETH: 0x1fca7781515a1bdb2950543b075d060489701424
GitHub: https://github.com/promptpolish-ai/git-context
