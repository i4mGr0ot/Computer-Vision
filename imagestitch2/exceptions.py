class InsufficientImagesError(Exception):

    def __init__(self, num_images):
        msg = "Expected 2 or more images but got only " +  str(num_images)
        super(InsufficientImagesError, self).__init__(msg)


class InvalidImageFilesError(Exception):

    def __init__(self, msg):
        super(InvalidImageFilesError, self).__init__(msg)


class NotEnoughMatchPointsError(Exception):

    def __init__(self, num_match_points, min_match_points_req):
        msg = "There are not enough match points between images in the input images. Required atleast " + \
               str(min_match_points_req) + " matches but could find only " + str(num_match_points) + " matches!"
        super(NotEnoughMatchPointsError, self).__init__(msg)


class MatchesNotConfident(Exception):

    def __init__(self, confidence):
        msg = "The confidence in the matches is less than the defined threshold and hence the stitching operation \
        cannot be performed. Perhaps the input images have very less overlapping content to detect good match points!"
        super(MatchesNotConfident, self).__init__(msg + " Confidence: " + str(confidence))
