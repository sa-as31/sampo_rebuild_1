import { createRouter, createWebHistory } from 'vue-router';

const LoginView = () => import('../views/LoginView.vue');
const AppShell = () => import('../views/AppShell.vue');
const RoleWorkspace = () => import('../modules/taskcenter/TaskCenterView.vue');
const TaskDetailView = () => import('../modules/taskcenter/TaskDetailView.vue');
const OpsDashboardView = () => import('../modules/dashboard/OpsDashboardView.vue');

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
  },
  {
    path: '/',
    name: 'AppShell',
    component: AppShell,
    children: [
      {
        path: 'task/:id',
        name: 'TaskDetail',
        component: TaskDetailView,
        props: route => ({ taskId: route.params.id, role: route.query.role, section: route.query.section })
      },
      {
        path: 'admin',
        redirect: '/admin/pending',
      },
      {
        path: 'admin/pending',
        component: RoleWorkspace,
        props: { role: 'admin', section: 'create' }
      },
      {
        path: 'admin/active',
        component: RoleWorkspace,
        props: { role: 'admin', section: 'active' }
      },
      {
        path: 'admin/completed',
        component: RoleWorkspace,
        props: { role: 'admin', section: 'completed' }
      },
      {
        path: 'requester',
        redirect: '/requester/create',
      },
      {
        path: 'requester/create',
        component: RoleWorkspace,
        props: { role: 'requester', section: 'create' }
      },
      {
        path: 'requester/history',
        component: RoleWorkspace,
        props: { role: 'requester', section: 'history' }
      },
      {
        path: 'executor',
        redirect: '/executor/tasks',
      },
      {
        path: 'executor/tasks',
        component: RoleWorkspace,
        props: { role: 'executor', section: 'tasks' }
      },
      {
        path: 'executor/dashboard',
        component: OpsDashboardView,
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
