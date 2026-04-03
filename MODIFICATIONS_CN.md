# 项目修改说明（中文）

本文档记录我基于原始项目所做的主要修改，目标是让项目在 Docker/CPU 环境可稳定运行，并补充 GPU 入口。

## 1. 依赖与容器化

### 1.1 新增/补全依赖
- 文件：`requirements.txt`
- 主要内容：
  - 固定兼容版本：`numpy<2`、`gym==0.23.1`、`pydantic<2`
  - 补充训练与日志依赖：`torch`、`ray[tune]`、`wandb`、`tensorboard`、`tensorboardX`、`faster-fifo`、`threadpoolctl` 等

### 1.2 完成 Docker 构建流程
- 文件：`Dockerfile`
- 主要修改：
  - 基础镜像改为 `python:3.9-slim`
  - 安装 C++ 编译所需系统依赖（`build-essential`、`g++`、`libgl1`、`libglib2.0-0`）
  - 安装 Python 依赖 + `pybind11` + `cppimport`
  - 构建期预编译两个规划器扩展：
    - `planner.LB_A.planner`
    - `planner.Static_A.planner`

## 2. 论文相关功能补全

### 2.1 新增重规划算法模块
- 文件：
  - `planning/replan_algo.py`
  - `planning/__init__.py`
- 主要实现：
  - `RePlanBase`
  - `NoPathSoRandomOrStayWrapper`
  - `FixNonesWrapper`
- 核心思路：
  - 按论文思路加入拥堵相关代价建模（PlCC/PeCC），用于多智能体重规划与冲突缓解。

## 3. Sample Factory 兼容与运行修复

### 3.1 补全缺失空间类型
- 文件：
  - `sample_factory/algorithms/utils/spaces/discretized.py`
  - `sample_factory/algorithms/utils/spaces/__init__.py`
- 作用：补全 `Discretized`，修复动作空间导入与类型判断链路。

### 3.2 修复 APPO 相关运行问题
- 文件：
  - `sample_factory/algorithms/appo/model.py`
  - `sample_factory/algorithms/appo/model_utils.py`
  - `sample_factory/algorithms/appo/learner.py`
  - `sample_factory/algorithms/appo/policy_worker.py`
  - `sample_factory/algorithms/appo/appo.py`
- 主要修改：
  - 去除不可用导入（`create_atten_layer`）导致的启动问题
  - 修复部分硬编码 `.cuda()` 带来的 CPU 运行崩溃，改为设备自适应
  - 在 GPU 不可用时自动回退 CPU（主流程、learner、policy worker）
  - 为注意力模块缺省参数补充默认值（`num_heads`）

## 4. 新增 GPU 训练入口

- 文件：`main_gpu.py`
- 说明：
  - 逻辑与 `main.py` 基本一致
  - 默认强制 `global_settings.device = "gpu"`
  - 可通过命令行参数继续覆盖其余配置

## 5. 运行验证结果

已在 Docker 中完成如下验证：

1. CPU 主流程（`main.py`）
- 能完成初始化、采样、训练流程并正常退出（退出码 `0`）。

2. 较大规模 CPU 测试
- 使用 `num_workers=2`、`num_envs_per_worker=2`、`target_num_agents=256`、`num_agents=128` 测试通过（退出码 `0`）。

3. GPU 入口文件（`main_gpu.py`）
- 在无 CUDA 的容器中可正确启动，并触发自动回退到 CPU，流程可正常结束（退出码 `0`）。

## 6. 新增文档

- `README.md`：补充本地运行、Docker 运行、GPU 运行和常见问题说明。

## 7. Linux + NVIDIA 一键 GPU 链路补全

为满足“在 Linux + NVIDIA 环境一键直接跑”的目标，新增如下文件：

