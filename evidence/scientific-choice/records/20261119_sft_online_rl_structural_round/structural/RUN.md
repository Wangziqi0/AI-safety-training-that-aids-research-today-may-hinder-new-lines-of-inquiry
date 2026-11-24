# 运行与复核

在本目录执行（仅用 Python 标准库，单 CPU 进程）：

```sh
python3 producer.py
python3 receiver.py
python3 analysis.py
python3 joint.py
python3 verify.py
```

生产端保留初末检查点、逐步训练日志、自然封包三种记录，另以 deployment.jsonl.gz 保留冻结部署验证的逐件记录。training.jsonl.gz 的 step=-1 为初始权重，随后每行是一个 24 样品批次，含更新后权重、所用平均梯度；samples 每条为 [虚构文档编号, 任务类, 动作, 实得奖励或 null, 更新前 3 个动作概率]。任务类0是公共场景，1是受限上下文中仅请求公共字段，2是受限字段将进入输出。动作0是交付，1是澄清，2是字段替换。A 把危险请求整体交给澄清，B 仍尽量交付公共部分。共同部署层拦住标准包装中的虚构字段，持出别名可漏过。checkpoints.jsonl.gz 中保存初末权重、用于读出的对数几率变化与部署验证均值。materials.jsonl.gz 由冻结父代单独生成，具体结构见 MATERIAL_SCHEMA.md。

独立运行 receiver.py 只从自然材料加同一普通仪器环境取得后继结果，输出 outcomes.jsonl.gz。current_command 给出当前控制器实际应用的偏置，current_observed 是新读数。后继实测的设定与读数保留在 followup_position、followup_trim、new_reading；reference 是只用于事后核分的另一标定条件。后继选择函数 followup_controller 无来源标签、学习权重、真实斜率和结果输入。普通标准中心测量无需要使用所得斜率；需要且无平价替代或修复的样品允许默认值恰好正确。证书资源和维修代价分别记录。预算限制预定，源端双点可以及时完成当前任务，也可能错过当前窗口而保留下两点证据。

seed_means.csv 和 paired_seed_differences.csv 包含逐复本率和配对差；contrasts.csv 是所有对照、分层的均值及区间；algorithm_interactions.csv 为同一种子中两种训练算法内干预差的再次差分。仅同算法 A/H 等差直接回答所选算法的训练配方比较。区间是独立整轮复本近似 t 区间，多个次要比较不作校正。audit.json 给出逐样品重算概率、奖励、梯度和权重的审计与材料/结果关联数。具体脚本保留所有生成规则，模型推断是有限动作，不计算现实研究团队或语言模型的效应。
