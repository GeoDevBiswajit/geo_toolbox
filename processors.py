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
    def smooth_series(self, column, sigma=10, suffix='_smoothed'):
        """
        Upsamples the dataframe to daily, interpolates gaps, 
        and applies Gaussian smoothing as a new column.
        """
        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame.")
        if not self.df.index.is_unique:
            print("Notice: Duplicate dates found (likely overlapping tiles). Averaging duplicates...")
            self.df = self.df.groupby(self.df.index).mean()

        # 1. Upsample to daily frequency so the smooth curve looks natural
        daily_index = pd.date_range(start=self.df.index.min(), end=self.df.index.max(), freq='D')
        self.df = self.df.reindex(daily_index)
        self.df.index.name = 'date'
        
        # 2. Interpolate the NaNs using time-based linear interpolation
        interpolated = self.df[column].interpolate(method='time')
        
        # 3. Apply Gaussian filter and store it alongside the raw data
        new_col_name = f"{column}{suffix}"
        self.df[new_col_name] = gaussian_filter(interpolated.values, sigma=sigma)
        
        # 4. Return self to allow method chaining
        return self
    # def smooth_series(self, column, sigma=10):
    #     """Applies Gaussian smoothing to a specific column."""
    #     dates = self.df.index
    #     values = self.df[column].values
        
    #     # Calculate age in days for interpolation
    #     age = np.array([(d - dates[0]).days for d in dates])
    #     age_interp = np.arange(age.min(), age.max() + 1)
        
    #     interp_func = interp1d(age, values, kind='linear', fill_value="extrapolate")
    #     smoothed_values = gaussian_filter(interp_func(age_interp), sigma=sigma)
        
    #     smoothed_dates = np.array([dates[0] + pd.Timedelta(days=int(i)) for i in age_interp])
        
    #     return smoothed_dates, smoothed_values