"""Bounded simple polygon validation for user-drawn map regions."""
import math


def validate_ring(value):
    if not isinstance(value, list) or not 4 <= len(value) <= 65:
        raise ValueError("圈选区域需要3至64个顶点，并闭合首尾坐标")
    points = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("每个顶点必须包含经度和纬度")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point):
            raise ValueError("顶点必须使用有限数值")
        x, y = map(float, point)
        if not -180 <= x <= 180 or not -90 <= y <= 90:
            raise ValueError("经纬度超出有效范围")
        points.append([x, y])
    if points[0] != points[-1] or len({tuple(p) for p in points[:-1]}) != len(points) - 1:
        raise ValueError("区域必须闭合，且不能有重复顶点")
    if max(p[0] for p in points) - min(p[0] for p in points) >= 180:
        raise ValueError("暂不支持跨越180度经线的圈选区域")

    def orientation(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_segment(a, b, p):
        return (abs(orientation(a, b, p)) < 1e-12
                and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))

    count = len(points) - 1
    for i in range(count):
        a, b = points[i], points[i + 1]
        for j in range(i + 1, count):
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            c, d = points[j], points[j + 1]
            crossed = (orientation(a, b, c) * orientation(a, b, d) < 0
                       and orientation(c, d, a) * orientation(c, d, b) < 0)
            if crossed or any((on_segment(a, b, c), on_segment(a, b, d), on_segment(c, d, a), on_segment(c, d, b))):
                raise ValueError("圈选边界不能交叉或相互接触，请重新圈选")
    area = abs(sum(points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1] for i in range(count))) / 2
    if area < 1e-10:
        raise ValueError("圈选区域过小或顶点共线，请扩大范围")
    return points
