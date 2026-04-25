import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go

class TimeSeriesPlotter:
    """Generates static or interactive plots from processed data."""
    
    def __init__(self, df):
        self.df = df
        # Reset index if date is the index, so we can plot it easily
        if self.df.index.name == 'date':
            self.df = self.df.reset_index()

    def plot_static(self, columns_to_plot, title="Time Series Analysis"):
        """Matplotlib static plot."""
        plt.style.use('ggplot')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for col in columns_to_plot:
            if col in self.df.columns:
                ax.plot(self.df['date'], self.df[col], marker='o', label=col)
                
        ax.set_title(title, fontweight='bold')
        ax.set_xlabel("Date", fontweight='bold')
        ax.set_ylabel("Index Value", fontweight='bold')
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=45, ha='right')
        ax.legend()
        fig.tight_layout()
        plt.show()

    def plot_interactive(self, columns_to_plot, title="Time Series Analysis"):
        """Plotly interactive plot."""
        fig = go.Figure()
        
        for col in columns_to_plot:
            if col in self.df.columns:
                fig.add_trace(go.Scatter(x=self.df['date'], y=self.df[col], 
                                         mode='lines+markers', name=col))
                
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Index Value",
                          template="plotly_white")
        fig.show()