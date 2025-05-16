#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

def create_radial_weight_mask(shape, center=None, sigma=None, flat_top_radius=None):
    """
    Create a radial weight mask that gives more weight to the center of the image.
    
    Args:
        shape: Shape of the image (height, width)
        center: Center coordinates (y, x), defaults to the center of the image
        sigma: Standard deviation of the Gaussian weighting, defaults to 1/6 of the shortest dimension
        flat_top_radius: Radius of the flat top center area, defaults to None
    
    Returns:
        2D numpy array with weights (highest at center)
    """
    height, width = shape
    
    if center is None:
        center = (height // 2, width // 2)
    
    if sigma is None:
        sigma = min(height, width) // 6  # Using 1/6 of the shortest dimension
    
    y, x = np.ogrid[:height, :width]
    y_dist = ((y - center[0]) ** 2)
    x_dist = ((x - center[1]) ** 2)
    dist_from_center = np.sqrt(y_dist + x_dist)
    
    # Create Gaussian weight mask (highest at center)
    weight_mask = np.exp(-0.5 * (dist_from_center / sigma) ** 2)
    
    # Create flat top if requested
    if flat_top_radius is not None:
        flat_region = dist_from_center <= flat_top_radius
        weight_mask[flat_region] = 1.0
    
    # Normalize weights to [0, 1]
    weight_mask = weight_mask / weight_mask.max()
    
    return weight_mask 