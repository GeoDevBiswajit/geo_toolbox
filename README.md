# geo_toolbox

Geospatial data extraction and analysis toolkit powered by Google Earth Engine.

## Features

- **GEE Data Extraction**: Extract Sentinel-2 time series data for any area of interest
- **Custom Indices**: Compute standard vegetation indices (NDVI, NDTI, EVI) or define custom formulas
- **Time Series Processing**: Aggregate, interpolate, and smooth temporal data
- **Visualization**: Create interactive (Plotly) and static (Matplotlib) plots

## Installation

### From source (development)

```bash
git clone https://github.com/yourusername/geo-toolbox.git
cd geo-toolbox
pip install -e ".[dev,notebooks]"
```

### Standard installation

```bash
pip install geo-toolbox
```

## Quick Start

```python
import geopandas as gpd
from geo_toolbox import GEETimeSeriesExtractor, TimeSeriesProcessor, TimeSeriesPlotter

# Load your area of interest
gdf = gpd.read_file('example_data/input/farm1.gpkg')
aoi = geemap.gdf_to_ee(gdf).geometry()

# Extract Sentinel-2 time series
extractor = GEETimeSeriesExtractor()
raw_df = extractor.extract(
    aoi=aoi,
    start_date='2025-10-01',
    end_date='2026-04-01',
    indices=['NDVI', 'NDTI'],
    reducer='median'
)

# Process the data
processor = TimeSeriesProcessor(raw_df)
processed_df = processor.aggregate(frequency='2W').df

# Create an interactive plot
plotter = TimeSeriesPlotter(processed_df)
plotter.plot_interactive(
    columns_to_plot=['NDVI', 'NDTI'],
    title="Farm Time Series Analysis"
)
```

## Documentation

For more details, see the [API documentation](docs/API.md).

## Examples

Check the `examples/notebooks/` directory for Jupyter notebooks with complete workflows.

## License

MIT License - see LICENSE file for details
