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

class Sentinal2TimeSeriesExtractor:
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


class LandsatTimeSeriesExtractor:
    """Handles Landsat 8/9 GEE interactions, bitwise masking, and harmonization."""
    
    def __init__(self, sensors=['LC08', 'LC09']):
        """
        sensors: List containing 'LC08' (Landsat 8), 'LC09' (Landsat 9), or both for fusion.
        """
        self.sensors = sensors
        
        # We keep the exact same Sentinel-style formulas because we will rename the Landsat bands!
        self.standard_indices = {
            'NDVI': '(b("B8") - b("B4")) / (b("B8") + b("B4"))',
            'NDTI': '(b("B11") - b("B12")) / (b("B11") + b("B12"))',
            'EVI': '2.5 * ((b("B8") - b("B4")) / (b("B8") + 6 * b("B4") - 7 * b("B2") + 10000))'
        }
        
        self._reducer_map = {
            'mean': ee.Reducer.mean(),
            'median': ee.Reducer.median(),
            'max': ee.Reducer.max(),
            'min': ee.Reducer.min(),
            'sum': ee.Reducer.sum()
        }

        # Mapping Landsat Collection 2 SR bands to Sentinel-2 naming convention
        self.band_map = {
            'SR_B2': 'B2',   # Blue
            'SR_B3': 'B3',   # Green
            'SR_B4': 'B4',   # Red
            'SR_B5': 'B8',   # NIR
            'SR_B6': 'B11',  # SWIR 1
            'SR_B7': 'B12'   # SWIR 2
        }

    def _apply_cloud_mask(self, image):
        """Scientifically robust bitwise cloud masking for Landsat Collection 2 QA_PIXEL."""
        qa = image.select('QA_PIXEL')
        
        # Landsat QA_PIXEL Bit Layout:
        # Bit 1: Dilated Cloud, Bit 3: Cloud, Bit 4: Cloud Shadow
        cloud_shadow_bit_mask = (1 << 4)
        clouds_bit_mask = (1 << 3)
        dilated_cloud_bit_mask = (1 << 1)
        
        # A pixel is clear if ALL of these bits are 0
        mask = qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0) \
            .And(qa.bitwiseAnd(clouds_bit_mask).eq(0)) \
            .And(qa.bitwiseAnd(dilated_cloud_bit_mask).eq(0))
            
        return image.updateMask(mask)

    def extract(self, aoi, start_date, end_date, reducer=Reducer.mean, indices=['NDVI'], custom_formulas=None, apply_mask=True, **reduce_kwargs):
        """Extracts and fuses data from requested Landsat sensors."""
        formulas_to_run = {}
        
        for idx in indices:
            if idx in self.standard_indices:
                formulas_to_run[idx] = self.standard_indices[idx]
        
        if custom_formulas:
            formulas_to_run.update(custom_formulas)
            
        reducer_key = reducer.value if isinstance(reducer, Enum) else str(reducer).lower()
        selected_gee_reducer = self._reducer_map.get(reducer_key, ee.Reducer.mean())

        def process_image(image):
            # 1. Apply mask first using the QA_PIXEL band
            if apply_mask:
                image = self._apply_cloud_mask(image)
                
            # 2. Extract and rigorously scale ONLY the optical SR bands
            # Landsat Collection 2 SR scaling formula: (Band * 0.0000275) - 0.2
            optical_bands = image.select(list(self.band_map.keys())) \
                                 .multiply(0.0000275).add(-0.2)
            
            # 3. HARMONIZATION: Rename Landsat bands to Sentinel-2 names
            harmonized_bands = optical_bands.select(list(self.band_map.keys()), 
                                                    list(self.band_map.values()))
            
            computed_bands = []
            for name, formula in formulas_to_run.items():
                index_img = harmonized_bands.expression(formula).rename(name)
                computed_bands.append(index_img)
            
            final_image = harmonized_bands.addBands(computed_bands)
            
            region_params = {
                'reducer': selected_gee_reducer,
                'geometry': aoi,
                'scale': 30,       # Landsat native resolution is 30m
                'maxPixels': 1e8 
            }
            region_params.update(reduce_kwargs)
            
            mean_dict = final_image.select(list(formulas_to_run.keys())).reduceRegion(**region_params)
            
            properties = {'date': image.date().format('YYYY-MM-dd')}
            for name in formulas_to_run.keys():
                properties[name] = mean_dict.get(name)
                
            return ee.Feature(None, properties)

        # 4. DYNAMIC FUSION: Create and merge collections based on user request
        collections = []
        for sensor in self.sensors:
            col = ee.ImageCollection(f"LANDSAT/{sensor}/C02/T1_L2") \
                    .filterBounds(aoi) \
                    .filterDate(start_date, end_date) \
                    .map(process_image)
            collections.append(col)
            
        # Merge all requested collections into one massive, dense time-series
        fused_collection = collections[0]
        for col in collections[1:]:
            fused_collection = fused_collection.merge(col)
        
        # Execute the fetch
        features = fused_collection.getInfo()['features']
        df = pd.DataFrame([f['properties'] for f in features])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna().sort_values(by='date').reset_index(drop=True)
    