1. `Dockerfile.gpu`
- 基于 `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- 明确安装 CUDA 版 PyTorch（`torch==2.3.1` + `cu121`）
- 构建期预编译规划器扩展（LB_A / Static_A）

2. `docker-compose.gpu.yml`
- 提供独立 GPU compose 服务（`gpus: all`、`ipc: host`）
- 启动前先执行容器内 GPU 检查脚本，再运行 `main_gpu.py`

3. `scripts/verify_gpu.py`
- 在容器内校验：
  - `torch` 是否为 CUDA 构建
  - CUDA runtime 是否可用
  - 是否存在可见 GPU
- 失败会返回非 0 退出码，避免“误以为在 GPU 上训练”

## 8. Web 前端 UI 架构重构（重大更新）

为解决界面重点不清晰、跳转划分不清晰等问题，对 Vue 前端进行了全面重构：

1. **引入基于 `vue-router` 的多页面架构**：
- 安装并配置了 `vue-router@4`，摒弃了原有单一 `App.vue` 依靠大量 `v-if/v-else` 切换视图的冗余模式。
- 设置了基于角色的路由体系（`/admin/...`, `/requester/...`, `/executor/...`），页面层级和工作流一目了然。

2. **抽离公共布局与状态管理**：
- 提取 `src/views/AppShell.vue` 作为带有顶部导航和侧边栏的公共布局。
- 提取 `src/views/LoginView.vue` 单独负责登录逻辑。
- 创建了原生的轻量级状态管理 `src/stores/auth.js` 统一接管全局用户身份、登录状态与权限分发。

3. **视图跳转与视觉强化**：
- 对主要操作的 CSS (`.btn`, `.admin-task-card`) 增加了 `hover`、`active` 等具有阴影反馈和 Z 轴深度的交互效果，提升“视觉操作感”和美感。
- 引入了 `fade` 和 `fade-slide` 路由动画，实现无缝丝滑的视图切换体验。
- 重用原有 `TaskCenterView.vue` 强大的交互逻辑，通过路由 prop 的双向绑定实现细粒度的子模块切换（例如：`/admin/pending` 映射到 `create` 视图），既保障了业务稳定，又使页面 URL 可分享、可回退。

## 9. 文档补充：解释高风险删除命令 `rm -rf src/components src/assets`

1. `解疑.md`
- 新增关于 `rm -rf src/components src/assets` 的说明
- 明确该命令会递归强制删除：
  - `src/components`
  - `src/assets`
- 同步解释了 `rm -rf` 三部分参数的含义，以及为什么这类命令会被标记为高风险

## 10. 文档补充：解释为什么会出现删除 `src/components` 和 `src/assets` 的步骤

1. `解疑.md`
- 新增关于该删除命令“出现原因”的说明
- 结合截图中的上下文，说明这类命令通常出现在：
  - 新建 Vue + Vite 前端后
  - 清理默认脚手架内容
  - 准备整体重构页面结构之前
- 同时强调其意图通常是“清理旧结构，准备重建”，但前提必须是这些目录里的内容已确认不再需要

## 11. `web_frontend_ge` 前端重构续作（重大更新）

本轮继续完成上次未收尾的 `web_frontend_ge` 子项目重构，目标是把未完成的演示模板补齐为一套可直接展示的完整前端界面。

### 11.1 全局视觉系统与构建链路

- 文件：
  - `web_frontend_ge/src/styles/main.css`
  - `web_frontend_ge/src/App.vue`
  - `web_frontend_ge/vite.config.js`
- 主要修改：
  - 重新定义全局设计令牌，切换为暖白、低饱和、编辑式的视觉语言
  - 新增统一按钮、分段导航、指标卡、状态徽标、深色舞台等基础样式
  - 优化全局页面切换动效，保持丝滑但克制
  - 在 Vite 中接入 `@tailwindcss/vite` 插件，使样式链路更完整

### 11.2 补齐共享展示数据层

- 文件：
  - `web_frontend_ge/src/data/mockMissionData.js`
- 主要修改：
  - 新增统一的任务、舰队、扇区覆盖、维护队列、动态流等 mock 数据
  - 抽离 `getTaskById`、`getBoardColumns` 等辅助方法
  - 为 `Dashboard / TaskBoard / TaskDetail / FleetMonitor` 提供统一数据口径

### 11.3 重做布局壳层

- 文件：
  - `web_frontend_ge/src/layouts/AuthLayout.vue`
  - `web_frontend_ge/src/layouts/MainLayout.vue`
  - `web_frontend_ge/src/router/index.js`
- 主要修改：
  - 重构登录页外层布局，加入更柔和的背景氛围与转场
  - 重构主工作台布局，统一顶部命题区、信号摘要和分段导航
  - 为路由补充页面简介文案
  - 修复原本路由中引用了不存在页面的问题

### 11.4 继续完成未完成业务页面

- 文件：
  - `web_frontend_ge/src/views/LoginView.vue`
  - `web_frontend_ge/src/views/TaskDashboard.vue`
  - `web_frontend_ge/src/views/TaskBoard.vue`
  - `web_frontend_ge/src/views/TaskDetail.vue`
  - `web_frontend_ge/src/views/FleetMonitor.vue`
- 主要修改：
  - `LoginView`：
    - 从简单表单升级为展示型登录入口
    - 提供角色切换、演示账号预设和说明卡片
  - `TaskDashboard`：
    - 采用“大 Hero + 指标条 + 活跃任务舞台 + 动态流 + 系统节拍”结构
  - `TaskBoard`：
    - 支持看板/列表双视图
    - 增加按任务阶段切换的筛选条
  - `TaskDetail`：
    - 采用“深色运行舞台 + 右侧概览/参数/告警/回放面板”结构
    - 用路径锚点和进度条模拟任务运行主舞台
  - `FleetMonitor`：
    - 新增舰队观测页
    - 展示覆盖扇区、在线机组、维护队列与即将执行任务

### 11.5 验证结果

- 已执行：
  - `cd web_frontend_ge && npm run build`
- 结果：
  - 构建通过
  - 已通过浏览器实测关键路由：
    - `/login`
    - `/dashboard`
    - `/tasks`
    - `/tasks/T004`
    - `/fleet`

## 12. `web_frontend` 运营化前端重构（重大更新）

本轮继续围绕 `web_frontend` 主链路做运营化重构，目标是把页面从“说明型演示原型”收紧成更接近真实企业运营台的前端界面，同时修复现有构建阻塞。

### 12.1 登录页与应用壳层收紧

- 文件：
  - `web_frontend/src/views/LoginView.vue`
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 登录页文案改为更偏系统入口和运营席位表达，压缩介绍口吻
  - 把账号提示与默认密码改成紧凑的状态胶囊，而不是连续说明文字
  - 顶部壳层新增工作台徽标，标题与简介改成更短、更产品化的页面命题
  - 调整头部、卡片、标签和面板的视觉层级，使全站更统一

### 12.2 三类角色工作台改为运营结构

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 管理员首页改成“审核 / 执行 / 归档”三类运营队列视图，移除教程式小字说明
  - 申请人首页改成“主表单 + 队列状态”结构，不再用“申请说明 / 当前流程 / 任务类别解释”占据首屏
  - 飞手首页补齐任务队列概览统计，强化待执行、执行中、已结束三类状态
  - 搜索和日期筛选重排为更紧凑的运营工具条
  - 任务卡片文案改成“标题 + 阶段 + 两行核心元信息”

### 12.3 任务详情页与运行舞台收紧

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
  - `web_frontend/src/modules/operations/OperationsModeView.vue`
  - `web_frontend/src/modules/dashboard/OpsDashboardView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 任务详情页顶部新增任务状态摘要条，减少泛化说明
  - 回放区和执行区删除“这里用于查看……”等解释型文案，改为状态条、帧信息、节拍信息
  - 飞手页把“反馈”重命名为更偏运营语境的“记录”，提交按钮文案也同步收紧
  - 联合运行视图改为通过“参数已锁定 / 当前步 / 镜头 / 放大”等状态型标签表达当前上下文
  - 运营观测页把焦点任务、任务阶段和更新时间前置，列表文案更贴近真实监控台

