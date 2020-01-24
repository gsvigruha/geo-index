import logging
import math
import shapely
import time


class GeoIndex:
  def __init__(
    self,
    shape_records: list,
    geometry_fn=lambda x: x,
    n_cells_x=100,
    n_cells_y=100):

    self.geometry_fn = geometry_fn
    self.n_cells_x = n_cells_x
    self.n_cells_y = n_cells_y
    self.shape_records = shape_records
    self.index = [[[] for i in range(n_cells_y)] for j in range(n_cells_x)]

    self.left   = min([geometry_fn(sr).bounds[0] for sr in shape_records])
    self.right  = max([geometry_fn(sr).bounds[2] for sr in shape_records]) + 1
    self.bottom = min([geometry_fn(sr).bounds[1] for sr in shape_records])
    self.top    = max([geometry_fn(sr).bounds[3] for sr in shape_records]) + 1

    self.d_w = ((self.right - self.left)   / n_cells_x)
    self.d_h = ((self.top   - self.bottom) / n_cells_y)

    logging.debug(f'Dimensions: left: {self.left} right: {self.right} top: {self.top} bottom: {self.bottom}, d_width: {self.d_w} d_height: {self.d_h}')

    start_time = time.time()
    for sr in self.shape_records:
      g = geometry_fn(sr)
      min_i = math.floor((g.bounds[0] - self.left)   / self.d_w)
      max_i = math.floor((g.bounds[2] - self.left)   / self.d_w)
      min_j = math.floor((g.bounds[1] - self.bottom) / self.d_h)
      max_j = math.floor((g.bounds[3] - self.bottom) / self.d_h)
      for i in range(min_i, max_i + 1):
        for j in range(min_j, max_j + 1):
          box = shapely.geometry.Polygon([
                ((i + 0) * self.d_w + self.left, (j + 0) * self.d_h + self.bottom),
                ((i + 1) * self.d_w + self.left, (j + 0) * self.d_h + self.bottom),
                ((i + 1) * self.d_w + self.left, (j + 1) * self.d_h + self.bottom),
                ((i + 0) * self.d_w + self.left, (j + 1) * self.d_h + self.bottom)
          ])
          if box.intersects(g):
            try:
              self.index[i][j].append(sr)
            except IndexError as e:
              logging.error(e)
              raise e
    logging.debug('Index built in ' + str(time.time() - start_time) + ' sec')
            
    size = 0
    for indexij in self.index:
      for indexi in indexij:
        size = size + len(indexi)
    logging.debug('Number of records: ' + str(len(shape_records)) + ', number of index entries: ' + str(size))


  def min_distance(self, p, max_rad=None):
    return self.nearest_object(p, max_rad)[0]


  def nearest_object(self, p, max_rad=None):
    min_d = None
    min_o = None

    c_i = math.floor((p.x - self.left) / self.d_w)
    c_j = math.floor((p.y - self.bottom) / self.d_h)
    
    if c_i >= 0 and c_i < self.n_cells_x and c_j >= 0 and c_j < self.n_cells_y:
      for sr in self.index[c_i][c_j]:
        dist = p.distance(geometry_fn(sr))
        if min_d is None or min_d > dist:
          min_d = dist
          min_o = sr

    for rad in range(1, max_rad):
      for x in range(0, rad * 2):
        for (i, j) in [(c_i - rad + x, c_j - rad),
                       (c_i + rad, c_j - rad + x),
                       (c_i + rad - x, c_j + rad),
                       (c_i - rad, c_j + rad - x)]:
          if i >= 0 and i < self.n_cells_x and j >= 0 and j < self.n_cells_y:
            for sr in self.index[i][j]:
              dist = p.distance(geometry_fn(sr))
              if min_d is None or min_d > dist:
                min_d = dist
                min_o = sr

      r_w = rad * self.d_w
      r_h = rad * self.d_h
      if min_d is not None and min_d < r_w and min_d < r_h:
        break
    return min_d, min_o


  def object_on_point(self, p):
    c_i = math.floor((p.x - self.left) / self.d_w)
    c_j = math.floor((p.y - self.bottom) / self.d_h)
    if c_i >= 0 and c_i < self.n_cells_x and c_j >= 0 and c_j < self.n_cells_y:
      for sr in self.index[c_i][c_j]:
        if geometry_fn(sr).contains(p):
          return sr
    return None

