#!/usr/bin/env python

import rospy
from cv2 import namedWindow, cvtColor, imshow
from cv2 import destroyAllWindows, startWindowThread
from cv2 import waitKey
from cv2 import blur, Canny, threshold, THRESH_BINARY, split
from numpy import ones, uint8
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class image_converter:

    def __init__(self):

        self.bridge = CvBridge()
        #initialising subscriber
        self.image_sub = rospy.Subscriber("/thorvald_001/kinect2_camera/hd/image_color_rect",
                                          Image, self.callback)
        #initialising kernel for closing operation                                   
        self.kernel = ones((5,5), uint8)                                  

    def callback(self, data):
        namedWindow("Image window")

        cv_img = self.bridge.imgmsg_to_cv2(data, "bgr8")
        b,g,r = split(cv_img)        
        
        ret, carrots = threshold(g, 50, 255, THRESH_BINARY)

        imshow("Image window", carrots)
                
        
        waitKey(1)

startWindowThread()
rospy.init_node('image_converter')
ic = image_converter()
rospy.spin()

destroyAllWindows()