# AgentZero

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

An agent-based decarbonisation pathways model.

This project demonstrates an end-to-end pipeline including assumptions packs, scenario packs, a simple simulation engine, and result generation. The model is deliberately minimal to maximise clarity and allow rapid iteration. Future versions can extend the data formats, agent behaviours and markets without changing the basic structure.

## Installation

```bash
# Install directly from GitHub
uv tool install git+https://github.com/dlg0/agent-zero

# Update to latest version
uv tool upgrade agentzero
```

## Usage

Run the command-line interface using the `agentzero` entrypoint:

```bash
# Validate an assumptions pack
agentzero validate data/assumptions_packs/baseline-v1

# Run a simulation
agentzero run --assum baseline-v1 --scen fast-elec-v1 --years 2025:2030 --out runs/
```

Results will be written into a unique run directory under `runs/`.

## Repository Structure

```
agent-zero/
├─ pyproject.toml        # package metadata and dependencies
├─ data/                 # sample assumptions and scenario packs
├─ runs/                 # simulation outputs (gitignored)
├─ src/agent_zero/       # source code for the model
├─ tests/                # test cases
└─ docs/                 # documentation
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/dlg0/agent-zero.git
cd agent-zero
uv sync --all-extras

# Run tests
uv run pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
