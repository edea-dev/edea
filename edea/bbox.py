"""
Bounding box calculation

SPDX-License-Identifier: EUPL-1.2
"""
from __future__ import annotations

from math import sin, cos, tau

import numpy as np


class BoundingBox:
    """
    BoundingBox for computing the upright 2D bounding box for a set of
    2D coordinates in a (n,2) numpy array.
    You can access the bbox using the
    (min_x, max_x, min_y, max_y) members.
    """

    def __init__(self, points):
        self.max_y = None
        self.min_y = None
        self.max_x = None
        self.min_x = None
        self._valid = None
        self.reset()
        self.envelop(points)

    @staticmethod
    def rot(point, angle):
        """rotate the point at xy by an angle"""
        point_x, point_y = point
        angle_sin, angle_cos = sin(angle), cos(angle)
        x_out = point_x * angle_cos + point_y * angle_sin
        y_out = point_y * angle_cos + point_x * angle_sin
        return [x_out, y_out]

    def envelop(self, points):
        """
        Envelop the existing bounding box with new points
        This might need optimization, we're doing some unnecessary
        math for the sake of programmatic simplicity
        """
        if points is None or len(points) == 0:
            return
        if len(points.shape) != 2 or points.shape[1] != 2:
            raise ValueError(
                f"Points must be a (n,2), array but it has shape {points.shape}"
            )
        if self._valid:
            extended = np.concatenate((points, self.corners))
        else:
            extended = points
        self._valid = True
        self.min_x, self.min_y = np.min(extended, axis=0)
        self.max_x, self.max_y = np.max(extended, axis=0)

    def translate(self, coords):
        """
        move the bounding box by [x y]
        this is used for coordinate system transformation
        """
        if self._valid:
            self.min_x += coords[0]
            self.max_x += coords[0]
            self.min_y += coords[1]
            self.max_y += coords[1]

    def reset(self):
        """reset the BoundingBox"""
        self.min_x, self.min_y = float("inf") * np.array([1, 1], dtype=np.float64)
        self.max_x, self.max_y = float("inf") * np.array([-1, -1], dtype=np.float64)
        self._valid = False

    def rotate(self, angle):
        """
        rotate the box around the origin. angle is in degrees
        """
        if self._valid:
            corners = self.corners
            rotated = np.zeros((4, 2), dtype=np.float64)
            angle = angle / tau
            angle_sin, angle_cos = sin(angle), cos(angle)
            for i, corner in enumerate(corners):
                x_out = corner[0] * angle_cos + corner[1] * angle_sin
                y_out = corner[1] * angle_cos + corner[0] * angle_sin
                rotated[i] = [x_out, y_out]
            self.reset()
            self.envelop(rotated)

    @property
    def corners(self):
        """
        If the bounding box is empty, this returns None.
        Returns all four corners of this rectangle in a [4][2] float64 array
        """
        if self._valid:
            return np.array(
                [
                    [self.min_x, self.min_y],
                    [self.min_x, self.max_y],
                    [self.max_x, self.max_y],
                    [self.max_x, self.min_y],
                ],
                dtype=np.float64,
            )
        return None  # np.array([[]])

    @property
    def valid(self):
        """returns True if the BoundBox has been calculated yet"""
        return self._valid

    @property
    def width(self):
        """X-axis extent of the bounding box"""
        if self._valid:
            return self.max_x - self.min_x

        return 0

    @property
    def height(self):
        """Y-axis extent of the bounding box"""
        if self._valid:
            return self.max_y - self.min_y

        return 0

    @property
    def area(self):
        """width * height"""
        return self.width * self.height

    @property
    def center(self):
        """(x,y) center point of the bounding box"""
        if self._valid:
            return self.min_x + self.width / 2, self.min_y + self.height / 2

        return False  # I don't want to return 0,0

    def __repr__(self):
        if not self._valid:
            return "boundingbox empty"

        val = f"boundingbox([{self.min_x:03.2f}x, {self.min_y:03.2f}y] -> [{self.max_x:03.2f}x, {self.max_y:03.2f}y])"
        return val
