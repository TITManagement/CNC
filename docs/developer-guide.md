# Developer Guide

## Project Structure

```
CNC/
├── src/              # Source code
│   └── xy_runner.py  # Main application
├── examples/         # Configuration and sample files
│   ├── job*.yaml     # Job configurations
│   └── *.svg         # Sample SVG files
├── docs/             # Documentation
├── scripts/          # Setup and utility scripts
├── requirements.txt  # Python dependencies
└── pyproject.toml    # Package configuration
```

## Code Architecture

### Core Classes

#### GCodeWrapper
Manages G-code generation and command processing:
```python
class GCodeWrapper:
    def __init__(self, config):
        # Initialize with YAML configuration
        
    def run_job(self):
        # Main execution loop
        
    def process_svg_file(self, svg_path):
        # Convert SVG to motion commands
```

#### SimDriver
Matplotlib-based simulation:
```python
class SimDriver:
    def show(self, tracks):
        # Animate CNC movements
        # Real-time visualization
        # Track display with colors
```

#### ChuoDriver
Hardware interface for Chuo Seiki machines:
```python
class ChuoDriver:
    def __init__(self, com_port):
        # Serial communication setup
        
    def move_to(self, x, y):
        # Send movement commands
```

## Development Setup

1. **Clone and setup**:
   ```bash
   git clone https://github.com/TITManagement/CNC.git
   cd CNC
   ./scripts/setup.sh --dev
   ```

2. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## Code Style

We use Black for code formatting:
```bash
black src/ --line-length 100
```

Type checking with mypy:
```bash
mypy src/
```

## Testing

Run tests with pytest:
```bash
pytest tests/
```

## Adding New Hardware Drivers

1. **Create driver class**:
   ```python
   class NewDriver:
       def __init__(self, config):
           pass
           
       def move_to(self, x, y):
           # Implement hardware-specific movement
           pass
           
       def set_speed(self, speed):
           # Set movement speed
           pass
   ```

2. **Register in main**:
   ```python
   driver_map = {
       'sim': SimDriver,
       'chuo': ChuoDriver,
       'new': NewDriver,  # Add here
   }
   ```

## Configuration System

YAML configurations support:
- Motion parameters
- Hardware settings
- Safety limits
- Debug options

Example structure:
```yaml
# Hardware driver selection
driver: sim  # or 'chuo', 'new'

# Motion control
motion_params:
  rapid_speed: 1000
  cut_speed: 100

# Input source
svg_file: examples/drawing.svg
# or
pattern:
  type: grid_circles
  rows: 3
  cols: 3
```

## SVG Processing

The system uses `svgpathtools` for path extraction:

```python
from svgpathtools import svg2paths

def process_svg_file(self, svg_path):
    paths, attributes = svg2paths(svg_path)
    for path in paths:
        # Convert path to coordinate points
        points = self.path_to_points(path)
        # Generate movement commands
        self.add_track(points)
```

## Debugging

Enable debug mode in configuration:
```yaml
debug: true
```

This provides:
- Detailed parsing output
- Command generation logs
- Serial communication traces
- Animation frame details

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run code quality checks
5. Submit pull request

### Code Quality Checklist
- [ ] Black formatting applied
- [ ] Type hints added
- [ ] Tests written
- [ ] Documentation updated
- [ ] No lint errors