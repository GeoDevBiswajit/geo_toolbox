import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter
import pandas as pd

class TimeSeriesProcessor:
    """Handles temporal aggregation, smoothing, and feature extraction."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df.set_index('date', inplace=True)

    def aggregate(self, frequency='W'):
        """
        Aggregates data by time. 
        frequency: 'D' = Daily, 'W' = Weekly, '2W' = Fortnightly, 'M' = Monthly, 'Y' = Yearly or any number of days (e.g., '10D' for 10-day periods)
        """
        # Resample and take the mean, then drop empty periods
        self.df = self.df.resample(frequency).mean().dropna()
        return self

    def smooth_series(self, column, sigma=10):
        """Applies Gaussian smoothing to a specific column."""
        dates = self.df.index
        values = self.df[column].values
        
        # Calculate age in days for interpolation
        age = np.array([(d - dates[0]).days for d in dates])
        age_interp = np.arange(age.min(), age.max() + 1)
        
        interp_func = interp1d(age, values, kind='linear', fill_value="extrapolate")
        smoothed_values = gaussian_filter(interp_func(age_interp), sigma=sigma)
        
        smoothed_dates = np.array([dates[0] + pd.Timedelta(days=int(i)) for i in age_interp])
        
        return smoothed_dates, smoothed_values