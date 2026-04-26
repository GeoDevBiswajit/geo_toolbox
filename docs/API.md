# geo-toolbox API Documentation

## Core Module

### `Sentinal2TimeSeriesExtractor`

Main class for extracting time series data from Google Earth Engine.

**Parameters:**
- `collection_name` (str): GEE image collection name. Default: `"COPERNICUS/S2_SR_HARMONIZED"`

**Methods:**

#### `extract(aoi, start_date, end_date, reducer, indices, custom_formulas, apply_mask, **reduce_kwargs)`

Extract aggregated index values for a region of interest.

**Parameters:**
- `aoi` (ee.Geometry): Area of interest geometry from Earth Engine
- `start_date` (str): Start date in 'YYYY-MM-DD' format
- `end_date` (str): End date in 'YYYY-MM-DD' format
- `reducer` (Reducer or str): Aggregation method ('mean', 'median', 'max', 'min', 'sum')
- `indices` (list): List of index names ('NDVI', 'NDTI', 'EVI', etc.)
- `custom_formulas` (dict): Custom index formulas. E.g., `{'MY_INDEX': 'b("B8")/b("B3")'}`
- `apply_mask` (bool): Apply cloud mask if True. Default: True
- `**reduce_kwargs`: Additional GEE reduceRegion parameters (scale, maxPixels, etc.)

**Returns:**
- `pd.DataFrame`: DataFrame with date column and calculated indices

**Example:**
```python
extractor = Sentinal2TimeSeriesExtractor()
df = extractor.extract(
    aoi=my_aoi_geometry,
    start_date='2025-10-01',
    end_date='2026-04-01',
    indices=['NDVI', 'NDTI'],
    reducer='median'
)
```

### `Reducer`

Enum for aggregation methods:
- `Reducer.mean`
- `Reducer.median`
- `Reducer.max`
- `Reducer.min`
- `Reducer.sum`

---

## Processing Module

### `TimeSeriesProcessor`

Processes time series data with aggregation and smoothing.

**Parameters:**
- `df` (pd.DataFrame): Input DataFrame with 'date' column

**Methods:**

#### `aggregate(frequency='W')`

Aggregate data by time period.

**Parameters:**
- `frequency` (str): Resampling frequency. 'D'=daily, 'W'=weekly, '2W'=fortnightly, 'M'=monthly, etc.

**Returns:**
- Self (for method chaining)

#### `smooth_series(column, sigma=10, suffix='_smoothed')`

Apply Gaussian smoothing to a time series column.

**Parameters:**
- `column` (str): Column name to smooth
- `sigma` (int): Gaussian filter standard deviation. Higher = more smoothing
- `suffix` (str): Suffix for smoothed column name

**Returns:**
- Self (for method chaining)

**Example:**
```python
processor = TimeSeriesProcessor(raw_df)
processed_df = (processor
    .aggregate(frequency='2W')
    .smooth_series('NDVI', sigma=10)
    .df)
```

---

## Visualization Module

### `TimeSeriesPlotter`

Create static and interactive time series plots.

**Parameters:**
- `df` (pd.DataFrame): Input DataFrame with 'date' column

**Methods:**

#### `plot_static(columns_to_plot, title, style_dict, save_file_path, **ax_kwargs)`

Create a Matplotlib static plot.

**Parameters:**
- `columns_to_plot` (list): Columns to plot
- `title` (str): Plot title
- `style_dict` (dict): Matplotlib line styling per column
- `save_file_path` (str): Optional path to save the figure
- `**ax_kwargs`: Additional Matplotlib Axes parameters (ylim, xlim, figsize, etc.)

#### `plot_interactive(columns_to_plot, title, style_dict, **layout_kwargs)`

Create an interactive Plotly plot.

**Parameters:**
- `columns_to_plot` (list): Columns to plot
- `title` (str): Plot title
- `style_dict` (dict): Plotly line styling per column
- `**layout_kwargs`: Additional Plotly layout parameters (height, width, yaxis_range, etc.)

**Example:**
```python
plotter = TimeSeriesPlotter(processed_df)
plotter.plot_interactive(
    columns_to_plot=['NDVI', 'NDTI'],
    title="Farm Analysis",
    yaxis_range=[0, 1],
    height=600
)
```

---

## Standard Vegetation Indices

Available standard indices in `GEETimeSeriesExtractor`:

| Index | Formula | Use Case |
|-------|---------|----------|
| NDVI | (B8 - B4) / (B8 + B4) | Vegetation health |
| NDTI | (B11 - B12) / (B11 + B12) | Tilling intensity |
| EVI | 2.5 * ((B8 - B4) / (B8 + 6*B4 - 7*B2 + 10000)) | Enhanced vegetation index |

Where B2=Blue, B3=Green, B4=Red, B8=NIR, B11=SWIR1, B12=SWIR2

---

## Installation for Development

```bash
cd geo_toolbox
pip install -e ".[dev,notebooks]"
```

This installs the package in editable mode with development and Jupyter notebook dependencies.
