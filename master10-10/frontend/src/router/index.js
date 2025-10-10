import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/HomeView.vue'
import Register from '../views/RegisterView.vue'
import MainLayout from '../views/MainLayout.vue'
import Login from '../views/LoginView.vue' 
import Display from '../views/DisplayView.vue'


const routes = [
  // 首页
  { path: '/', component: Home },

  // 注册页
  { path: '/register', component: Register },

  // 登录页
  { path: '/login', component: Login }, 

  // 主页面
  { path: '/main', component: MainLayout }, 
  // 展示
  { path: '/display/:uid', component: Display},

  // 未知路径跳回首页
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
