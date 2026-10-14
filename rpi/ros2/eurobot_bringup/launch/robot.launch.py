"""Pokretanje celog robota: ros2 launch eurobot_bringup robot.launch.py

Cvorovi se dodaju ovde kako nastaju (nucleo_bridge, pico_bridge, lidar, strategija).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import LogInfo


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory("eurobot_bringup"), "config", "robot.yaml"
    )
    return LaunchDescription([
        LogInfo(msg=f"eurobot_bringup: parametri iz {params}"),
        # Primer kada nucleo_bridge bude spreman:
        # Node(package="nucleo_bridge", executable="nucleo_bridge_node",
        #      parameters=[params], output="screen"),
    ])
