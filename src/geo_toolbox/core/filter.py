import ee

class SpeckleFilter:
    """A collection of reusable SAR speckle filters. Images MUST be in linear scale."""
    
    @staticmethod
    def boxcar(image, radius=3):
        """Simple focal mean (Boxcar) filter."""
        return image.focal_mean(radius, 'square', 'pixels').copyProperties(image)
    
    @staticmethod
    def lee(image, radius=3):
        """Simple boxcar filter for speckle reduction (placeholder for full Lee filter)."""
        sar_bands = ['VV', 'VH']
        sar_image = image.select(sar_bands)
        
        # Apply simple focal mean (boxcar) filter
        filtered_sar = sar_image.focal_mean(radius, 'square', 'pixels')
        
        # Add back other bands unchanged
        other_bands = image.bandNames().removeAll(sar_bands)
        if other_bands.length().gt(0):
            other_image = image.select(other_bands)
            filtered = filtered_sar.addBands(other_image)
        else:
            filtered = filtered_sar
        
        return filtered.copyProperties(image, ["system:time_start"])


    @staticmethod
    def refined_lee(image):
        """
        Standard 7x7 Refined Lee speckle filter for SAR data in linear scale.
        Preserves edges by detecting 8 directional gradients.
        """
        band_names = image.bandNames()

        def apply_to_band(b):
            img = image.select([b])

            # 1. Set up 3x3 kernels
            weights3 = ee.List.repeat(ee.List.repeat(1, 3), 3)
            kernel3 = ee.Kernel.fixed(3, 3, weights3, 1, 1, False)
            mean3 = img.reduceNeighborhood(ee.Reducer.mean(), kernel3)
            variance3 = img.reduceNeighborhood(ee.Reducer.variance(), kernel3)

            # 2. Use a sample of the 3x3 windows inside a 7x7 window to determine gradients
            sample_weights = ee.List([
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 1, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 1, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 1, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0]
            ])
            sample_kernel = ee.Kernel.fixed(7, 7, sample_weights, 3, 3, False)

            # Calculate mean and variance for the sampled windows and store as 9 bands
            sample_mean = mean3.neighborhoodToBands(sample_kernel)
            sample_var = variance3.neighborhoodToBands(sample_kernel)

            # Determine the 4 gradients for the sampled windows
            gradients = sample_mean.select(1).subtract(sample_mean.select(7)).abs()
            gradients = gradients.addBands(sample_mean.select(6).subtract(sample_mean.select(2)).abs())
            gradients = gradients.addBands(sample_mean.select(3).subtract(sample_mean.select(5)).abs())
            gradients = gradients.addBands(sample_mean.select(0).subtract(sample_mean.select(8)).abs())

            # Find the maximum gradient amongst gradient bands
            max_gradient = gradients.reduce(ee.Reducer.max())

            # Create a mask for band pixels that are the maximum gradient
            gradmask = gradients.eq(max_gradient)
            gradmask = gradmask.addBands(gradmask)

            # Determine the 8 directions
            directions = sample_mean.select(1).subtract(sample_mean.select(4)).gt(
                sample_mean.select(4).subtract(sample_mean.select(7))).multiply(1)
            directions = directions.addBands(sample_mean.select(6).subtract(sample_mean.select(4)).gt(
                sample_mean.select(4).subtract(sample_mean.select(2))).multiply(2))
            directions = directions.addBands(sample_mean.select(3).subtract(sample_mean.select(4)).gt(
                sample_mean.select(4).subtract(sample_mean.select(5))).multiply(3))
            directions = directions.addBands(sample_mean.select(0).subtract(sample_mean.select(4)).gt(
                sample_mean.select(4).subtract(sample_mean.select(8))).multiply(4))

            # The next 4 are the inverse of the previous 4
            directions = directions.addBands((directions.select(0).Not()).multiply(5))
            directions = directions.addBands((directions.select(1).Not()).multiply(6))
            directions = directions.addBands((directions.select(2).Not()).multiply(7))
            directions = directions.addBands((directions.select(3).Not()).multiply(8))

            # Mask all values that are not 1-8
            directions = directions.updateMask(gradmask)
            directions = directions.reduce(ee.Reducer.sum())
            sample_stats = sample_var.divide(sample_mean.multiply(sample_mean))

            # Calculate localNoiseVariance (sigmaV)
            sigmaV = (sample_stats.toArray()
                      .arraySort()
                      .arraySlice(0, 0, 5)
                      .arrayReduce(ee.Reducer.mean(), [0]))

            # Set up the 7x7 kernels for directional statistics
            rect_weights = ee.List.repeat(ee.List.repeat(0, 7), 3).cat(ee.List.repeat(ee.List.repeat(1, 7), 4))
            diag_weights = ee.List([
                [1, 0, 0, 0, 0, 0, 0],
                [1, 1, 0, 0, 0, 0, 0],
                [1, 1, 1, 0, 0, 0, 0],
                [1, 1, 1, 1, 0, 0, 0],
                [1, 1, 1, 1, 1, 0, 0],
                [1, 1, 1, 1, 1, 1, 0],
                [1, 1, 1, 1, 1, 1, 1]
            ])
            rect_kernel = ee.Kernel.fixed(7, 7, rect_weights, 3, 3, False)
            diag_kernel = ee.Kernel.fixed(7, 7, diag_weights, 3, 3, False)

            # Create stacks for mean and variance using the original kernels
            dir_mean = img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel).updateMask(directions.eq(1))
            dir_var = img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel).updateMask(directions.eq(1))
            dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel).updateMask(directions.eq(2)))
            dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel).updateMask(directions.eq(2)))

            # Add the bands for rotated kernels
            for i in range(1, 4):
                dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
                dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
                dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))
                dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))

            dir_mean = dir_mean.reduce(ee.Reducer.sum())
            dir_var = dir_var.reduce(ee.Reducer.sum())

            # Generate the filtered value
            varX = dir_var.subtract(dir_mean.multiply(dir_mean).multiply(sigmaV)).divide(sigmaV.add(1.0))
            b = varX.divide(dir_var)

            filtered = dir_mean.add(b.multiply(img.subtract(dir_mean)))
            
            # Project, flatten, and cast back to float to match GEE standard formats
            return filtered.arrayProject([0]).arrayFlatten([["sum"]]).float()

        # Map the complex filter over every band in the image and combine them back
        filtered_image_collection = ee.ImageCollection(band_names.map(apply_to_band))
        final_image = filtered_image_collection.toBands().rename(band_names)
        
        # Copy properties (like system:time_start) from original image so the time-series extractor doesn't break
        return final_image.copyProperties(image, image.propertyNames())
    
