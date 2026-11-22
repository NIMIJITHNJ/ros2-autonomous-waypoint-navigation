from glob import glob

from setuptools import find_packages, setup

package_name = 'robot_nav_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/robot_nav_controller/launch',
         glob('launch/*.launch.py')),
        ('share/robot_nav_controller/config',
         glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='nimi',
    maintainer_email='154909952+NIMIJITHNJ@users.noreply.github.com',
    description='Autonomous waypoint navigation controller for ROS 2 and Nav2',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'goal_manager = robot_nav_controller.goal_manager:main',
        ],
    },
)
