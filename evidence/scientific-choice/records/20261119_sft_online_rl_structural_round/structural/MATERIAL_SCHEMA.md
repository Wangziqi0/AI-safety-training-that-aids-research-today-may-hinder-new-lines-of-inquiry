# 跨模块交换

运行完成后写 `materials.jsonl.gz`（gzip UTF-8 JSON lines）。每项顶层含 `seed,algo,arm,coupling,split,family,clone,package`。首选 `coupling="aligned"`，`algo` 为 sft 或 reinforce，`arm` 为 H/A/B；split 取 source、heldout。package 含 `family_features`（长度2、±1）、`current`（已按时交付的当前整数，或 null）、`observations`（按自然采集顺序的 [位置,读数] 整数对，可能为空；中心位置0）、`status`（delivered / expired / unavailable）。同一仪器族斜率是 ±2，独立新样品中心截距改变；双点可识别斜率。公开规律可由来源族学习但有例外。真值、机会、后续结果存于独立 `outcomes.jsonl.gz`，不得加入训练材料。可用共同 heldout 家族生成新样品，评价键 (seed, split, family)，预先锁定的模拟器可回答新位置的真实读数。材料无需请求方还原策略或训练。
