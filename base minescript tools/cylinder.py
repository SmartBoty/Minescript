# SPDX-FileCopyrightText: © 2022 Greg Christiana <maxuser@minescript.net>
# SPDX-License-Identifier: MIT

r"""cylinder v1 distributed via minescript.net

Usage:
  \cylinder X Y Z RADIUS HEIGHT BLOCK_TYPE

Builds the lateral surface of a cylinder with a base circle
centered at location (X, Y, Z) with radius RADIUS, height
HEIGHT, made of BLOCK_TYPE.

Example:
  Creates a cylinder centered at the player's current
  location, with radius 20 blocks, 5 blocks high, made from
  blocks of yellow concrete:

  \cylinder ~ ~ ~ 20 5 yellow_concrete
"""

import math
import sys

def create_circle(r):
  """
  Args:
    r: radius (int)
  Returns:
    set of (x, z) coords along circumference of a circle
  """
  surface = set()
  for arc in range(round(2 * math.pi * r)):
    theta = arc / r
    x = round(r * math.cos(theta))
    z = round(r * math.sin(theta))
    surface.add((x, z))
  return surface

def run(args):
  x_origin = int(eval(args[1]))
  y_origin = int(eval(args[2]))
  z_origin = int(eval(args[3]))

  r = int(args[4])
  h = int(args[5])
  block = args[6]

  surface = create_circle(r)
  num_blocks = len(surface) * h
  blocks_placed = 0
  for sx, sz in surface:
    x = sx + x_origin
    z = sz + z_origin
    rest = "" if len(args) < 8 else f" {' '.join(args[7:])}"
    print(f"/fill {x} {y_origin} {z} {x} {y_origin + h} {z} {block}{rest}")
    blocks_placed += h
    print(f"Blocks placed: {blocks_placed} of {num_blocks}", file=sys.stderr)
  print(f"Created cylinder surface with {num_blocks} blocks.", file=sys.stderr)

if __name__ == "__main__":
  run(sys.argv)
