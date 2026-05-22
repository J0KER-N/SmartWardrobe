# Rules Engine 服务

简要说明 Rules Engine 的用途、位置与本地验证步骤。

位置
- `backend/app/services/rules_engine.py`

概述
- 基于简单 YAML 规则对衣物进行匹配与评分，返回包含 `candidate_id`, `garment_id`, `score`, `reason` 的候选列表。

配置
- 规则文件目录：`backend/config/rules/*.yaml`（默认）。
- 规则项示例字段：`name`, `description`, `tag`, `color`, `style`, `weight`。

本地运行
- 使用示例脚本演示：
  - `python scripts/run_rules_demo.py`
  - 或通过 mock endpoint（需运行后端）：`POST /internal/mock_recommend`。

测试
- 运行本模块相关测试：
```bash
pytest backend/tests/test_rules_engine.py -q
pytest backend/tests/test_rules_engine_priority.py -q
```

开发注意事项
- `RulesEngine` 支持传入自定义 `rules_path` 以便在测试中使用临时规则文件。