class Sentinel1TimeSeriesExtractor:
    """Handles Sentinel-1 SAR extraction, dB/linear conversion, and dynamic speckle filtering."""
    
    def __init__(self, orbit_pass='DESCENDING'):
        self.collection_name = "COPERNICUS/S1_GRD"
        self.orbit_pass = orbit_pass
        
        # Formulas MUST be written for LINEAR scale data.
        self.standard_indices = {
            'RVI': '(4 * b("VH")) / (b("VV") + b("VH"))',
            'Ratio_VV_VH': 'b("VV") / b("VH")' # Linear ratio (equivalent to VV(dB) - VH(dB))
        }

    def _db_to_linear(self, image):
        """Converts dB to linear power: 10^(dB/10)."""
        # Select only SAR bands (VV, VH, etc.), ignore angle bands for the math
        sar_bands = image.select(['VV', 'VH'])
        linear = ee.Image(10.0).pow(sar_bands.divide(10.0))
        return image.addBands(linear, overwrite=True)

    def _linear_to_db(self, image):
        """Converts linear power back to dB: 10 * log10(Linear)."""
        sar_bands = image.select(['VV', 'VH'])
        db = ee.Image(10.0).multiply(sar_bands.log10())
        return image.addBands(db, overwrite=True)

    def extract(self, aoi, start_date, end_date, reducer=ee.Reducer.mean(), 
                indices=['RVI'], custom_formulas=None, filter_func=None, **reduce_kwargs):
        """
        filter_func: A callable function from SpeckleFilter (e.g., SpeckleFilter.lee)
        """
        formulas_to_run = {}
        for idx in indices:
            if idx in self.standard_indices:
                formulas_to_run[idx] = self.standard_indices[idx]
        if custom_formulas:
            formulas_to_run.update(custom_formulas)

        # def process_image(image):
        #     # 1. Convert to Linear Scale BEFORE filtering
        #     linear_image = self._db_to_linear(image)
            
        #     # 2. Apply Dynamic Speckle Filter (if provided)
        #     if filter_func is not None:
        #         linear_image = filter_func(linear_image)
            
        #     # 3. Calculate custom indices on the filtered linear data
        #     computed_bands = []
        #     for name, formula in formulas_to_run.items():
        #         index_img = linear_image.expression(formula).rename(name)
        #         computed_bands.append(index_img)
            
        #     # 4. Optional: Convert core bands back to dB for output, but append linear indices
        #     final_image = self._linear_to_db(linear_image).addBands(computed_bands)
            
        #     # 5. Extract using reduceRegion
        #     bands_to_extract = ['VV', 'VH'] + list(formulas_to_run.keys())
        #     region_params = {
        #         'reducer': reducer,
        #         'geometry': aoi,
        #         'scale': 10,
        #         'maxPixels': 1e8
        #     }
        #     region_params.update(reduce_kwargs)
            
        #     mean_dict = final_image.select(bands_to_extract).reduceRegion(**region_params)
            
        #     properties = {'date': image.date().format('YYYY-MM-dd')}
        #     for b in bands_to_extract:
        #         properties[b] = mean_dict.get(b)
                
        #     return ee.Feature(None, properties)
        def process_image(image):
            # 1. Convert to Linear Scale BEFORE filtering
            linear_image = self._db_to_linear(image)
            
            # 2. Apply Dynamic Speckle Filter (if provided)
            if filter_func is not None:
                linear_image = filter_func(linear_image)
            
            # --- THE FIX: Explicitly cast back to ee.Image ---
            # This ensures that whether the filter returned an Image or an Element,
            # GEE treats it as an Image moving forward.
            linear_image = ee.Image(linear_image)
            # -------------------------------------------------
            
            # 3. Calculate custom indices on the filtered linear data
            computed_bands = []
            for name, formula in formulas_to_run.items():
                index_img = linear_image.expression(formula).rename(name)
                computed_bands.append(index_img)
            
            # 4. Optional: Convert core bands back to dB for output, but append linear indices
            final_image = self._linear_to_db(linear_image).addBands(computed_bands)
            
            # 5. Extract using reduceRegion
            bands_to_extract = ['VV', 'VH'] + list(formulas_to_run.keys())
            region_params = {
                'reducer': reducer,
                'geometry': aoi,
                'scale': 10,
                'maxPixels': 1e8
            }
            region_params.update(reduce_kwargs)
            
            mean_dict = final_image.select(bands_to_extract).reduceRegion(**region_params)
            
            properties = {'date': image.date().format('YYYY-MM-dd')}
            for b in bands_to_extract:
                properties[b] = mean_dict.get(b)
                
            return ee.Feature(None, properties)
        # Build S1 specific collection
        collection = (ee.ImageCollection(self.collection_name)
                      .filterBounds(aoi)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.eq('instrumentMode', 'IW'))
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                      .filter(ee.Filter.eq('orbitProperties_pass', self.orbit_pass))
                      .map(process_image))
        
        features = collection.getInfo()['features']
        df = pd.DataFrame([f['properties'] for f in features])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna().sort_values(by='date').reset_index(drop=True)