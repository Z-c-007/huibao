"""审计日志：jsonl 追加写入，含耗时。"""
import json
from datetime import datetime

from ..core.config import AUDIT_PATH


def audit(fn_name, args, result, elapsed_ms):
    """记录一次工具调用的完整痕迹（谁、带什么参数、成没成、花了多久）"""
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "tool": fn_name,
        "args": args,
        "ok": result.get("ok"),
        "error_type": result.get("error_type"),
        "elapsed_ms": elapsed_ms,
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")