### 12.4 构建阻塞修复

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
- 主要修改：
  - 删除重复声明的 `onImportMapFile`，修复此前导致 `vite build` 失败的脚本错误

### 12.5 验证结果

- 已执行：
  - `cd web_frontend && npm run build`
- 结果：
  - 构建通过
  - `TaskDetailView.vue` 的重复声明问题已修复

## 13. 顶栏标题进一步精简并压缩上半屏占比

- 文件：
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 将顶栏黑色大标题改为更短的单一主标题，避免长句占据首屏
  - 申请页大标题收紧为：`提交任务申请`
  - 其他页面同步改为简短标题：
    - `审核申请`
    - `执行调度`
    - `任务归档`
    - `我的申请`
    - `任务中心`
    - `运营观测`
    - `任务详情`
  - 非必要页面简介默认不再显示，只在申请页保留一行很短的辅助说明
  - 缩小顶栏整体高度：减少上下内边距、标题字号、页签外边距和账户区尺寸
  - 让页面上半部分更紧凑，避免首屏被大面积头部留白占满

## 14. 申请页移除统计区并转移到“我的申请”

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 删除申请人工作台顶部整块统计 Hero，避免“发起申请”页被状态区占据
  - 删除“发起申请”页右侧的申请队列统计侧栏，让该页只保留任务申请表单和提交预览
  - 将申请总数、待审核、已通过、已驳回以及“最近申请”统一移动到“我的申请”页中显示
  - 把申请页布局改为单列，使填写界面更干净、更聚焦

