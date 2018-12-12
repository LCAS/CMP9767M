#!/usr/bin/env python
import rospy
import tf
import math

from std_msgs.msg import Bool
from nav_msgs.msg import OccupancyGrid, Odometry
from simple_move_base import Go_To_Point
from tf.transformations import euler_from_quaternion, quaternion_from_euler

class weed_control():
    map_places = []
    #move_base_commander = Go_To_Point()
    def __init__(self):
	#pubs
	self.spray_pub = rospy.Publisher('/spray', \
					 Bool, \
					 queue_size=10)
	self.find_weeds_pub = rospy.Publisher('/find_weeds', \
					      Bool, \
					      queue_size=10)
	self.go_pub = rospy.Publisher('/find_row', \
				      Bool, queue_size=10)
	#subs
	self.spray_sub = rospy.Subscriber('/spray', \
					  Bool, \
					  self.spray_weeds_call)
	self.find_weeds_sub = rospy.Subscriber('/found_weeds', \
					       Bool, \
					       self.found_weeds_call)
	self.map_sub = rospy.Subscriber('/map', \
					OccupancyGrid,\
					self.create_map_places)
	self.odom_sub = rospy.Subscriber('/thorvald_001/odometry/gazebo', \
					 Odometry, \
					 self.odom_call)
	self.tf_listener = tf.TransformListener()
	self.unfin_path_sub = rospy.Subscriber('/unfinished_path', Bool, self.unfin_path_call)
	self.spray = False
	self.find_weeds = False
	self.ends = False
	self.odom = Odometry()

    def odom_call(self, data):
	self.odom = data

    def create_map_places(self, data): #create searching points in the four corners of the square map
	y_trans = (data.info.height * data.info.resolution)/3
	x_trans = (data.info.width * data.info.resolution)/3
	self.map_places.append([x_trans, y_trans])
	self.map_places.append([x_trans*-1.0, y_trans])
	self.map_places.append([x_trans, y_trans*-1.0])
	self.map_places.append([x_trans*-1.0, y_trans*-1.0])
	self.map_sub.unregister()
	self.search()

    def unfin_path_call(self, data):
	if data.data == True:
		self.go_pub.publish(True)
	elif data.data == False:
		if self.ends == False:
			move_base_commander = Go_To_Point()
			(roll, pitch, yaw) = euler_from_quaternion([self.odom.pose.pose.orientation.x, \
								   self.odom.pose.pose.orientation.y, \
								   self.odom.pose.pose.orientation.z, \
								   self.odom.pose.pose.orientation.w])

			yaw = yaw + math.pi
			if yaw >= (math.pi*2):
				yaw = yaw - (math.pi*2)
			quat = quaternion_from_euler (roll, pitch, yaw)
			go_place = []
			go_place.append(self.odom.pose.pose.position.x)
			go_place.append(self.odom.pose.pose.position.y)
			go_place.append(quat[0])
			go_place.append(quat[1])
			go_place.append(quat[2])
			go_place.append(quat[3])
			success = move_base_commander.point(go_place, 20)
			if success == True:
				self.go_pub.publish(True)
				self.ends = True

		elif self.ends == True:
			self.spray_pub.publish(True)
			self.ends = False

    def found_weeds_call(self, data):
	if data.data == True:
		self.find_weeds_pub.publish(True)
	elif data.data == False:
		self.find_weeds_pub.publish(False)
	
    def spray_weeds_call(self, data):
	if data.data == False:
		self.spray = False #spraying finished
    	
    def search(self):
	if len(self.map_places) == 0:
		return
	x = self.map_places.pop()
	go_place = []
	go_place.append(x[0])
	go_place.append(x[1])
	go_place.append(0)
	go_place.append(0)
	go_place.append(0)
	go_place.append(1)
	move_base_commander = Go_To_Point()
	success = move_base_commander.point(go_place, 120) #go_place = location for sprayer, 120 = time(s) until goal is rejected
	if success == True:
		print "go find row"
		self.go_pub.publish(True) 
	
rospy.init_node('weed_control', anonymous=True)
wc = weed_control()
rospy.spin()

