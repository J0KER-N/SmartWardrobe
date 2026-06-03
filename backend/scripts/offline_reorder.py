import json
import os
import random

# 创建示例反馈数据集 (JSON)
def generate_sample_feedbacks(filepath: str):
    """
    生成用户的历史反馈数据。
    包含 `like`, `save`, `click`, `view` 事件。
    """
    events = ["like", "save", "click", "view"]
    # 假设我们有一些候选穿搭或衣物，ID 为 'item_1' 到 'item_10'
    feedbacks = []
    
    # 模拟 user_1 偏好 item_1, item_3, 以及 category 为 "休闲" 的单品
    for i in range(1, 11):
        item_id = f"item_{i}"
        
        # 为了演示，令 item_1 和 item_3 拥有更多的高优事件
        if i in [1, 3]:
            # 制造像是 like 和 save 这样的强正向反馈
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "like"})
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "save"})
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "click"})
        elif i in [2, 4]:
            # 一般事件
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "click"})
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "view"})
        else:
            # 弱事件
            feedbacks.append({"user_id": 1, "item_id": item_id, "event_type": "view"})

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=4)
    print(f"✅ 生成示例反馈数据集至 {filepath}")


def load_feedbacks(filepath: str) -> list:
    if not os.path.exists(filepath):
        generate_sample_feedbacks(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def offline_reorder(user_id: int, candidates: list, feedbacks: list) -> list:
    """
    根据历史反馈进行离线候选重排。
    
    事件权重配置：
    - like: 5.0
    - save: 4.0
    - click: 2.0
    - view: 1.0
    
    基于 item_id 匹配历史反馈。
    """
    event_weights = {
        "like": 5.0,
        "save": 4.0,
        "click": 2.0,
        "view": 1.0,
    }

    # 聚合针对各件物品的反馈得分
    item_scores = {}
    for fb in feedbacks:
        if fb["user_id"] == user_id:
            i_id = fb["item_id"]
            e_type = fb["event_type"]
            score = event_weights.get(e_type, 0.0)
            item_scores[i_id] = item_scores.get(i_id, 0.0) + score

    # 计算最终得分：原始排序基础分(base_score) + 反馈增益分
    # 模拟每个候选项的基础分为 [0.5, 0.9] 之间的随机值
    scored_candidates = []
    for item in candidates:
        base_score = item.get("base_score", 0.5)
        item_id = item["item_id"]
        
        # 也可以做归一化，这里简单加法演示
        feedback_gain = item_scores.get(item_id, 0.0) * 0.1  # 降权叠加
        final_score = base_score + feedback_gain
        scored_candidates.append({
            "item_id": item_id,
            "base_score": base_score,
            "feedback_gain": feedback_gain,
            "final_score": final_score
        })

    # 根据 final_score 降序排列
    scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return scored_candidates


def main():
    dataset_path = "sample_feedbacks.json"
    generate_sample_feedbacks(dataset_path)
    
    feedbacks = load_feedbacks(dataset_path)
    
    # 预设的推荐候选集，仅基于基础推荐算法得出的打分
    candidates = []
    for i in range(1, 11):
        # 假设基础检索模型推荐的基础分数分布
        candidates.append({
            "item_id": f"item_{i}",
            "base_score": round(random.uniform(0.5, 0.9), 2)
        })
    
    print("\n--- 初始候选集（按基础检索打分排序） ---")
    candidates_sorted_base = sorted(candidates, key=lambda x: x["base_score"], reverse=True)
    for c in candidates_sorted_base:
        print(f" {c['item_id']}: base_score={c['base_score']}")

    # 离线重排
    reordered = offline_reorder(user_id=1, candidates=candidates, feedbacks=feedbacks)
    
    print("\n--- 离线重排结果（结合历史反馈数据） ---")
    for r in reordered:
        print(f" {r['item_id']}: final_score={r['final_score']:.2f} (base={r['base_score']:.2f}, gain={r['feedback_gain']:.2f})")


if __name__ == "__main__":
    main()
