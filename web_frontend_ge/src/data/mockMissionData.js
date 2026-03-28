export const shellSignals = [
  { label: '今日审批', value: '14', detail: '较昨日 +3' },
  { label: '在线机组', value: '19 / 24', detail: '链路稳定' },
  { label: '平均吞吐', value: '4.2 /s', detail: '高峰时段' },
];

export const dashboardMetrics = [
  { label: '执行中任务', value: '06', note: '集中在巡检与测绘任务', tone: 'teal' },
  { label: '待审核申请', value: '09', note: '申请高峰集中在下午', tone: 'amber' },
  { label: '今日完成架次', value: '148', note: '较昨日提升 12%', tone: 'ink' },
  { label: '系统告警', value: '02', note: '均已进入处理流程', tone: 'rose' },
];

export const dashboardActivities = [
  { title: '北区屋顶巡检完成第 3 圈路径校核', time: '5 分钟前', tone: 'teal' },
  { title: '仓储航线补给任务已通过管理员复核', time: '18 分钟前', tone: 'ink' },
  { title: '观礼编队演示任务上报 1 条低电量提醒', time: '26 分钟前', tone: 'rose' },
  { title: '实验田热成像测绘进入执行准备阶段', time: '38 分钟前', tone: 'amber' },
];

export const capacityLanes = [
  { label: '审核吞吐', value: '14 / h', percent: 72, detail: '管理员工作台保持平稳节奏' },
  { label: '飞手负载', value: '79%', percent: 79, detail: '建议晚高峰前再释放 2 名待命飞手' },
  { label: '地图准备度', value: '91%', percent: 91, detail: '大部分任务已绑定可用地图模板' },
];

export const fleetSummary = [
  { label: '活跃机组', value: '19', note: '执行、热备、联调合计', tone: 'teal' },
  { label: '待命机组', value: '03', note: '适合补位临时任务', tone: 'ink' },
  { label: '维护中', value: '02', note: '云台校准与电池养护', tone: 'amber' },
  { label: '链路告警', value: '01', note: '已转人工跟进', tone: 'rose' },
];

export const fleetRoster = [
  { id: 'UAV-07', name: 'UAV-07', mission: '北区屋顶巡检', pilot: '侯越', stage: '第三圈屋面采样', battery: 88, link: 97, tone: 'teal' },
  { id: 'UAV-12', name: 'UAV-12', mission: '体育馆顶棚测绘', pilot: '陈澈', stage: '顶部网格对齐', battery: 76, link: 91, tone: 'ink' },
  { id: 'UAV-18', name: 'UAV-18', mission: '观礼编队演示', pilot: '林祺', stage: '低空阵型保持', battery: 42, link: 86, tone: 'amber' },
  { id: 'UAV-23', name: 'UAV-23', mission: '仓储补给航线', pilot: '周岚', stage: '返航前补给确认', battery: 63, link: 94, tone: 'teal' },
];

export const sectorCoverage = [
  { name: '北区建筑群', coverage: 92, latency: '28 ms', status: '巡检稳定', tone: 'teal' },
  { name: '中心操场', coverage: 81, latency: '35 ms', status: '编队复演中', tone: 'ink' },
  { name: '仓储物流轴', coverage: 74, latency: '49 ms', status: '补给往返频繁', tone: 'amber' },
];

export const maintenanceQueue = [
  { name: 'UAV-03', issue: '主摄像头防抖漂移', eta: '今日 17:30 前完成校准' },
  { name: 'UAV-15', issue: '电池循环数接近上限', eta: '建议明日更换备电池组' },
];

