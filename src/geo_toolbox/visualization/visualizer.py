import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import os
import pandas as pd

class TimeSeriesPlotter:
    """Generates static or interactive plots from processed data."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Reset index if date is the index, so we can plot it easily
        if self.df.index.name == 'date':
            self.df = self.df.reset_index()
    
    def plot_static(self, columns_to_plot, title="Time Series Analysis", style_dict=None, save_file_path: str = None, **ax_kwargs):
        """
        Matplotlib static plot with dynamic keyword arguments.
        
        columns_to_plot: list of column names to plot.
        style_dict: dictionary mapping column names to Matplotlib line kwargs 
                    (e.g., {'NDVI': {'color': 'green', 'lw': 2}})
        ax_kwargs: any Matplotlib Axes kwargs (e.g., xlim, ylim, figsize)
        """
        plt.style.use('ggplot')
        
        # 1. Pop figsize from ax_kwargs if the user provided it; otherwise default to (12, 6)
        figsize = ax_kwargs.pop('figsize', (12, 6))
        fig, ax = plt.subplots(figsize=figsize)
        
        # 2. Ensure style_dict is at least an empty dictionary if the user didn't provide one
        style_dict = style_dict or {}
        
        for col in columns_to_plot:
            if col in self.df.columns:
                # Extract the specific kwargs for this column, or use empty dict
                col_style = style_dict.get(col, {})
                
                # Provide a default marker if the user didn't specify one
                col_style.setdefault('marker', 'o')
                
                # The ** operator unpacks the dictionary as keyword arguments into ax.plot()
                ax.plot(self.df['date'], self.df[col], label=col, **col_style)
                
        # Default labels and titles (can be overwritten by ax_kwargs)
        ax.set_title(title, fontweight='bold')
        ax.set_xlabel("Date", fontweight='bold')
        ax.set_ylabel("Index Value", fontweight='bold')

        if ax_kwargs:
            ax.set(**ax_kwargs)
            
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=30, ha='right')
        ax.legend(loc='upper left')
        fig.tight_layout()
        if save_file_path:
            os.makedirs(os.path.dirname(save_file_path), exist_ok=True)
            if os.path.exists(save_file_path):
                print(f"Warning: {save_file_path} already exists and will be overwritten.")
            plt.savefig(save_file_path, dpi=300)
        plt.show()

    def plot_interactive(self, columns_to_plot, title="Time Series Analysis", style_dict=None, **layout_kwargs):
        """
        Plotly interactive plot with dynamic keyword arguments.
        
        columns_to_plot: list of column names to plot.
        style_dict: dictionary mapping column names to Plotly Scatter kwargs 
                    (e.g., {'NDVI': {'line_color': 'green', 'mode': 'lines+markers'}})
        layout_kwargs: any Plotly layout kwargs (e.g., xaxis_range, yaxis_range, height)
        """
        fig = go.Figure()
        
        # Ensure style_dict is available
        style_dict = style_dict or {}
        
        for col in columns_to_plot:
            if col in self.df.columns:
                # Extract the specific Plotly kwargs for this column
                col_style = style_dict.get(col, {})
                
                # Set Plotly-specific defaults if the user didn't provide them
                col_style.setdefault('mode', 'lines+markers')
                col_style.setdefault('name', col)  # Ensure the legend name matches the column
                
                # The ** operator unpacks the dictionary directly into the Scatter trace
                fig.add_trace(go.Scatter(
                    x=self.df['date'], 
                    y=self.df[col], 
                    **col_style
                ))
                
        # 1. Define standard package defaults for the layout
        layout_config = dict(
            title=title,
            xaxis_title="Date",
            yaxis_title="Index Value",
            template="plotly_white",
            hovermode="x unified"  # Great for time series: shows all values for a given date
        )
        
        # 2. Update/Overwrite defaults with anything the user passed in **layout_kwargs
        layout_config.update(layout_kwargs)
        
        # 3. Apply everything to the figure
        fig.update_layout(**layout_config)
        
        fig.show()
