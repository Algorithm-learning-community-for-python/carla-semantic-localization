""" Implements world-to-ego transformations. """

# %%
# The following boilerplate is required if .egg is not installed
# See: https://carla.readthedocs.io/en/latest/build_system/
import glob
import os
import sys

try:
    sys.path.append(glob.glob('./carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import numpy as np
from scipy.spatial.transform import Rotation


class CarlaW2ETform:
    """ 
    Helper class to perform world-to-ego transformation for Carla. 
    
    Carla provides only an API to transform a location from ego to world frame.
    This class complements the transfromation abilities from world to ego frame.

    Important note:
     Carla (Unreal Engine) uses:
     - Left-handed coordinate system for locations (x-forward, y-rightward, z-up)
     - Right-handed z-down coordinate (airplane like) coordinate system for rotations (roll-pitch-yaw)

    This class automatically converts given carla.Transform and carla.Location so the transformation results
    will be in our right-handed z-up coordinate system convention.
    """

    def __init__(self, ego_transform: carla.Transform):
        """ 
        Constructor method using lazy initialization. 
        
        Input:
            ego_transform: Carla.Transform object of ego frame.
        """
        self._ego_veh_transform = ego_transform
        # rotation matrix to transform a vector from world frame to ego frame
        self._rotm_w2e = None
        # homogeneous transformation matrix to transform a vector from world frame to ego frame
        self._tform_w2e = None

    def rotm_world_to_ego(self, vector3D: carla.Vector3D):
        """ 
        Rotationally transform the given carla.Vector3D in ego frame to world frame.

        Note the return np 3D vector already follows the right-handed z-up coordinate system.

        Input:
            vector3D: Carla.Vector3D which follows carla's coordinate system (z-down system).
        Output:
            Numpy.array representing a 3D coordinate in the right-handed z-up coordinate system.
        """
        if self._rotm_w2e is None:
            self._init_rotm_w2e()
        # Need to convert from left-handed to right-handed before apply the rotation
        np_vec = np.array([vector3D.x, -vector3D.y, vector3D.z]).T
        return self._rotm_w2e.dot(np_vec)

    def tform_world_to_ego(self, vector3D: carla.Vector3D):
        """ 
        Homogeneous transform the given carla.Vector3D in ego frame to world frame.

        Note the return np 3D vector already follows right-handed z-up coordinate system.

        Input:
            vector3D: Carla.Vector3D which follows carla's coordinate system (z-down system).
        Output:
            Numpy.array representing a 3D coordinate in the right-handed z-up coordinate system.
        """
        if self._tform_w2e is None:
            self._init_tform_w2e()
        # Need to convert from left-handed to right-handed before apply the homogeneous transformation
        np_homo_vec = np.array([vector3D.x, -vector3D.y, vector3D.z, 1])
        return self._tform_w2e.dot(np_homo_vec)[0:3]
        

    def _init_rotm_w2e(self):
        """ Helper method to create rotation matrix _rotm_e2w. """
        rotation = self._ego_veh_transform.rotation
        # Need to convert from right-handed z-down to right-handed z-down system when building up the rotation matrix
        # Transpose so it is the rotation of the world frame wrt the ego frame
        self._rotm_w2e = Rotation.from_euler(
            'zyx', [-rotation.yaw, -rotation.pitch, rotation.roll], degrees=True).as_matrix().T

    def _init_tform_w2e(self):
        """ Helper method to create rotation matrix _tform_e2w. """
        if self._rotm_w2e is None:
            self._init_rotm_w2e()
        self._tform_w2e = np.zeros((4, 4), dtype=np.float)
        self._tform_w2e[3, 3] = 1
        self._tform_w2e[0:3, 0:3] = self._rotm_w2e
        trvec = np.array([self._ego_veh_transform.location.x,
                          -self._ego_veh_transform.location.y, 
                          -self._ego_veh_transform.location.z]).T
        self._tform_w2e[0:3, 3] = - self._rotm_w2e.dot(trvec)
