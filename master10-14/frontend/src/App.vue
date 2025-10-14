<template>
  <div>
    <header style="padding: 12px 16px; border-bottom: 1px solid #eee;">
      <strong>婚恋系统</strong>
      <nav style="float: right;">
        <router-link to="/">首页</router-link>
        <router-link to="/register" style="margin-left: 16px;">注册</router-link>
        <router-link to="/login" style="margin-left: 16px;">登录</router-link>
      </nav>
    </header>

    <main style="padding: 20px;">
      <router-view />
    </main>
  </div>
</template>
