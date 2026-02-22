import cv2
import numpy as np
import os

def deskew_image(image: np.ndarray) -> np.ndarray:
    # Invert image to find coordinates of non-background pixels
    inv = cv2.bitwise_not(image)
    coords = np.column_stack(np.where(inv > 0))
    
    if len(coords) == 0:
        return image
        
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Limit angle correction to avoid dramatic flips if detection is wrong
    if abs(angle) > 15:
         return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def denoise_image(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

def binarize_image(image: np.ndarray) -> np.ndarray:
    # Adaptive thresholding works well for documents with varying lighting
    return cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

def preprocess_image(file_path: str) -> str:
    """
    Reads an image, applies preprocessing (grayscale, deskew, denoise, binarize),
    and saves the preprocessed image with a prefix. Returns the new file path.
    """
    # Force read as grayscale
    image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        # File is either not an image or corrupted - skip preprocessing
        return file_path
        
    deskewed = deskew_image(image)
    denoised = denoise_image(deskewed)
    binarized = binarize_image(denoised)
    
    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    new_path = os.path.join(dir_name, "preprocessed_" + base_name)
    
    cv2.imwrite(new_path, binarized)
    return new_path
