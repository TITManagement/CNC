# CNC XY Runner

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PowerPoint to CNC: Professional SVG path-based XY controller for manufacturing automation**

[Features](#features) •
[Installation](#installation) •
[Quick Start](#quick-start) •
[Documentation](#documentation) •
[Contributing](#contributing)

</div>

## Overview

CNC XY Runner bridges the gap between design and manufacturing by converting PowerPoint presentations directly into CNC machine instructions. This system processes SVG exports through sophisticated path analysis and generates precise motion control commands for XY positioning systems.

### Key Capabilities

🎯 **Design to Manufacturing Pipeline**
- PowerPoint → SVG → CNC workflow
- Interactive file selection with GUI
- Real-time simulation and preview

🔧 **Hardware Integration**
- Chuo Seiki XY stage control
- Serial communication interface
- Extensible driver architecture

📊 **Visualization & Safety**
- matplotlib-based real-time simulation
- Motion path preview and validation
- Configurable safety limits and parameters

## Features

- ✅ **PowerPoint Integration**: Direct SVG export processing
- ✅ **Interactive GUI**: File selection dialogs for ease of use
- ✅ **Real-time Simulation**: matplotlib animation with motion preview
- ✅ **Hardware Control**: Chuo Seiki machine integration via PySerial
- ✅ **Flexible Configuration**: YAML-based job definitions
- ✅ **Pattern Generation**: Built-in grid and geometric patterns
- ✅ **Safety Systems**: Configurable limits and motion validation
- ✅ **Extensible Architecture**: Plugin-based driver system

## Installation

### Quick Setup (Recommended)

```bash
git clone https://github.com/TITManagement/CNC.git
cd CNC
./scripts/setup.sh
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/TITManagement/CNC.git
cd CNC

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Development Setup

```bash
./scripts/setup.sh --dev
```

This installs additional development tools (pytest, black, mypy, etc.)

## Quick Start

### 1. PowerPoint to SVG
1. Create your design in PowerPoint using **shapes** (not text)
2. Export as SVG: `File → Export → Change File Type → SVG`
3. Select "Current Slide"

### 2. Run Simulation
```bash
# Using Python module
python src/xy_runner.py examples/job_svg.yaml

# Or using installed command
cnc-xy-runner examples/job_svg.yaml
```

### 3. Select Your SVG
- A file dialog will appear
- Select your exported SVG file
- Watch the real-time simulation

## Project Structure

```
CNC/
├── src/                    # Source code
│   └── xy_runner.py        # Main application
├── examples/               # Configurations & samples
│   ├── job_svg.yaml        # SVG processing config
│   ├── job_svg_chuo.yaml   # Hardware config
│   ├── job.yaml            # Grid pattern config
│   └── drawing.svg         # Sample SVG file
├── docs/                   # Documentation
│   ├── user-guide.md       # User documentation
│   └── developer-guide.md  # Development guide
├── scripts/                # Utility scripts
│   └── setup.sh            # Environment setup
├── requirements.txt        # Dependencies
├── pyproject.toml          # Package configuration
└── README.md               # This file
```

## Configuration

The system uses YAML configuration files to define jobs:

```yaml
# examples/job_svg.yaml
driver: sim                 # 'sim' for simulation, 'chuo' for hardware
svg_file: select            # 'select' for GUI file picker

motion_params:
  rapid_speed: 1000         # Fast movement speed (mm/min)
  cut_speed: 100            # Drawing speed (mm/min)
  lift_height: 5            # Z-axis lift for rapid moves

visualization:
  animate: true             # Enable real-time animation
  title: "CNC XY Simulation"
```

## Hardware Support

### Chuo Seiki Integration
- Serial communication via PySerial
- Configurable COM port and baud rate
- Real-time position feedback
- Safety limit enforcement

### Simulation Mode
- No hardware required
- matplotlib-based visualization
- Motion path preview
- Animation controls

## Documentation

- 📖 [User Guide](docs/user-guide.md) - Complete usage instructions
- 🔧 [Developer Guide](docs/developer-guide.md) - Development and customization
- 📚 [Full Documentation](docs/index.md) - Comprehensive documentation index

## Contributing

We welcome contributions! Please see our [Developer Guide](docs/developer-guide.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `black src/ && mypy src/`
5. Submit a pull request

## Use Cases

- **Prototyping**: Rapid conversion of designs to physical movement
- **Education**: Teaching CNC concepts with visual feedback
- **Research**: Automated pattern generation for experiments
- **Manufacturing**: Production toolpath generation from presentations

## Technical Details

- **Python 3.8+** compatibility
- **Dependencies**: PyYAML, matplotlib, PySerial, svgpathtools
- **Architecture**: Modular driver system for extensibility
- **Testing**: pytest-based test suite
- **Code Quality**: Black formatting, mypy type checking

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 **Email**: info@titmanagement.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/TITManagement/CNC/issues)
- 📖 **Documentation**: [Full Documentation](docs/index.md)

---

<div align="center">
<strong>Transform your PowerPoint designs into precise CNC motion with professional-grade control and visualization.</strong>
</div>