const baseTasks = [
  {
    id: 'T001',
    code: 'TASK-20260328-001',
    name: '北区屋顶巡检',
    stage: '待审核',
    stageKey: 'pending',
    category: '巡检',
    location: '北区 3 号楼与 4 号楼连廊',
    schedule: '03-28 14:30',
    requester: '建筑安全组',
    operator: '待分配',
    drones: 4,
    progress: 18,
    throughput: '2.4 /s',
    map: 'north_rooftop_v3.json',
    algorithm: 'SMAPO / APPO',
    summary: '重点检查屋顶边缘、风机组与通风井周边遮挡，任务需要稳定低速巡检。',
    note: '建议优先分配具备近距离悬停经验的飞手。',
    tone: 'amber',
    kpis: [
      { label: '预计时长', value: '42 min' },
      { label: '风险等级', value: '中' },
      { label: '申请优先级', value: '高' },
    ],
    alerts: [],
    logs: [
      '[REVIEW] 建筑安全组提交屋顶巡检申请。',
      '[CHECK] 地图模板 north_rooftop_v3.json 可复用。',
      '[TODO] 待补充飞手与起飞窗口。',
    ],
    checkpoints: [
      { label: 'S1', x: 14, y: 66, altitude: '18m' },
      { label: 'S2', x: 32, y: 42, altitude: '20m' },
      { label: 'S3', x: 48, y: 35, altitude: '22m' },
      { label: 'S4', x: 72, y: 46, altitude: '19m' },
    ],
  },
  {
    id: 'T002',
    code: 'TASK-20260328-002',
    name: '实验田热成像测绘',
    stage: '待审核',
    stageKey: 'pending',
    category: '测绘',
    location: '实验田 B 区与灌溉沟渠',
    schedule: '03-28 16:00',
    requester: '农业研究组',
    operator: '待分配',
    drones: 6,
    progress: 24,
    throughput: '3.1 /s',
    map: 'field_thermal_v2.json',
    algorithm: 'SMAPO / Hybrid Search',
    summary: '需要在日照变化前完成热源分布采样，重点观察灌溉沟渠周边温差。',
    note: '申请人要求输出热成像拼接图。',
    tone: 'amber',
    kpis: [
      { label: '预计时长', value: '55 min' },
      { label: '风险等级', value: '低' },
      { label: '申请优先级', value: '中' },
    ],
    alerts: [],
    logs: [
      '[REVIEW] 等待管理员确认执行时间。',
      '[MAP] 热成像模板已通过上次 smoke test。',
      '[NOTE] 推荐绑定 6 架中航时机组。',
    ],
    checkpoints: [
      { label: 'F1', x: 18, y: 62, altitude: '25m' },
      { label: 'F2', x: 34, y: 50, altitude: '26m' },
      { label: 'F3', x: 58, y: 38, altitude: '24m' },
      { label: 'F4', x: 80, y: 44, altitude: '23m' },
    ],
  },
  {
    id: 'T003',
    code: 'TASK-20260328-003',
    name: '仓储补给航线',
    stage: '待执行',
    stageKey: 'ready',
    category: '运输',
    location: '仓库 A 区 -> 东实验楼',
    schedule: '03-28 15:10',
    requester: '实验物流组',
    operator: '周岚',
    drones: 3,
    progress: 42,
    throughput: '3.6 /s',
    map: 'warehouse_route_v5.json',
    algorithm: 'SMAPO / Dispatch',
    summary: '临时补给路线已规划完成，等待任务窗口打开后执行。',
    note: '物资为传感器备件，要求飞行平稳。',
    tone: 'ink',
    kpis: [
      { label: '预计时长', value: '28 min' },
      { label: '风险等级', value: '低' },
      { label: '任务批次', value: '第二批' },
    ],
    alerts: [],
    logs: [
      '[READY] 机组已完成挂载检查。',
      '[SYNC] 飞手周岚已确认路线。',
      '[WAIT] 等待起飞时间窗开放。',
    ],
    checkpoints: [
      { label: 'W1', x: 14, y: 72, altitude: '12m' },
      { label: 'W2', x: 36, y: 56, altitude: '16m' },
      { label: 'W3', x: 58, y: 44, altitude: '18m' },
      { label: 'W4', x: 82, y: 32, altitude: '14m' },
    ],
  },
  {
    id: 'T004',
    code: 'TASK-20260328-004',
    name: '体育馆顶棚测绘',
    stage: '执行中',
    stageKey: 'running',
    category: '测绘',
    location: '新体育馆顶棚',
    schedule: '03-28 13:40',
    requester: '设施运维组',
    operator: '陈澈',
    drones: 8,
    progress: 67,
    throughput: '4.2 /s',
    map: 'stadium_roof_scan_v4.json',
    algorithm: 'SMAPO / APPO',
    summary: '任务已进入顶棚网格覆盖阶段，当前重点是边缘遮挡修补与视角补偿。',
    note: '顶棚南侧风速上升，需关注低速悬停姿态。',
    tone: 'teal',
    kpis: [
      { label: '当前高度', value: '24m' },
      { label: '实时延迟', value: '31 ms' },
      { label: '覆盖率', value: '68%' },
    ],
    alerts: [
      { level: 'warn', title: '南侧风场波动', detail: '第 6 架机体在南侧边缘出现 45ms 延迟抖动。' },
      { level: 'info', title: '数据回传稳定', detail: '热区重建模块已连续 20 分钟无丢帧。' },
    ],
    logs: [
      '[INFO] Env reset completed.',
      '[DEBUG] Agent 0 -> target (12, 45, 10)',
      '[DEBUG] Agent 1 -> target (14, 40, 10)',
      '[WARN] High latency detected: 45ms',
      '[DEBUG] Step 125 executed.',
    ],
    checkpoints: [
      { label: 'P1', x: 12, y: 70, altitude: '18m' },
      { label: 'P2', x: 28, y: 56, altitude: '22m' },
      { label: 'P3', x: 44, y: 40, altitude: '24m' },
      { label: 'P4', x: 64, y: 34, altitude: '24m' },
      { label: 'P5', x: 82, y: 46, altitude: '21m' },
    ],
  },
  {
    id: 'T005',
    code: 'TASK-20260328-005',
    name: '观礼编队演示',
    stage: '执行中',
    stageKey: 'running',
    category: '演示',
    location: '中心操场低空展示区',
    schedule: '03-28 12:20',
    requester: '活动统筹组',
    operator: '林祺',
    drones: 16,
    progress: 58,
    throughput: '3.8 /s',
    map: 'formation_show_v8.json',
    algorithm: 'SMAPO / Formation',
    summary: '当前正在进行队形切换复演，重点观察阵列边缘机体的队形贴合。',
    note: '一架无人机低电量，建议下一轮前完成轮换。',
    tone: 'rose',
    kpis: [
      { label: '当前编队', value: '双环' },
      { label: '实时延迟', value: '39 ms' },
      { label: '覆盖率', value: '72%' },
    ],
    alerts: [
      { level: 'danger', title: '低电量提醒', detail: 'UAV-18 当前电量 42%，建议 8 分钟内轮换。' },
    ],
    logs: [
      '[INFO] Formation warm-up complete.',
      '[DEBUG] Pattern ring-switch -> stable.',
      '[WARN] UAV-18 battery low.',
      '[DEBUG] Step 204 executed.',
    ],
    checkpoints: [
      { label: 'C1', x: 20, y: 58, altitude: '14m' },
      { label: 'C2', x: 36, y: 44, altitude: '16m' },
      { label: 'C3', x: 52, y: 36, altitude: '17m' },
      { label: 'C4', x: 70, y: 42, altitude: '15m' },
      { label: 'C5', x: 84, y: 56, altitude: '13m' },
    ],
  },
  {
    id: 'T006',
    code: 'TASK-20260327-016',
    name: '南门异常排查',
    stage: '已归档',
    stageKey: 'archived',
    category: '巡检',
    location: '南门与访客通道',
    schedule: '03-27 18:20',
    requester: '校园安保组',
    operator: '孙峥',
    drones: 3,
    progress: 100,
    throughput: '4.6 /s',
    map: 'south_gate_scan_v2.json',
    algorithm: 'SMAPO / Search',
    summary: '异常排查任务已完成，已确认现场无持续风险，回放数据可直接用于答辩展示。',
    note: '复盘建议保留夜间低照度链路优化方案。',
    tone: 'ink',
    kpis: [
      { label: '任务耗时', value: '24 min' },
      { label: '告警条数', value: '1' },
      { label: '反馈条数', value: '2' },
    ],
    alerts: [
      { level: 'info', title: '夜间补光触发', detail: '低照度模式自动接管云台曝光。' },
    ],
    logs: [
      '[INFO] South gate anomaly sweep finished.',
      '[INFO] No residual risk detected.',
      '[ARCHIVE] Replay saved to task_replays/4511d2d0c5d6.json',
    ],
    checkpoints: [
      { label: 'A1', x: 16, y: 64, altitude: '10m' },
      { label: 'A2', x: 34, y: 48, altitude: '12m' },
      { label: 'A3', x: 58, y: 44, altitude: '13m' },
      { label: 'A4', x: 76, y: 54, altitude: '10m' },
    ],
  },
];

