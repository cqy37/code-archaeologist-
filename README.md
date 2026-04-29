# Code Archaeologist

An intelligent multi-agent system for analyzing, understanding, and safely modernizing legacy codebases.

## Overview

Code Archaeologist addresses the "nobody dares touch it" problem facing organizations with decade-old legacy systems. It autonomously explores codebases, reconstructs business intent from undocumented code, proposes safe modernization strategies, and validates changes.

## Core Agents

| Agent | Responsibility |
|-------|---------------|
| **Explorer** | Scans repositories, maps file dependencies, identifies hotspots and dead code |
| **Reasoner** | Uses long-chain reasoning to infer business logic and document intent |
| **Refactor** | Generates safe modernization plans and code transformations |
| **Validator** | Runs regression tests, checks behavioral consistency, validates performance |

## Architecture

```
User Query / Target Directory
       |
       v
  [Orchestrator]
       |
  +----+----+-----+
  |         |     |
  v         v     v
[Explorer][Reasoner][Refactor] <--> [Validator]
  |         |     |          |
  v         v     v          v
[Knowledge Base / Dependency Graph]
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 2. Analyze a Codebase

```bash
python main.py analyze /path/to/legacy/code --output report.json
```

### 3. Generate Modernization Plan

```bash
python main.py plan /path/to/legacy/code --target module_name --output plan.json
```

### 4. Full Pipeline (Explore -> Reason -> Refactor -> Validate)

```bash
python main.py pipeline /path/to/legacy/code --target module_name
```

## Example

The `examples/sample_project/` directory contains a simulated legacy billing module. Run:

```bash
python main.py pipeline examples/sample_project --target legacy_billing
```

## Key Features

- **Long-Chain Reasoning**: Multi-step analysis from raw code -> dependency mapping -> business intent reconstruction -> safe refactoring
- **Multi-Agent Collaboration**: Agents communicate through a shared knowledge base, with feedback loops (e.g., Refactor proposes -> Validator rejects -> Reasoner re-analyzes -> Refactor retries)
- **Cross-Language Support**: Python, JavaScript, Java, SQL analysis (extensible via Tree-sitter)
- **Safety-First**: All refactoring suggestions include behavioral validation checkpoints

## License

MIT
