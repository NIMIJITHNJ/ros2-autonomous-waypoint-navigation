# Third-Party Notices

## Navigation2 (Nav2)

The file `config/nav2_params.yaml` was adapted from the
Navigation2 `nav2_bringup` example configuration.

Source:
https://github.com/ros-navigation/navigation2/blob/main/nav2_bringup/params/nav2_params.yaml

The `nav2_bringup` package is distributed under Apache-2.0.
This project uses Nav2 for underlying robot navigation and
implements a separate high-level waypoint management controller.

## Customised TurtleBot3 Model

The file `custom_models/gz_waffle_blue.sdf.xacro` is adapted from
the `nav2_minimal_tb3_sim` package.

Source:
https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation

Licence: Apache-2.0

Modification: Changed the robot body's visual material to blue.
The original collision geometry, sensors and physics are unchanged.
The model references mesh assets from the installed ROS 2 package.
