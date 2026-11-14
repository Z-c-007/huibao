export type Coordinate = [number, number]
export interface AreaSelection { coordinates: Coordinate[] }
export function validatePolygon(value: unknown): Coordinate[] {
  if (!Array.isArray(value) || value.length < 4 || value.length > 65) throw new Error('需要3至64个顶点并闭合区域。')
  const points: Coordinate[] = value.map(point => {
    if (!Array.isArray(point) || point.length !== 2 || point.some(v => typeof v !== 'number' || !Number.isFinite(v))) throw new Error('顶点坐标无效。')
    const [x, y] = point as Coordinate
    if (Math.abs(x) > 180 || Math.abs(y) > 90) throw new Error('经纬度超出范围。')
    return [x, y]
  })
  const first = points[0]!, last = points.at(-1)!
  if (first[0] !== last[0] || first[1] !== last[1]) throw new Error('圈选区域必须闭合。')
  if (new Set(points.slice(0, -1).map(p => p.join(','))).size !== points.length - 1) throw new Error('顶点重复，请撤销重复点。')
  if (Math.max(...points.map(p => p[0])) - Math.min(...points.map(p => p[0])) >= 180) throw new Error('暂不支持跨越180度经线。')
  const orient = (a: Coordinate, b: Coordinate, c: Coordinate) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
  const on = (a: Coordinate, b: Coordinate, p: Coordinate) => Math.abs(orient(a, b, p)) < 1e-12 && p[0] >= Math.min(a[0], b[0]) && p[0] <= Math.max(a[0], b[0]) && p[1] >= Math.min(a[1], b[1]) && p[1] <= Math.max(a[1], b[1])
  const count = points.length - 1
  for (let i = 0; i < count; i++) for (let j = i + 1; j < count; j++) {
    if (j === i + 1 || (i === 0 && j === count - 1)) continue
    const a = points[i]!, b = points[i + 1]!, c = points[j]!, d = points[j + 1]!
    if ((orient(a, b, c) * orient(a, b, d) < 0 && orient(c, d, a) * orient(c, d, b) < 0) || on(a, b, c) || on(a, b, d) || on(c, d, a) || on(c, d, b)) throw new Error('边界交叉或接触，请撤销顶点后重新圈选。')
  }
  const area = Math.abs(points.slice(0, -1).reduce((sum, p, i) => sum + p[0] * points[i + 1]![1] - points[i + 1]![0] * p[1], 0)) / 2
  if (area < 1e-10) throw new Error('区域过小或顶点共线，请扩大圈选范围。')
  return points
}
export function closePolygon(points: Coordinate[]): Coordinate[] {
  if (points.length < 3) throw new Error('请至少添加3个顶点后完成圈选。')
  return validatePolygon([...points, [...points[0]!] as Coordinate])
}
