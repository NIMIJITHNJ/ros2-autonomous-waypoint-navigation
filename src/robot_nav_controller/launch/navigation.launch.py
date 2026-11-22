import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory(
        'robot_nav_controller'
    )

    config = os.path.join(
        package_dir, 'config', 'controller.yaml'
    )

    return LaunchDescription([
        Node(
            package='robot_nav_controller',
            executable='goal_manager',
            name='goal_manager',
            output='screen',
            parameters=[config]
        )
    ])
