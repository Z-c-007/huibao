import json
from pathlib import Path

def extract_number(s, keyword):
    idx = s.find(keyword)
    if idx == -1:
        return None
    start = idx + len(keyword)
    num_str = ""
    for ch in s[start:]:
        if ch.isdigit():
            num_str += ch
        elif num_str:
            break
    return int(num_str)
def parse_line(line):
    line = line.strip()
    if not line:
        raise ValueError("空行")

    industry_map = {"制造": "制造业", "餐饮": "餐饮业", "医院": "医疗业"}
    industry = None
    for key, value in industry_map.items():
        if key in line:
            industry = value
            break

    water_used = extract_number(line, "用水")
    budget = extract_number(line, "预算")
    if water_used is None or budget is None:
        raise ValueError(f"缺少用水或预算字段: {line}")

    return {"industry": industry, "water_used": water_used, "budget": budget}
def main():
    src = Path("data/water_users.txt")
    text = src.read_text(encoding="utf-8")

    results = []
    for i, line in enumerate(text.splitlines(), start=1):
        try:
            results.append(parse_line(line))
        except Exception as e:
            print(f"[跳过] 第{i}行解析失败: {e}")

    out = Path("data/result.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    back = json.loads(out.read_text(encoding="utf-8"))
    print("读回验证:", len(back), "条")


if __name__ == "__main__":
    main()