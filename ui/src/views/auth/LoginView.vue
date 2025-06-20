<script setup lang="ts">
import LoginBanner from './components/LoginBanner.vue'
import LoginForm from './components/LoginForm.vue'
</script>

<template>
  <!-- 页面容器 -->
  <div class="flex h-screen bg-white">
    <!-- 左侧banner -->
    <login-banner />
    <!-- 右侧表单 -->
    <div class="relative flex flex-1 items-center justify-center pb-10">
      <!-- 登录表单 -->
      <login-form />
    </div>
  </div>
</template>

<style scoped></style>
