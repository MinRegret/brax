# Copyright 2021 The Brax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for brax.physics."""

from absl.testing import absltest
from absl.testing import parameterized
from jax import numpy as jnp
import brax
from brax.physics import math
from brax.physics.base import take
from google.protobuf import text_format


class BodyTest(absltest.TestCase):

  def test_projectile_motion(self):
    """A ball with an initial velocity curves down due to gravity."""
    sys = brax.System(
        text_format.Parse(
            """
    dt: 1 substeps: 1000
    gravity { z: -9.8 }
    bodies { name: "Ball" mass: 1 }
    """, brax.Config()))
    qp = brax.QP(
        pos=jnp.array([[0., 0., 0.]]),
        rot=jnp.array([[1., 0., 0., 0.]]),
        vel=jnp.array([[1., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    # v = v_0 + a * t
    self.assertAlmostEqual(qp.vel[0, 2], -9.8, 2)
    # x = x_0 + v_0 * t + 0.5 * a * t^2
    self.assertAlmostEqual(qp.pos[0, 0], 1, 2)
    self.assertAlmostEqual(qp.pos[0, 2], -9.8 / 2, 2)


class BoxTest(absltest.TestCase):

  _CONFIG = """
    dt: 1.5 substeps: 1000 friction: 0.6 baumgarte_erp: 0.1
    gravity { z: -9.8 }
    bodies {
      name: "Torso" mass: 1
      colliders { box { halfsize { x: 0.5 y: 0.5 z: 0.5 }}}
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Ground" frozen: { all: true } colliders { plane {}}}
  """

  def test_box_hits_ground(self):
    """A box falls onto the ground and stops."""
    sys = brax.System(text_format.Parse(BoxTest._CONFIG, brax.Config()))
    qp = brax.QP(
        pos=jnp.array([[0., 0., 1.], [0, 0, 0]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., 0., 0.], [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    self.assertAlmostEqual(qp.pos[0, 2], 0.5, 2)

  def test_box_slide(self):
    """A box slides across the ground and comes to a stop."""
    sys = brax.System(text_format.Parse(BoxTest._CONFIG, brax.Config()))
    qp = brax.QP(
        pos=jnp.array([[0., 0., 2.], [0, 0, 0]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[2., 0., 0.], [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    self.assertAlmostEqual(qp.pos[0, 2], 0.5, 2)
    self.assertAlmostEqual(qp.vel[0, 0], 0, 2)  # friction brings it to a stop
    self.assertLess(qp.pos[0, 0], 1.5)  # ... and keeps it from travelling 2m


class CapsuleTest(absltest.TestCase):

  _CONFIG = """
    dt: 5 substeps: 5000 friction: 0.6 baumgarte_erp: 0.1
    gravity { z: -9.8 }
    bodies {
      name: "Capsule1" mass: 1
      colliders { capsule { radius: 0.25 length: 1.0 }}
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies {
      name: "Capsule2" mass: 1
      colliders { rotation { y: 90 } capsule { radius: 0.25 length: 1.0 }}
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies {
      name: "Capsule3" mass: 1
      colliders { rotation { y: 45 } capsule { radius: 0.25 length: 1.0 }}
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies {
      name: "Capsule4" mass: 1
      colliders { rotation { x: 45 } capsule { radius: 0.25 length: 1.0 }}
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Ground" frozen: { all: true } colliders { plane {}}}
  """

  def test_capsule_hits_ground(self):
    """A capsule falls onto the ground and stops."""
    sys = brax.System(text_format.Parse(CapsuleTest._CONFIG, brax.Config()))
    qp = brax.QP(
        pos=jnp.array([[0., 0., 1.], [1., 0., 1.], [3., 0., 1.], [5., 0., 1.],
                       [0, 0, 0]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.], [1., 0., 0., 0.],
                       [1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                       [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                       [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    self.assertAlmostEqual(qp.pos[0, 2], 0.5, 2)  # standing up and down
    self.assertAlmostEqual(qp.pos[1, 2], 0.25, 2)  # lying on its side
    self.assertAlmostEqual(qp.pos[2, 2], 0.25, 2)  # rolls to side from y rot
    self.assertAlmostEqual(qp.pos[3, 2], 0.25, 2)  # rolls to side from x rot

  def test_capsule_hits_capsule(self):
    """A capsule falls onto another capsule and balances on it."""
    sys = brax.System(text_format.Parse(CapsuleTest._CONFIG, brax.Config()))
    qp = brax.QP(
        pos=jnp.array([[0., 0., 1.], [0., 0., 2.], [3., 0., 1.], [5., 0., 1.],
                       [0, 0, 0]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.], [1., 0., 0., 0.],
                       [1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                       [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                       [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    self.assertAlmostEqual(qp.pos[0, 2], 0.5, 2)  # standing up and down
    self.assertAlmostEqual(qp.pos[1, 2], 1.25, 2)  # lying on Capsule1


class JointTest(parameterized.TestCase):

  _CONFIG = """
    substeps: 100000
    gravity { z: -9.8 }
    bodies {
      name: "Anchor" frozen: { all: true } mass: 1
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Bob" }
    joints {
      name: "Joint" parent: "Anchor" child: "Bob" stiffness: 10000
      child_offset { z: 1 }
      angle_limit { min: -180 max: 180 }
    }
  """

  @parameterized.parameters((2.0, 0.125, 0.0625), (5.0, 0.125, 0.03125),
                            (1.0, 0.0625, 0.1))
  def test_pendulum_period(self, mass, radius, vel):
    """A small spherical mass swings for approximately one period."""
    config = text_format.Parse(JointTest._CONFIG, brax.Config())

    # this length of time comes from the following:
    # inertia_about_anchor = mass * dist_to_anchor^2 + inertia_cm
    # dist_to_anchor = 1.0
    # inertia_cm = 2/5 * mass * radius^2 (solid sphere)
    # T = 2 * pi * sqrt(inertia_about_anchor / (2 * mass * g * dist_to_anchor))
    config.dt = float(2 * jnp.pi * jnp.sqrt((.4 * radius**2 + 1.) / 9.8))
    config.bodies[1].mass = mass
    config.bodies[1].inertia.x = .4 * mass * radius**2
    config.bodies[1].inertia.y = .4 * mass * radius**2
    config.bodies[1].inertia.z = .4 * mass * radius**2
    sys = brax.System(config)

    # initializing system to have a small initial velocity and ang velocity
    # so that small angle approximation is valid
    qp = brax.QP(
        pos=jnp.array([[0., 0., -1.], [0., 0., 0.]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., vel, 0.], [0., 0., 0.]]),
        ang=jnp.array([[.5 * vel, 0., 0.], [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([]))
    self.assertAlmostEqual(qp.pos[0, 1], 0., 3)  # returned to the origin


class Actuator1DTest(parameterized.TestCase):

  _CONFIG = """
    substeps: 1200
    dt: 4.0
    gravity { z: -9.8 }
    bodies {
      name: "Anchor" frozen: { all: true } mass: 1
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Bob" mass: 1
      inertia { x: 1 y: 1 z: 1 }}
    joints {
      name: "Joint" parent: "Anchor" child: "Bob" stiffness: 10000
      child_offset { z: 1 }
      angle_limit { min: -180 max: 180 }
      angular_damping: 140.0
      }
    actuators {
    name: "Joint"
    joint: "Joint"
    strength: 15000.0
    angle {}
    }
"""

  @parameterized.parameters(15., 30., 45., 90.)
  def test_1d_angle_actuator(self, target_angle):
    """A simple part actuates to a target angle."""
    config = text_format.Parse(Actuator1DTest._CONFIG, brax.Config())
    sys = brax.System(config=config)
    qp = brax.QP(
        pos=jnp.array([[0., 0., 2.], [0., 0., 1.]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., 0., 0.], [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([target_angle]))
    joint = sys.joint_revolute
    qp_p = brax.physics.base.take(qp, 0)
    qp_c = brax.physics.base.take(qp, 1)
    axis_p = brax.physics.math.rotate(joint.axis_1.reshape(-1), qp_p.rot)
    axis_c = brax.physics.math.rotate(joint.axis_1.reshape(-1), qp_c.rot)
    final_angle = brax.physics.math.signed_angle(qp_p, qp_c,
                                                   ((axis_p + axis_c) / 2.),
                                                   joint.ref.reshape(-1))

    self.assertAlmostEqual(target_angle * jnp.pi / 180., final_angle,
                           2)  # actuated to target angle (in radians)


class Actuator2DTest(parameterized.TestCase):

  _CONFIG = """
  substeps: 2000
    dt: 2.0
    gravity { z: -9.8 }
    bodies {
      name: "Anchor" frozen: { all: true } mass: 1
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Bob" mass: 1
      inertia { x: 1 y: 1 z: 1 }
    colliders {
      capsule {
        radius: 0.5
        length: 2.0
      }
      }
    }
    joints {
      name: "Joint" parent: "Anchor" child: "Bob" stiffness: 10000
      child_offset { z: 1 }
      angle_limit {
        min: -180
        max: 180
      }
      angle_limit {
        min: -180
        max: 180
      }
      angular_damping: 200.0
      }
    actuators {
    name: "Joint"
    joint: "Joint"
    strength: 2000.0
    angle {}
    }
"""

  @parameterized.parameters((15., 30.), (45., 90.5), (-120, 60.), (30., -120.),
                            (-150, -130), (130, 165))
  def test_2d_angle_actuator(self, target_angle_1, target_angle_2):
    """A simple part actuates 2d-angle actuator to two target angles."""
    config = text_format.Parse(Actuator2DTest._CONFIG, brax.Config())
    sys = brax.System(config=config)
    qp = brax.QP(
        pos=jnp.array([[0., 0., 2.], [0., 0., 1.]]),
        rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
        vel=jnp.array([[0., 0., 0.], [0., 0., 0.]]),
        ang=jnp.array([[0., 0., 0.], [0., 0., 0.]]))
    qp, _ = sys.step(qp, jnp.array([target_angle_1, target_angle_2]))
    joint = sys.joint_universal
    qp_p = brax.physics.base.take(qp, 0)
    qp_c = brax.physics.base.take(qp, 1)
    axis_c = brax.physics.math.rotate(joint.axis_1.reshape(-1), qp_c.rot)
    axis_2_p = brax.physics.math.rotate(joint.axis_2.reshape(-1), qp_p.rot)
    ref_c = brax.physics.math.rotate(joint.ref.reshape(-1), qp_c.rot)
    child_in_plane = jnp.cross(axis_2_p, axis_c)
    angle_1 = brax.physics.math.signed_angle(qp_p, qp_c, axis_2_p,
                                               joint.ref.reshape(-1))
    angle_2 = jnp.arctan2(
        jnp.dot(jnp.cross(child_in_plane, ref_c), axis_c),
        jnp.dot(child_in_plane, ref_c))

    self.assertAlmostEqual(target_angle_1 * jnp.pi / 180., angle_1,
                           2)  # actuated to target angle 1 (in radians)
    self.assertAlmostEqual(target_angle_2 * jnp.pi / 180., angle_2,
                           2)  # actuated to target angle 2 (in radians)


class Actuator3DTest(parameterized.TestCase):

  _CONFIG = """
    substeps: 8
    dt: .02
    bodies {
      name: "Anchor" frozen: { all: true } mass: 1
      inertia { x: 1 y: 1 z: 1 }
    }
    bodies { name: "Bob" mass: 1
      inertia { x: 1 y: 1 z: 1 }
    colliders {
      capsule {
        radius: 0.5
        length: 2.0
      }
      }
    }
    joints {
      name: "Joint" parent: "Anchor" child: "Bob" stiffness: 10000
      child_offset { z: 1 }
      angle_limit {
        min: -100
        max: 100
      }
      angle_limit {
        min: -100
        max: 100
      }
      angle_limit {
        min: -100
        max: 100
      }
      angular_damping: 120.0
      }
    actuators {
    name: "Joint"
    joint: "Joint"
    strength: 40.0
    torque {}
    }
  """
  torques = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)]

  @parameterized.parameters(((15, 15, 15), torques), ((35, 40, 75), torques),
                            ((80, 45, 30), torques))
  def test_3d_torque_actuator(self, limits, torques):
    """A simple part actuates 3d-torque actuator to its limits."""
    config = text_format.Parse(Actuator3DTest._CONFIG, brax.Config())
    for t in torques:
      for angle_limit, limit in zip(config.joints[0].angle_limit, limits):
        angle_limit.min = -limit
        angle_limit.max = limit

      sys = brax.System(config=config)
      qp = brax.QP(
          pos=jnp.array([[0., 0., 2.], [0., 0., 1.]]),
          rot=jnp.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
          vel=jnp.array([[0., 0., 0.], [0., 0., 0.]]),
          ang=jnp.array([[0., 0., 0.], [0., 0., 0.]]))

      # cuts down compile time for test to only compile a short step
      for _ in range(1000):
        qp, _ = sys.step(qp, jnp.array(t))

      qp_p = take(qp, 0)
      qp_c = take(qp, 1)

      axis_1 = math.rotate(sys.joint_spherical.axis_1[0], qp_p.rot)
      axis_2 = math.rotate(sys.joint_spherical.axis_2[0], qp_p.rot)
      axis_3 = math.rotate(sys.joint_spherical.axis_3[0], qp_p.rot)

      axis_1_c = math.rotate(sys.joint_spherical.axis_1[0], qp_c.rot)
      axis_2_c = math.rotate(sys.joint_spherical.axis_2[0], qp_c.rot)
      axis_3_c = math.rotate(sys.joint_spherical.axis_3[0], qp_c.rot)

      axis_2_in_plane = axis_2_c - jnp.dot(axis_2_c, axis_3) * axis_3
      axis_2_in_projected_length = jnp.linalg.norm(axis_2_in_plane)
      axis_2_in_plane = axis_2_in_plane / (1e-7 +
                                           jnp.linalg.norm(axis_2_in_plane))

      angle_1 = jnp.arctan2(
          jnp.dot(axis_2_in_plane, axis_1), jnp.dot(axis_2_in_plane, axis_2))

      angle_2 = -1. * jnp.arctan2(
          jnp.dot(axis_2_c, axis_3), axis_2_in_projected_length)

      axis_3_in_child_xz = axis_3 - jnp.dot(axis_3, axis_2_c) * axis_2_c

      angle_3 = jnp.arctan2(
          jnp.dot(
              axis_3_in_child_xz -
              jnp.dot(axis_3_in_child_xz, axis_3_c) * axis_3_c, axis_1_c),
          jnp.dot(
              axis_3_in_child_xz -
              jnp.dot(axis_3_in_child_xz, axis_1_c) * axis_1_c, axis_3_c))

      scale = 360. / (2 * jnp.pi)
      final_angles = [angle_1 * scale, angle_2 * scale, angle_3 * scale]
      for final_angle, limit, torque in zip(final_angles, limits, t):
        if torque != 0:
          self.assertAlmostEqual(final_angle, limit,
                                 1)  # actuated to target angle (in degrees)


if __name__ == '__main__':
  absltest.main()
