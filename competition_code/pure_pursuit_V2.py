import numpy as np
import matplotlib.pyplot as plt
import math
import matplotlib.animation as animation
from IPython import display
from matplotlib.animation import FuncAnimation



traj = np.genfromtxt('traj_race_cl_mintime.csv', delimiter=';', skip_header=3)
path1 = traj[:, 1:3]


# helper functions
def pt_to_pt_distance (pt1,pt2):
    distance = np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)
    return distance

# returns -1 if num is negative, 1 otherwise
def sgn (num):
  if num >= 0:
    return 1
  else:
    return -1

# THIS IS DIFFERENT THAN BEFORE! initialize variables here
# you can also change the Kp constant which is located at line 113
currentPos = [-280.4307880, 392.8053185]
currentHeading = 330
lastFoundIndex = 0
lookAheadDis = 2.8
linearVel = 500

# set this to true if you use rotations
using_rotation = False

# this determines how long (how many frames) the animation will run. 400 frames takes around 30 seconds.
numOfFrames = 400

# this function needs to return 3 things in the following order: goalPt, lastFoundIndex, turnVel
# think about this function as a snapshot in a while loop
# given all information about the robot's current state, what should be the goalPt, lastFoundIndex, and turnVel?
# the LFindex takes in the value of lastFoundIndex as input. Looking at it now I can't remember why I have it.
# it is this way because I don't want the global lastFoundIndex to get modified in this function, instead, this function returns the updated lastFoundIndex value 
# this function will be feed into another function for creating animation
def pure_pursuit_step (path, currentPos, currentHeading, lookAheadDis, LFindex) :

  # extract currentX and currentY
  currentX = currentPos[0]
  currentY = currentPos[1]

  # use for loop to search intersections
  lastFoundIndex = LFindex
  intersectFound = False
  startingIndex = lastFoundIndex

  for i in range (startingIndex, len(path)-1):

    # beginning of line-circle intersection code
    x1 = path[i][0] - currentX
    y1 = path[i][1] - currentY
    x2 = path[i+1][0] - currentX
    y2 = path[i+1][1] - currentY
    dx = x2 - x1
    dy = y2 - y1
    dr = math.sqrt (dx**2 + dy**2)
    D = x1*y2 - x2*y1
    discriminant = (lookAheadDis**2) * (dr**2) - D**2

    if discriminant >= 0:
      sol_x1 = (D * dy + sgn(dy) * dx * np.sqrt(discriminant)) / dr**2
      sol_x2 = (D * dy - sgn(dy) * dx * np.sqrt(discriminant)) / dr**2
      sol_y1 = (- D * dx + abs(dy) * np.sqrt(discriminant)) / dr**2
      sol_y2 = (- D * dx - abs(dy) * np.sqrt(discriminant)) / dr**2

      sol_pt1 = [sol_x1 + currentX, sol_y1 + currentY]
      sol_pt2 = [sol_x2 + currentX, sol_y2 + currentY]
      # end of line-circle intersection code

      minX = min(path[i][0], path[i+1][0])
      minY = min(path[i][1], path[i+1][1])
      maxX = max(path[i][0], path[i+1][0])
      maxY = max(path[i][1], path[i+1][1])

      # if one or both of the solutions are in range
      if ((minX <= sol_pt1[0] <= maxX) and (minY <= sol_pt1[1] <= maxY)) or ((minX <= sol_pt2[0] <= maxX) and (minY <= sol_pt2[1] <= maxY)):

        foundIntersection = True

        # if both solutions are in range, check which one is better
        if ((minX <= sol_pt1[0] <= maxX) and (minY <= sol_pt1[1] <= maxY)) and ((minX <= sol_pt2[0] <= maxX) and (minY <= sol_pt2[1] <= maxY)):
          # make the decision by compare the distance between the intersections and the next point in path
          if pt_to_pt_distance(sol_pt1, path[i+1]) < pt_to_pt_distance(sol_pt2, path[i+1]):
            goalPt = sol_pt1
          else:
            goalPt = sol_pt2
        
        # if not both solutions are in range, take the one that's in range
        else:
          # if solution pt1 is in range, set that as goal point
          if (minX <= sol_pt1[0] <= maxX) and (minY <= sol_pt1[1] <= maxY):
            goalPt = sol_pt1
          else:
            goalPt = sol_pt2
          
        # only exit loop if the solution pt found is closer to the next pt in path than the current pos
        if pt_to_pt_distance (goalPt, path[i+1]) < pt_to_pt_distance ([currentX, currentY], path[i+1]):
          # update lastFoundIndex and exit
          lastFoundIndex = i
          break
        else:
          # in case for some reason the robot cannot find intersection in the next path segment, but we also don't want it to go backward
          lastFoundIndex = i+1
        
      # if no solutions are in range
      else:
        foundIntersection = False
        # no new intersection found, potentially deviated from the path
        # follow path[lastFoundIndex]
        goalPt = [path[lastFoundIndex][0], path[lastFoundIndex][1]]

    # if determinant < 0
    else:
      foundIntersection = False
      # no new intersection found, potentially deviated from the path
      # follow path[lastFoundIndex]
      goalPt = [path[lastFoundIndex][0], path[lastFoundIndex][1]]

  # obtained goal point, now compute turn vel
  # initialize proportional controller constant
  Kp = 5

  # calculate absTargetAngle with the atan2 function
  absTargetAngle = math.atan2 (goalPt[1]-currentPos[1], goalPt[0]-currentPos[0]) *180/pi
  if absTargetAngle < 0: absTargetAngle += 360

  # compute turn error by finding the minimum angle
  turnError = absTargetAngle - currentHeading
  if turnError > 180 or turnError < -180 :
    turnError = -1 * sgn(turnError) * (360 - abs(turnError))
  
  # apply proportional controller
  turnVel = Kp*turnError
  
  return goalPt, lastFoundIndex, turnVel