## 15. 发起申请后自动切换到“我的申请”

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/modules/taskcenter/TaskDetailView.vue`
- 主要修改：
  - 修复“提交成功后看不到我的申请数据变动”的交互问题
  - 申请提交成功后，先刷新任务列表，再自动切换到 `我的申请`
  - 保留新创建任务的 `task_id` 作为当前选中项，进入历史页后直接看到刚提交的申请详情
  - 成功提示改为“已切换到我的申请”，让状态反馈更直接
  - 修复任务中心和任务详情页未正确读取当前登录用户的问题，避免 `我的申请` / `分配给我的任务` 因 `currentUser` 为空而筛选不到数据

## 16. 管理端顶部统计拆分为独立“总览”页

- 文件：
  - `web_frontend/src/router/index.js`
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/styles.css`
- 主要修改：
  - 删除管理员工作页顶部原有的大面积统计 Hero，避免审核页一进入先被总览区占住
  - 新增独立页面 `总览`，承接原来的任务总数、执行中、已归档、待审核等统计信息
  - 管理员顶部分页调整为：
    - `总览`
    - `审核`
    - `执行`
    - `归档`
  - 将管理员页面切换改为真正的路由分页，避免标题、地址和内容不同步
  - 总览页改为紧凑卡片结构，并保留跳转到审核、执行、归档的快捷入口

## 17. 飞手页顶部统计迁入独立“总览”页

- 文件：
  - `web_frontend/src/router/index.js`
  - `web_frontend/src/views/AppShell.vue`
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
  - `web_frontend/src/modules/dashboard/OpsDashboardView.vue`
- 主要修改：
  - 删除飞手任务中心顶部原有的“我的任务队列”大统计区，避免任务页首屏被概览信息占满
  - 将飞手导航改为：
    - `总览`
    - `任务中心`
  - 新增飞手侧独立 `总览` 路由，原 `executor/dashboard` 兼容跳转到 `executor/overview`
  - 飞手总览改为只统计“分配给当前飞手”的任务，不再展示全局任务汇总
  - 总览卡片改为任务总数、待执行、执行中、已结束，并保留焦点任务和任务快照

## 18. 任务卡点击恢复跳转详情页

- 文件：
  - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 修复飞手任务中心点击任务卡无跳转的问题
  - 修复申请人“我的申请”列表点击记录无跳转的问题
  - 将这两处点击行为从组件内 `selectTask` 改回路由跳转到 `/task/:id`
  - 跳转时保留角色和来源分页参数，确保详情页上下文正确
