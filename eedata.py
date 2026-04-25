import ee
import pandas as pd
from datetime import datetime

class GEETimeSeriesExtractor:
    """Handles GEE interactions, cloud masking, and custom index extraction."""
    
    def __init__(self, collection_name="COPERNICUS/S2_SR_HARMONIZED"):
        self.collection_name = collection_name
        # Pre-define some standard formulas so the user doesn't have to memorize them
        self.standard_indices = {
            'NDVI': '(b("B8") - b("B4")) / (b("B8") + b("B4"))',
            'NDTI': '(b("B11") - b("B12")) / (b("B11") + b("B12"))',
            'EVI': '2.5 * ((b("B8") - b("B4")) / (b("B8") + 6 * b("B4") - 7 * b("B2") + 10000))'
        }

    def _apply_cloud_mask(self, image):
        """Standard Sentinel-2 SCL cloud masking."""
        scl = image.select('SCL')
        mask = scl.gt(3).And(scl.lte(7))
        return image.updateMask(mask)

    def extract(self, aoi, start_date, end_date, indices=['NDVI'], custom_formulas=None, apply_mask=True):
        """
        Extracts mean values for requested indices over an AOI.
        indices: List of strings (e.g., ['NDVI', 'NDTI'])
        custom_formulas: Dict of {name: formula} (e.g., {'MY_INDEX': 'b("B8")/b("B3")'})
        """
        formulas_to_run = {}
        
        # Load requested standard indices
        for idx in indices:
            if idx in self.standard_indices:
                formulas_to_run[idx] = self.standard_indices[idx]
        
        # Load any custom user indices
        if custom_formulas:
            formulas_to_run.update(custom_formulas)

        def process_image(image):
            # Apply scaling
            scaled = image.divide(10000).copyProperties(image, ["system:time_start"])
            if apply_mask:
                scaled = self._apply_cloud_mask(scaled)
            
            # Dynamically calculate all requested indices
            computed_bands = []
            for name, formula in formulas_to_run.items():
                # GEE expression automatically maps b("BandName") to image bands
                index_img = scaled.expression(formula).rename(name)
                computed_bands.append(index_img)
            
            final_image = scaled.addBands(computed_bands)
            
            # Extract mean over AOI
            mean_dict = final_image.select(list(formulas_to_run.keys())).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10,
                maxPixels=1e8
            )
            
            # Construct return feature dynamically
            properties = {'date': image.date().format('YYYY-MM-dd')}
            for name in formulas_to_run.keys():
                properties[name] = mean_dict.get(name)
                
            return ee.Feature(None, properties)

        # Build and run the collection
        collection = (ee.ImageCollection(self.collection_name)
                      .filterBounds(aoi)
                      .filterDate(start_date, end_date)
                      .map(process_image))
        
        features = collection.getInfo()['features']
        df = pd.DataFrame([f['properties'] for f in features])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna().sort_values(by='date').reset_index(drop=True)