export const tasks = baseTasks.map((task) => ({
  ...task,
  timeline: [
    { label: '任务申请', detail: `${task.requester} 已提交任务。`, done: true },
    { label: '审核排班', detail: task.stageKey === 'pending' ? '等待管理员确认排班。' : `已由管理员完成 ${task.operator} 排班。`, done: task.stageKey !== 'pending' },
    { label: '执行联调', detail: task.stageKey === 'archived' ? '执行阶段已完成。' : '当前进入联调/执行窗口。', done: ['running', 'archived'].includes(task.stageKey) },
    { label: '回放归档', detail: task.stageKey === 'archived' ? '回放、日志和反馈已归档。' : '执行结束后自动生成。', done: task.stageKey === 'archived' },
  ],
}));

export const stageMeta = {
  pending: { label: '待审核', tone: 'amber' },
  ready: { label: '待执行', tone: 'ink' },
  running: { label: '执行中', tone: 'teal' },
  archived: { label: '已归档', tone: 'slate' },
};

export function getTaskById(id) {
  return tasks.find((task) => task.id === id) || tasks[3];
}

export function getBoardColumns() {
  const order = ['pending', 'ready', 'running', 'archived'];
  return order.map((stageKey) => ({
    id: stageKey,
    ...stageMeta[stageKey],
    tasks: tasks.filter((task) => task.stageKey === stageKey),
  }));
}