@staticmethod
    def gamma_map(image, radius=3, enl=4.4):
        """
        Gamma MAP (Maximum A Posteriori) speckle filter for SAR data in linear scale.
        Assumes the intensity and reflectivity follow a Gamma distribution.
        
        radius: Kernel radius in pixels (3 = 7x7 window).
        enl: Equivalent Number of Looks (4.4 is standard for Sentinel-1 GRD IW).
        """
        kernel = ee.Kernel.square(radius, 'pixels')

        # 1. Calculate local mean and standard deviation
        reducer = ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True)
        stats = image.reduceNeighborhood(reducer=reducer, kernel=kernel)

        band_names = image.bandNames()
        mean_bands = band_names.map(lambda b: ee.String(b).cat('_mean'))
        std_bands = band_names.map(lambda b: ee.String(b).cat('_stdDev'))

        mean = stats.select(mean_bands).rename(band_names)
        std = stats.select(std_bands).rename(band_names)

        # 2. Calculate Coefficients of Variation
        ci = std.divide(mean)  # Local variation (sigma / mean)
        ci2 = ci.pow(2)

        cu = 1.0 / (enl ** 0.5)  # Noise variation coefficient
        cu2 = cu ** 2
        cmax = (2.0 ** 0.5) * cu # Maximum variation threshold (approx 1.414 * cu)

        # 3. Calculate Gamma MAP equation parameters for the textured regime
        alpha = ee.Image(1.0).add(cu2).divide(ci2.subtract(cu2))
        b = alpha.subtract(enl).add(1.0)

        # Discriminant: (B * mean)^2 + 4 * alpha * ENL * mean * I
        d = mean.pow(2).multiply(b.pow(2)).add(
            alpha.multiply(image).multiply(mean).multiply(4.0 * enl)
        )

        # MAP Estimate: (B * mean + sqrt(Discriminant)) / (2 * alpha)
        map_filtered = b.multiply(mean).add(d.sqrt()).divide(alpha.multiply(2.0))

        # 4. Pixel-wise Conditional Routing
        # Start with the MAP estimate as the base
        filtered = map_filtered

        # Overwrite with local mean if it's a homogeneous area
        filtered = filtered.where(ci.lte(cu), mean)

        # Overwrite with the original raw pixel if it's a sharp edge or point target
        filtered = filtered.where(ci.gte(cmax), image)

        # 5. Return with properties preserved
        return filtered.copyProperties(image, image.propertyNames())