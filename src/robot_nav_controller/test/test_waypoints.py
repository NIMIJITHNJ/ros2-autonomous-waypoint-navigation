import pytest

from robot_nav_controller.goal_manager import parse_waypoints


def test_valid_waypoints():
    coordinates = [-0.3625, 1.6780, 0.7508, -1.4771]

    result = parse_waypoints(coordinates)

    assert result == [
        (-0.3625, 1.6780),
        (0.7508, -1.4771)
    ]


def test_incomplete_waypoints():
    coordinates = [1.0, 2.0, 3.0]

    with pytest.raises(ValueError, match='complete'):
        parse_waypoints(coordinates)


def test_nonfinite_waypoints():
    coordinates = [1.0, float('inf')]

    with pytest.raises(ValueError, match='finite'):
        parse_waypoints(coordinates)


def test_empty_waypoints():
    coordinates = []

    with pytest.raises(ValueError, match='complete'):
        parse_waypoints(coordinates)
