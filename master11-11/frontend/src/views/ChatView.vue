<template>
    <div class="chat-page">
      <h2>聊天页面（占位）</h2>
      <p>正在和用户 {{ withUser }} 聊天（query 参数 with={{ withUser }}）</p>
    </div>
  </template>
  
  <script setup>
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  
  const route = useRoute()
  
  // 我们之前用的是 /chat?with=xxx，所以从 query 拿
  const withUser = computed(() => route.query.with || '')
  </script>
  
  <style scoped>
  .chat-page {
    padding: 24px;
  }
  </style>
  