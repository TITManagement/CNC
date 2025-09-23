# CNC XY Runner Documentation

Welcome to the CNC XY Runner documentation. This system enables seamless conversion from PowerPoint presentations to CNC machine instructions via SVG path processing.

## Table of Contents

- [User Guide](user-guide.md) - How to use the CNC XY Runner
- [Developer Guide](developer-guide.md) - Development and customization
- [API Reference](api-reference.md) - Code documentation
- [Configuration](configuration.md) - YAML configuration details
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Quick Start

1. **Install**: Use the setup script `./scripts/setup.sh`
2. **Configure**: Edit YAML files in `examples/`
3. **Run**: Execute with `python src/xy_runner.py examples/job_svg.yaml`

## System Overview

The CNC XY Runner processes SVG files through the following pipeline:

```
PowerPoint → SVG Export → SVG Path Processing → G-Code Generation → CNC Control
```

Key components:
- **SVG Path Parser**: Converts SVG paths to coordinate sequences
- **Simulation Driver**: Matplotlib-based visualization
- **Chuo Driver**: Real hardware interface for Chuo Seiki machines
- **Configuration System**: YAML-based job definitions

## Features

- ✅ PowerPoint to CNC workflow
- ✅ Interactive SVG file selection
- ✅ Real-time simulation with matplotlib
- ✅ Chuo Seiki machine integration
- ✅ Configurable motion parameters
- ✅ Grid pattern generation
- ✅ Safety limits and validation

## Hardware Support

- **Chuo Seiki XY Stages**: Serial communication via PySerial
- **Simulation Mode**: No hardware required for testing
- **Custom Drivers**: Extensible architecture for new hardware

## License

MIT License - see [LICENSE](../LICENSE) for details.