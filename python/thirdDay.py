import asyncio
import time


def parse_line_sync(line, delay):
    time.sleep(delay)
    return line.strip()


async def parse_line_async(line, delay):
    await asyncio.sleep(delay)
    return line.strip()
def run_sync(lines):
    start = time.perf_counter()
    results = [parse_line_sync(line, 1) for line in lines]
    elapsed = time.perf_counter() - start
    print(f"同步: 处理 {len(lines)} 行耗时 {elapsed:.2f} 秒")
    return results


async def run_async(lines):
    start = time.perf_counter()
    results = await asyncio.gather(*[parse_line_async(line, 1) for line in lines])
    elapsed = time.perf_counter() - start
    print(f"异步: 处理 {len(lines)} 行耗时 {elapsed:.2f} 秒")
    return results
def main():
    lines = [
        "通州某制造企业，本月用水 12000 吨，预算 10000 吨",
        "朝阳某餐饮企业，本月用水 3000 吨，预算 4000 吨",
        "海淀某医院，本月用水 8000 吨，预算 9000 吨",
        "大兴某制造企业，本月用水 15000 吨，预算 20000 吨",
    ]

    run_sync(lines)

    asyncio.run(run_async(lines))


if __name__ == "__main__":
    main()