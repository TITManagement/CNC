# User Guide

## Installation

### Quick Setup
Use the automated setup script:
```bash
./scripts/setup.sh
```

### Manual Setup
1. Create virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

### Running SVG Jobs
1. Export your PowerPoint slide as SVG
2. Run with configuration:
   ```bash
   python src/xy_runner.py examples/job_svg.yaml
   ```

### Configuration Files
- `job_svg.yaml` - SVG file processing with file selection dialog
- `job_svg_chuo.yaml` - Real hardware configuration
- `job.yaml` - Grid pattern generation

## PowerPoint to SVG Workflow

1. **Create PowerPoint Slide**
   - Use shapes, not text
   - Keep designs simple
   - Use high contrast colors

2. **Export as SVG**
   - File → Export → Change File Type → SVG
   - Choose "Current Slide"

3. **Process with CNC XY Runner**
   - Use SVG configuration file
   - Select exported SVG when prompted

## Motion Parameters

Adjust these settings in your YAML configuration:

```yaml
motion_params:
  rapid_speed: 1000    # Fast movement speed
  cut_speed: 100       # Cutting/drawing speed
  lift_height: 5       # Z-axis lift for rapid moves
```

## Safety Settings

Configure limits to protect your machine:

```yaml
safety:
  max_x: 100
  max_y: 100
  max_speed: 2000
  enable_limits: true
```

## Troubleshooting

### Common Issues

1. **"No tracks" error**
   - Ensure SVG contains path elements, not text
   - Re-export from PowerPoint with shapes only

2. **File selection dialog doesn't appear**
   - Check that tkinter is installed
   - Verify desktop environment supports GUI

3. **Serial communication fails**
   - Check COM port settings
   - Verify hardware connections
   - Test with simulation mode first

### Debug Mode

Enable debug output:
```yaml
debug: true
```

This will show:
- Parsed SVG elements
- Generated motion commands
- Serial communication details