import json
text = "通州某制造企业，本月用水 12000 吨，预算 10000 吨"
industry_map = {"制造": "制造业", "餐饮": "餐饮业", "医院": "医疗业"}
industry = None
for key , value in industry_map.items():
    if key in text:
        industry = value
        print(industry)
        break
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
water_used = extract_number(text, "用水")
budget = extract_number(text, "预算")
result = {"industry": industry, "water_used": water_used, "budget": budget}

print(result)
print(json.dumps(result, ensure_ascii=False))