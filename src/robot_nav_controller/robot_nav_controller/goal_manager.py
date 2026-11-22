import math

from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node


def parse_waypoints(coordinates):
    if not coordinates or len(coordinates) % 2 != 0:
        raise ValueError(
            'waypoint_coordinates must contain complete (x, y) pairs'
        )

    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError(
            'waypoint_coordinates must contain finite numeric values'
        )

    return [
        (coordinates[i], coordinates[i + 1])
        for i in range(0, len(coordinates), 2)
    ]


class GoalManager(Node):
    def __init__(self):
        super().__init__('goal_manager')
        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose'
        )

        self.declare_parameter(
            'waypoint_coordinates',
            [-0.3625, 1.6780, 0.7508, -1.4771, -2.0, -0.5]
        )

        self.declare_parameter('max_retries', 2)
        self.declare_parameter('goal_timeout', 60.0)
        self.declare_parameter('server_timeout', 5.0)
        self.declare_parameter('retry_delay', 2.0)

        coordinates = self.get_parameter('waypoint_coordinates').value
        self.waypoints = parse_waypoints(coordinates)
        self.waypoint_index = 0
        self.total_duration = 0.0
        self.retry_count = 0
        self.max_retries = self.get_parameter('max_retries').value
        self.goal_timeout = self.get_parameter('goal_timeout').value
        self.server_timeout = self.get_parameter('server_timeout').value
        self.retry_delay = self.get_parameter('retry_delay').value

        if (self.max_retries < 0 or self.goal_timeout <= 0
                or self.server_timeout <= 0 or self.retry_delay <= 0):
            raise ValueError('Invalid navigation configuration')

        self.retry_timer = None
        self.goal_attempts = 0
        self.active_goal = None
        self.timeout_requested = False
        self.timeout_timer = self.create_timer(
            0.5,
            self.check_timeout
        )

        self.get_logger().info('Goal manager node started')

    def send_next_goal(self):
        if self.waypoint_index >= len(self.waypoints):
            self.get_logger().info('All waypoints completed')
            self.get_logger().info(
                f'Completed waypoints: {self.waypoint_index}'
            )
            self.get_logger().info(
                f'Goal submissions: {self.goal_attempts}'
            )
            self.get_logger().info(
                f'Average waypoint time: '
                f'{self.total_duration / len(self.waypoints):.2f} seconds'
            )
            self.get_logger().info(
                f'Total navigation time: {self.total_duration:.2f} seconds'
            )
            return

        x, y = self.waypoints[self.waypoint_index]

        self.get_logger().info(
            f'Navigating to waypoint {self.waypoint_index + 1}/{len(self.waypoints)}'
        )

        self.send_goal(x, y)

    def send_goal(self, x, y):
        if not self.nav_client.wait_for_server(
            timeout_sec=self.server_timeout
        ):
            self.get_logger().error('Navigation server unavailable')

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.get_logger().warning(
                    f'Retrying server: {self.retry_count}/{self.max_retries}'
                )
                self.retry_timer = self.create_timer(
                    self.retry_delay, self.retry_server
                )
            else:
                self.get_logger().error(
                    'Maximum retries reached. Navigation stopped.'
                )
            return

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.w = 1.0

        try:
            self.goal_future = self.nav_client.send_goal_async(
                goal,
                feedback_callback=self.goal_feedback
            )
            self.goal_attempts += 1
            self.goal_future.add_done_callback(self.goal_response)
        except Exception as exc:
            self.get_logger().error(f'Unable to send goal: {exc}')
            return
        self.get_logger().info(f'Navigation requested: ({x}, {y})')

    def retry_server(self):
        timer = self.retry_timer
        self.retry_timer = None
        timer.cancel()
        self.destroy_timer(timer)
        self.send_next_goal()

    def goal_response(self, future):
        try:
            goal_handle = future.result()
        except Exception as exc:
            self.get_logger().error(f'Goal request failed: {exc}')
            return

        if not goal_handle.accepted:
            self.get_logger().warning('Navigation goal rejected')

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.get_logger().warning(
                    f'Retrying waypoint: attempt {self.retry_count}/{self.max_retries}'
                )
                self.send_next_goal()
            else:
                self.get_logger().error(
                    'Maximum retries reached. Navigation stopped.'
                )
            return

        self.get_logger().info('Navigation goal accepted')
        self.active_goal = goal_handle
        self.timeout_requested = False
        self.goal_start = self.get_clock().now()

        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.goal_result)

    def goal_result(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.active_goal = None
            self.get_logger().error(f'Navigation failed: {exc}')
            return

        self.active_goal = None

        duration = (
            self.get_clock().now() - self.goal_start
        ).nanoseconds / 1e9

        self.get_logger().info(
            f'Navigation duration: {duration:.2f} seconds'
        )

        if response.status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Destination reached successfully')
            self.total_duration += duration
            self.retry_count = 0
            self.waypoint_index += 1
            self.send_next_goal()

        elif response.status == GoalStatus.STATUS_ABORTED:
            self.get_logger().warning('Navigation aborted')

            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.get_logger().warning(
                    f'Retrying waypoint: attempt {self.retry_count}/{self.max_retries}'
                )
                self.send_next_goal()
            else:
                self.get_logger().error(
                    'Maximum retries reached. Navigation stopped.'
                )

        elif response.status == GoalStatus.STATUS_CANCELED:
            if self.timeout_requested is True:
                self.get_logger().warning('Navigation cancelled due to timeout')

                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    self.get_logger().warning(
                        f'Retrying waypoint: attempt {self.retry_count}/{self.max_retries}'
                    )
                    self.send_next_goal()
                else:
                    self.get_logger().error(
                        'Maximum retries reached. Navigation stopped.'
                    )
            else:
                self.get_logger().warning('Navigation cancelled')

        else:
            self.get_logger().warning(
                f'Navigation status: {response.status}'
            )

    def goal_feedback(self, feedback_msg):
        feedback = feedback_msg.feedback
        distance = feedback.distance_remaining
        self.get_logger().info(
            f'Distance remaining: {distance:.2f} m',
            throttle_duration_sec=1.0
        )

    def check_timeout(self):
        if self.active_goal is None or self.timeout_requested:
            return

        elapsed = (
            self.get_clock().now() - self.goal_start
        ).nanoseconds / 1e9

        if elapsed >= self.goal_timeout:
            self.timeout_requested = True
            self.get_logger().warning(
                f'Navigation timeout after {elapsed:.2f} seconds'
            )
            self.cancel_future = self.active_goal.cancel_goal_async()


def main(args=None):
    rclpy.init(args=args)
    node = GoalManager()
    node.send_next_goal()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
