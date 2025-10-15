import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/HomeView.vue'
import Register from '../views/RegisterView.vue'
import MainLayout from '../views/MainLayout.vue'
import Login from '../views/LoginView.vue' 
import MatchDisplay from '../views/MatchDisplayView.vue'
import DisplayView from '../views/DisplayView.vue'


const routes = [
  // 首页
  { path: '/', component: Home },

  // 注册页
  { path: '/register', component: Register },

  // 登录页
  { path: '/login', component: Login }, 

  // 主页面
  { path: '/main', component: MainLayout }, 

  // 匹配页面
  { path: '/match', component: MatchDisplay },
  
  // 展示喜欢的人的资料
  { path: '/display/:uid', name: 'display', component: DisplayView, props: true },

  // 未知路径跳回首页
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
