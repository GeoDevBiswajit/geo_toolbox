import ee
import pandas as pd
from datetime import datetime
from enum import Enum

class Reducer(Enum):
    mean = 'mean'
    median = 'median'
    max = 'max'
    min = 'min'
    sum = 'sum'

class GEETimeSeriesExtractor:
    """Handles GEE interactions, cloud masking, and custom index extraction."""
    
    def __init__(self, collection_name="COPERNICUS/S2_SR_HARMONIZED"):
        self.collection_name = collection_name
        self.standard_indices = {
            'NDVI': '(b("B8") - b("B4")) / (b("B8") + b("B4"))',
            'NDTI': '(b("B11") - b("B12")) / (b("B11") + b("B12"))',
            'EVI': '2.5 * ((b("B8") - b("B4")) / (b("B8") + 6 * b("B4") - 7 * b("B2") + 10000))'
        }
        
        # 1. Create a mapping from your Enum/Strings to actual GEE Reducers
        self._reducer_map = {
            'mean': ee.Reducer.mean(),
            'median': ee.Reducer.median(),
            'max': ee.Reducer.max(),
            'min': ee.Reducer.min(),
            'sum': ee.Reducer.sum()
        }

    def _apply_cloud_mask(self, image):
        """Standard Sentinel-2 SCL cloud masking."""
        scl = image.select('SCL')
        mask = scl.gt(3).And(scl.lte(7))
        return image.updateMask(mask)

    def extract(self, aoi, start_date, end_date, reducer=Reducer.mean, indices=['NDVI'], custom_formulas=None, apply_mask=True, **reduce_kwargs):
        """
        Extracts aggregated values for requested indices over an AOI.
        
        reducer: Reducer Enum or string ('mean', 'median', etc.)
        **reduce_kwargs: Any kwargs to pass to GEE's reduceRegion (e.g., scale=20, maxPixels=1e9)
        """
        formulas_to_run = {}
        
        for idx in indices:
            if idx in self.standard_indices:
                formulas_to_run[idx] = self.standard_indices[idx]
        
        if custom_formulas:
            formulas_to_run.update(custom_formulas)
            
        # 2. Extract the string value safely, whether the user passed the Enum or a plain string
        reducer_key = reducer.value if isinstance(reducer, Enum) else str(reducer).lower()
        selected_gee_reducer = self._reducer_map.get(reducer_key, ee.Reducer.mean())

        def process_image(image):
            optical_bands = image.select('B.*').divide(10000)
            scaled = image.addBands(optical_bands, overwrite=True)
            
            if apply_mask:
                scaled = self._apply_cloud_mask(scaled)
            
            computed_bands = []
            for name, formula in formulas_to_run.items():
                index_img = scaled.expression(formula).rename(name)
                computed_bands.append(index_img)
            
            final_image = scaled.addBands(computed_bands)
            
            # 3. Setup default region kwargs
            region_params = {
                'reducer': selected_gee_reducer,
                'geometry': aoi,
                'scale': 10,       # Default Sentinel-2 resolution
                'maxPixels': 1e8   # Default safety limit
            }
            
            # 4. Overwrite defaults with anything the user passed in **reduce_kwargs
            region_params.update(reduce_kwargs)
            
            # 5. Unpack directly into reduceRegion
            mean_dict = final_image.select(list(formulas_to_run.keys())).reduceRegion(**region_params)
            
            properties = {'date': image.date().format('YYYY-MM-dd')}
            for name in formulas_to_run.keys():
                properties[name] = mean_dict.get(name)
                
            return ee.Feature(None, properties)

        collection = (ee.ImageCollection(self.collection_name)
                      .filterBounds(aoi)
                      .filterDate(start_date, end_date)
                      .map(process_image))
        
        features = collection.getInfo()['features']
        df = pd.DataFrame([f['properties'] for f in features])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna().sort_values(by='date').reset_index(drop=True)

# import ee
# import pandas as pd
# from datetime import datetime
# from enum import Enum

# class Reducer(Enum):
#     mean = 'mean'
#     median = 'median'
#     max = 'max'
#     min = 'min'

# class GEETimeSeriesExtractor:
#     """Handles GEE interactions, cloud masking, and custom index extraction."""
    
#     def __init__(self, collection_name="COPERNICUS/S2_SR_HARMONIZED"):
#         self.collection_name = collection_name
#         # Pre-define some standard formulas so the user doesn't have to memorize them
#         self.standard_indices = {
#             'NDVI': '(b("B8") - b("B4")) / (b("B8") + b("B4"))',
#             'NDTI': '(b("B11") - b("B12")) / (b("B11") + b("B12"))',
#             'EVI': '2.5 * ((b("B8") - b("B4")) / (b("B8") + 6 * b("B4") - 7 * b("B2") + 10000))'
#         }

#     def _apply_cloud_mask(self, image):
#         """Standard Sentinel-2 SCL cloud masking."""
#         scl = image.select('SCL')
#         mask = scl.gt(3).And(scl.lte(7))
#         return image.updateMask(mask)

#     def extract(self, aoi, start_date, end_date, reducer='mean', indices=['NDVI'], custom_formulas=None, apply_mask=True):
#         """
#         Extracts mean values for requested indices over an AOI.
#         aoi: ee.Geometry defining the area of interest
#         start_date, end_date: Strings in 'YYYY-MM-DD' format
#         indices: List of strings (e.g., ['NDVI', 'NDTI'])
#         custom_formulas: Dict of {name: formula} (e.g., {'MY_INDEX': 'b("B8")/b("B3")'})
#         """
#         formulas_to_run = {}
        
#         # Load requested standard indices
#         for idx in indices:
#             if idx in self.standard_indices:
#                 formulas_to_run[idx] = self.standard_indices[idx]
        
#         # Load any custom user indices
#         if custom_formulas:
#             formulas_to_run.update(custom_formulas)
#         def process_image(image):
#             # Scale ONLY the reflectance bands (starting with 'B'), leaving SCL intact
#             optical_bands = image.select('B.*').divide(10000)
            
#             # Overwrite the unscaled optical bands with the scaled ones
#             scaled = image.addBands(optical_bands, overwrite=True)
            
#             if apply_mask:
#                 scaled = self._apply_cloud_mask(scaled)
            
#             # Dynamically calculate all requested indices
#             computed_bands = []
#             for name, formula in formulas_to_run.items():
#                 # GEE expression automatically maps b("BandName") to image bands
#                 index_img = scaled.expression(formula).rename(name)
#                 computed_bands.append(index_img)
            
#             final_image = scaled.addBands(computed_bands)
            
#             # Extract mean over AOI
#             mean_dict = final_image.select(list(formulas_to_run.keys())).reduceRegion(
#                 reducer=ee.Reducer.mean(),
#                 geometry=aoi,
#                 scale=10,
#                 maxPixels=1e8
#             )
            
#             # Construct return feature dynamically using the original 'image' for the date
#             properties = {'date': image.date().format('YYYY-MM-dd')}
#             for name in formulas_to_run.keys():
#                 properties[name] = mean_dict.get(name)
                
#             return ee.Feature(None, properties)

#         # Build and run the collection
#         collection = (ee.ImageCollection(self.collection_name)
#                       .filterBounds(aoi)
#                       .filterDate(start_date, end_date)
#                       .map(process_image))
        
#         features = collection.getInfo()['features']
#         df = pd.DataFrame([f['properties'] for f in features])
#         df['date'] = pd.to_datetime(df['date'], errors='coerce')
#         return df.dropna().sort_values(by='date').reset_index(drop=True)