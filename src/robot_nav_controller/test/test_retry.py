from unittest.mock import MagicMock

from action_msgs.msg import GoalStatus
from rclpy.time import Time

from robot_nav_controller.goal_manager import GoalManager


def test_aborted_retries():
    node = MagicMock()
    node.retry_count = 0
    node.max_retries = 2
    node.goal_start = Time(seconds=1)
    node.get_clock.return_value.now.return_value = Time(seconds=2)

    future = MagicMock()
    future.result.return_value.status = GoalStatus.STATUS_ABORTED

    for attempt in (1, 2):
        GoalManager.goal_result(node, future)
        assert node.retry_count == attempt
        assert node.send_next_goal.call_count == attempt

    GoalManager.goal_result(node, future)

    assert node.retry_count == 2
    assert node.send_next_goal.call_count == 2
    node.get_logger.return_value.error.assert_called_once_with(
        'Maximum retries reached. Navigation stopped.'
    )


def test_success_resets_retries():
    node = MagicMock()
    node.retry_count = 2
    node.total_duration = 0.0
    node.waypoint_index = 0
    node.goal_start = Time(seconds=1)
    node.get_clock.return_value.now.return_value = Time(seconds=4)

    future = MagicMock()
    future.result.return_value.status = GoalStatus.STATUS_SUCCEEDED

    GoalManager.goal_result(node, future)

    assert node.retry_count == 0
    assert node.waypoint_index == 1
    assert node.total_duration == 3.0
    node.send_next_goal.assert_called_once_with()


def test_canceled_stops():
    node = MagicMock()
    node.retry_count = 0
    node.waypoint_index = 0
    node.goal_start = Time(seconds=1)
    node.get_clock.return_value.now.return_value = Time(seconds=3)

    future = MagicMock()
    future.result.return_value.status = GoalStatus.STATUS_CANCELED

    GoalManager.goal_result(node, future)

    assert node.retry_count == 0
    assert node.waypoint_index == 0
    node.send_next_goal.assert_not_called()
    node.get_logger.return_value.warning.assert_called_once_with(
        'Navigation cancelled'
    )


def test_rejected_retries():
    node = MagicMock()
    node.retry_count = 0
    node.max_retries = 2

    future = MagicMock()
    future.result.return_value.accepted = False

    for attempt in (1, 2):
        GoalManager.goal_response(node, future)
        assert node.retry_count == attempt
        assert node.send_next_goal.call_count == attempt

    GoalManager.goal_response(node, future)

    assert node.retry_count == 2
    assert node.send_next_goal.call_count == 2
    node.get_logger.return_value.error.assert_called_once_with(
        'Maximum retries reached. Navigation stopped.'
    )


def test_timeout_retries():
    node = MagicMock()
    node.retry_count = 0
    node.max_retries = 2
    node.timeout_requested = True
    node.goal_start = Time(seconds=1)
    node.get_clock.return_value.now.return_value = Time(seconds=65)

    future = MagicMock()
    future.result.return_value.status = GoalStatus.STATUS_CANCELED

    for attempt in (1, 2):
        GoalManager.goal_result(node, future)
        assert node.retry_count == attempt
        assert node.send_next_goal.call_count == attempt

    GoalManager.goal_result(node, future)

    assert node.retry_count == 2
    assert node.send_next_goal.call_count == 2
    node.get_logger.return_value.error.assert_called_once_with(
        'Maximum retries reached. Navigation stopped.'
    )


def test_timeout_detection():
    node = MagicMock()
    node.active_goal = MagicMock()
    node.timeout_requested = False
    node.goal_timeout = 60.0
    node.goal_start = Time(seconds=1)

    node.get_clock.return_value.now.return_value = Time(seconds=60)

    GoalManager.check_timeout(node)

    assert node.timeout_requested is False
    node.active_goal.cancel_goal_async.assert_not_called()

    node.get_clock.return_value.now.return_value = Time(seconds=62)

    GoalManager.check_timeout(node)

    assert node.timeout_requested is True
    node.active_goal.cancel_goal_async.assert_called_once_with()

    GoalManager.check_timeout(node)

    node.active_goal.cancel_goal_async.assert_called_once_with()


def test_result_exception():
    node = MagicMock()
    node.active_goal = MagicMock()

    future = MagicMock()
    future.result.side_effect = RuntimeError('Test failure')

    GoalManager.goal_result(node, future)

    assert node.active_goal is None
    node.send_next_goal.assert_not_called()
    node.get_logger.return_value.error.assert_called_once_with(
        'Navigation failed: Test failure'
    )


def test_server_unavailable():
    node = MagicMock()
    node.server_timeout = 0.1
    node.retry_delay = 2.0
    node.retry_count = 0
    node.max_retries = 2
    node.nav_client.wait_for_server.return_value = False

    GoalManager.send_goal(node, 1.0, 2.0)

    assert node.retry_count == 1
    node.create_timer.assert_called_once_with(
        2.0, node.retry_server
    )


def test_server_retries_exhausted():
    node = MagicMock()
    node.server_timeout = 0.1
    node.retry_count = 2
    node.max_retries = 2
    node.nav_client.wait_for_server.return_value = False

    GoalManager.send_goal(node, 1.0, 2.0)

    assert node.retry_count == 2
    node.create_timer.assert_not_called()
    node.get_logger.return_value.error.assert_any_call(
        'Maximum retries reached. Navigation stopped.'
    )