# the code below is for animation
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# for the sake of my sanity
pi = np.pi
# animation
fig = plt.figure()
trajectory_lines = plt.plot([], '-', color='orange', linewidth = 4)
trajectory_line = trajectory_lines[0]
heading_lines = plt.plot([], '-', color='red')
heading_line = heading_lines[0]
connection_lines = plt.plot([], '-', color='green')
connection_line = connection_lines[0]
poses = plt.plot([], 'o', color='black', markersize=10)
pose = poses[0]

# other setup, stationay stuff for example
# plt.plot([initX], [initY], 'x',color='red',markersize=10)
# plt.plot([path1[-1][0]], [path1[-1][1]], 'x',color='red',markersize=10)
pathForGraph = np.array(path1)
plt.plot(pathForGraph[:, 0], pathForGraph[:, 1], '--', color='grey')
# plt.plot(pathForGraph[:, 0], pathForGraph[:, 1], 'o', color='purple', markersize=2)

plt.axis("scaled")
plt.xlim (-750, 1000)
plt.ylim (-1200, 1200)
dt = 50
xs = [currentPos[0]]
ys = [currentPos[1]]

def pure_pursuit_animation (frame) :
  # define globals
  global currentPos
  global currentHeading
  global lastFoundIndex
  global linearVel

  # for the animation to loop
  if lastFoundIndex >= len(path1)-2 : lastFoundIndex = 0

  # call pure_pursuit_step to get info
  goalPt, lastFoundIndex, turnVel = pure_pursuit_step (path1, currentPos, currentHeading, lookAheadDis, lastFoundIndex)

  # model: 200rpm drive with 18" width
  #               rpm   /s  circ   feet
  maxLinVelfeet = 600 / 60 * pi*4 / 12
  #               rpm   /s  center angle   deg
  maxTurnVelDeg = 600 / 60 * pi*4 / 9 *180/pi

  # update x and y, but x and y stays constant here
  stepDis = linearVel/100 * maxLinVelfeet * dt/1000
  currentPos[0] += stepDis * np.cos(currentHeading*pi/180)
  currentPos[1] += stepDis * np.sin(currentHeading*pi/180)

  heading_line.set_data ([currentPos[0], currentPos[0] + 0.5*np.cos(currentHeading/180*pi)], [currentPos[1], currentPos[1] + 0.5*np.sin(currentHeading/180*pi)])
  connection_line.set_data ([currentPos[0], goalPt[0]], [currentPos[1], goalPt[1]])

  currentHeading += turnVel/100 * maxTurnVelDeg * dt/1000
  if using_rotation == False :
    currentHeading = currentHeading%360
    if currentHeading < 0: currentHeading += 360

  # rest of the animation code
  xs.append(currentPos[0])
  ys.append(currentPos[1])

  pose.set_data ((currentPos[0], currentPos[1]))
  trajectory_line.set_data (xs, ys)

anim = FuncAnimation(fig, pure_pursuit_animation, frames = numOfFrames, interval = 50)

# Afficher l'animation
plt.show()