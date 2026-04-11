# 系统数据库ER图配套说明

## 图名建议

图X 无人机动态路径规划系统数据库ER图

## 正文引用语句

为使任务申请、审核分配、执行调度、告警反馈与结果评估的业务链路具备更清晰的数据库落地结构，本文进一步设计了规范化数据库 ER 图，如图X所示。

## 图注说明

该图采用数据库 ER 图表达方式，对当前系统中的任务管理主链路进行规范化建模。图中以 `execution_tasks` 为中心表，向外关联任务申请、无人机分配、地图资源、规划路径、运行告警、用户反馈与执行结果等对象。与当前 SQLite 中以 `tasks + params_json` 承载多类语义的实现不同，本图将申请态、执行态和分配态拆分为独立表，以突出主外键关系和数据库层次结构。

## 主表与核心字段

- `user_accounts`：`PK user_id`、`username`、`display_name`、`role`、`department`、`status`
- `auth_credentials`：`PK/FK user_id`、`password_hash`、`updated_at`
- `task_requests`：`PK request_id`、`FK requester_user_id`、`request_name`、`task_category`、`requested_location`、`scheduled_start_at`、`review_status`
- `execution_tasks`：`PK task_id`、`FK request_id`、`FK map_id`、`task_name`、`source`、`status`、`tick_ms`、`planned_start_at`
- `task_assignments`：`PK assignment_id`、`FK task_id`、`FK uav_id`、`FK assigned_by_user_id`、`assigned_at`、`assignment_status`
- `uavs`：`PK uav_id`、`uav_code`、`model_name`、`fleet_group`、`current_status`、`home_base`
- `maps`：`PK map_id`、`map_name`、`scene_type`、`obstacle_profile`、`map_version`
- `planned_paths`：`PK path_id`、`FK task_id`、`planning_method`、`path_sequence`、`generated_at`、`path_status`
- `task_alerts`：`PK alert_id`、`FK task_id`、`alert_level`、`alert_code`、`message`、`frame_step`
- `task_feedback`：`PK feedback_id`、`FK task_id`、`FK user_id`、`category`、`message`、`created_at`
- `task_results`：`PK result_id`、`FK task_id (UNIQUE)`、`throughput`、`avg_latency`、`conflict_count`、`completed_at`

## 主要关系

- `user_accounts` `1:1` `auth_credentials`
- `user_accounts` `1:N` `task_requests`
- `task_requests` `1:0..1` `execution_tasks`
- `maps` `1:N` `execution_tasks`
- `execution_tasks` `1:N` `task_assignments`
- `uavs` `1:N` `task_assignments`
- `user_accounts` `1:N` `task_assignments`
- `execution_tasks` `1:N` `planned_paths`
- `execution_tasks` `1:N` `task_alerts`
- `execution_tasks` `1:N` `task_feedback`
- `user_accounts` `1:N` `task_feedback`
- `execution_tasks` `1:1` `task_results`

## 从当前真实库到规范化设计的映射

- 当前真实库中的 `tasks`
  - 在本图中被拆分为 `task_requests` 与 `execution_tasks`
  - 目的：分离申请阶段和执行阶段，降低单表职责耦合
- 当前真实库中的 `params_json`
  - 在本图中被拆分为结构化字段和关联表
  - 例如申请人、分配人、地图、计划时间、任务分配等信息分别进入主表或关联表
- 当前真实库中的 `task_feedback`
  - 在本图中保留为独立表，但明确 `user_id` 与 `task_id` 的外键语义
- 当前真实库中尚未显式存在的 `task_assignments`
  - 在本图中新增为中间表
  - 用于规范表达“一个执行任务可分配多架无人机”的关系

## 未纳入主图的支撑表

- `task_events`：运行时事件流与回放支撑，更偏日志层
- `app_state`：会话与当前身份状态，更偏系统状态层
- 训练实验记录、模型权重、回放文件：更偏实验与文件资产层，不属于任务管理主链路数据库主图
