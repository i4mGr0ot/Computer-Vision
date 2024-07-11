from . import utils
from . import exceptions
import os
import cv2
import time

def stitch_images(image_folder, image_filenames, stitch_direction):

    num_images = len(image_filenames)
    
    if num_images < 2:
        raise(exceptions.InsufficientImagesError(num_images))
    
    valid_files, file_error_msg = utils.check_imgfile_validity(image_folder, image_filenames)
    if not valid_files:
        raise(exceptions.InvalidImageFilesError(file_error_msg))
    
    pivot_img_path = os.path.join(image_folder, image_filenames[0])
    pivot_img = cv2.imread(pivot_img_path)

    for i in range(1, num_images, 1):
        join_img_path = os.path.join(image_folder, image_filenames[i])
        join_img = cv2.imread(join_img_path)
        pivot_img = utils.stitch_image_pair(pivot_img, join_img, stitch_direc=stitch_direction)
    
    return pivot_img

def stitch_images_and_save(image_folder, image_filenames, stitch_direction, output_folder=None):

    timestr = time.strftime("%Y%m%d_%H%M%S")
    filename = "stitched_image_" + timestr + ".jpg"
    stitched_img = stitch_images(image_folder, image_filenames, stitch_direction)
    if output_folder is None:
        if not os.path.isdir("output"):
            os.makedirs("output/")
        output_folder = "output"
    full_save_path = os.path.join(output_folder, filename)
    _ = cv2.imwrite(full_save_path, stitched_img)
    print("The stitched image is saved at: " + full_save_path)
