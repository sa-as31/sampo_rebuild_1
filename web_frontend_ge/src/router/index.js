import { createRouter, createWebHistory } from 'vue-router';

// Layouts
const MainLayout = () => import('../layouts/MainLayout.vue');
const AuthLayout = () => import('../layouts/AuthLayout.vue');

// Views
const LoginView = () => import('../views/LoginView.vue');
const TaskDashboard = () => import('../views/TaskDashboard.vue');
const TaskBoard = () => import('../views/TaskBoard.vue');
const TaskDetail = () => import('../views/TaskDetail.vue');
const FleetMonitor = () => import('../views/FleetMonitor.vue');

const routes = [
  {
    path: '/login',
    component: AuthLayout,
    children: [
      { path: '', name: 'Login', component: LoginView }
    ]
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { 
        path: 'dashboard', 
        name: 'Dashboard', 
        component: TaskDashboard,
        meta: {
          title: '总览仪表盘',
          intro: '把审批、执行和舰队态势压缩成一个更适合展示和调度的首页。',
          icon: 'ChartPieIcon',
        }
      },
      { 
        path: 'tasks', 
        name: 'TaskBoard', 
        component: TaskBoard,
        meta: {
          title: '任务看板',
          intro: '用统一的任务视图串联申请、执行准备、运行中和归档复盘。',
          icon: 'ViewColumnsIcon',
        }
      },
      { 
        path: 'tasks/:id', 
        name: 'TaskDetail', 
        component: TaskDetail,
        meta: {
          title: '任务详情',
          intro: '围绕单个任务展开主舞台、参数、告警和回放观察。',
          hidden: true,
        }
      },
      { 
        path: 'fleet', 
        name: 'FleetMonitor', 
        component: FleetMonitor,
        meta: {
          title: '舰队观测',
          intro: '从在线链路、电量、覆盖扇区和维护队列观察当前机组状态。',
          icon: 'PaperAirplaneIcon',
        }
      },
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
