#!/usr/bin/env python
import sys
import time
import numpy as np

import rospy
import image_geometry
import roslib
import tf

import cv2
from cv_bridge import CvBridge

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped


class image_converter:
    camera_model = None
    weeds = []

    def __init__(self):

        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber('/thorvald_001/kinect2_camera/hd/image_color_rect',
                                          Image, self.callback)
	self.camera_info_sub = rospy.Subscriber('/thorvald_001/kinect2_camera/hd/camera_info', 
            				  CameraInfo, self.camera_info_callback)
	self.tf_listener = tf.TransformListener()

    def camera_info_callback(self, data): #get camera info once
	self.camera_model = image_geometry.PinholeCameraModel()
        self.camera_model.fromCameraInfo(data)
        self.camera_info_sub.unregister()

    def callback(self, data):
	if not self.camera_model:
            return
	k = self.weeding(data)
	self.coords(k)
	
	(trans, rot) = self.tf_listener.lookupTransform('map', 
            'thorvald_001/kinect2_rgb_optical_frame', rospy.Time())

	try:
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)

	for x in range(len(self.weeds)):
		p_robotz = PoseStamped()
		p_robotz.header.frame_id = "map"
		p_robotz.pose.orientation.w = 1.0
		p_robotz.pose.position.x = self.weeds[x][0]
		p_robotz.pose.position.y = self.weeds[x][1]
		p_robotz.pose.position.z = 0
		p_camera = self.tf_listener.transformPose('thorvald_001/kinect2_rgb_optical_frame', p_robotz)

		uv = self.camera_model.project3dToPixel((p_camera.pose.position.x,p_camera.pose.position.y,p_camera.pose.position.z))

		cv2.circle(cv_image, (int(uv[0]),int(uv[1])), 10, 255, -1)
	
        #resize for visualisation
        cv_image_s = cv2.resize(cv_image, (0,0), fx=0.5, fy=0.5)

        cv2.imshow("Image window", cv_image_s)
        cv2.waitKey(1)
		
     	
    def coords(self, XY_pixel_list): #https://answers.ros.org/question/241624/converting-pixel-location-in-camera-frame-to-world-frame/

	(trans, rot) = self.tf_listener.lookupTransform('map', 
            'thorvald_001/kinect2_rgb_optical_frame', rospy.Time())

	weed_coords = []
	
	for z in range(len(XY_pixel_list)):	
		ray = self.camera_model.projectPixelTo3dRay((XY_pixel_list[z][0],XY_pixel_list[z][1]))

		p_point = PoseStamped()
		p_point.header.frame_id = 'thorvald_001/kinect2_rgb_optical_frame'
		p_point.pose.orientation.w = 1.0
		p_point.pose.position.x = ray[0]
		p_point.pose.position.y = ray[1]
		p_point.pose.position.z = ray[2]
		p_test = self.tf_listener.transformPose('map', p_point)

		vector = [p_test.pose.position.x - trans[0],
		  	  p_test.pose.position.y - trans[1],
		  	  p_test.pose.position.z - trans[2]]

		vector_n = []
		for c in range(3):
			vector_n.append(vector[c] / ((vector[0]*vector[0])+(vector[1]*vector[1])+(vector[2]*vector[2]))**.5)
	
		change_mag = (0.0 - p_test.pose.position.z)/vector_n[2]
		inter_vec = [p_test.pose.position.x + (vector_n[0]*change_mag),p_test.pose.position.y + (vector_n[1]*change_mag),0]

		weed_coords.append((inter_vec[0], inter_vec[1]))
	if len(self.weeds) == 0:
		for x in range(len(weed_coords)):
			self.weeds.append(weed_coords[x])
	for x in range(len(weed_coords)):
		for y in range(len(self.weeds)):
			if weed_coords[x][0] < (self.weeds[y][0]+0.25) and \
			   weed_coords[x][0] > (self.weeds[y][0]-0.25) and \
			   weed_coords[x][1] < (self.weeds[y][1]+0.25) and \
			   weed_coords[x][1] > (self.weeds[y][1]-0.25):
				break
			elif y == len(self.weeds)-1:
				self.weeds.append(weed_coords[x])
   
    def weeding(self, data): #weed finding in camera image

	#set up hsv image from camera sub
        cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        
	#set mask
        lower_green = np.array([40,20,20])
        upper_green = np.array([80,255,255])        
        image_mask = cv2.inRange(hsv, lower_green, upper_green)  
        #erode and open the image to split up plants
        kernel = np.ones((5,5),np.uint8)
        erosion = cv2.erode(image_mask,kernel,iterations = 3)
        opening = cv2.morphologyEx(erosion, cv2.MORPH_OPEN, kernel)
	#find the contours in the image
	_, contours, hierarchy = cv2.findContours(opening, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
	
	plants = []
	#check if a contour looks like a weed by getting a value of area/peri to get a rough idea of shape (looking for plants with large areas vs perimeters
	for c in contours:
		peri = cv2.arcLength(c, True)
		area = cv2.contourArea(c)
		if ((area / peri) >= 17.0):
			plants.append(c)

	plant_cXY = []
	#for each of the weeds find the center point to use for co-ordinates
	for c in plants: #https://www.learnopencv.com/find-center-of-blob-centroid-using-opencv-cpp-python/
		M = cv2.moments(c)
		if M["m00"] != 0:
 			cX = int(M["m10"] / M["m00"])
 			cY = int(M["m01"] / M["m00"])
			plant_cXY.append([cX,cY])
		else:
 			cX, cY = 0, 0
		#cv2.putText(cv_image, "weed", (cX - 25, cY - 25),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 255), 2)
	return plant_cXY
	
        """
        https://stackoverflow.com/questions/37745274/opencv-find-perimeter-of-a-connected-component
        https://stackoverflow.com/questions/35854197/how-to-use-opencvs-connected-components-with-stats-in-python
        https://stackoverflow.com/questions/42798659/how-to-remove-small-connected-objects-using-opencv/42812226
        https://stackoverflow.com/questions/46441893/connected-component-labeling-in-python?rq=1
        """             
cv2.startWindowThread()
rospy.init_node('image_converter')
ic = image_converter()
rospy.spin()

cv2.destroyAllWindows()
