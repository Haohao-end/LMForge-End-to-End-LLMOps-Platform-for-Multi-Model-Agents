<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthorize } from '@/hooks/use-oauth'
import { useCredentialStore } from '@/stores/credential'

// 1.定义页面所需的数据
const route = useRoute()
const router = useRouter()
const credentialStore = useCredentialStore()
const { authorization, handleAuthorize } = useAuthorize()

onMounted(async () => {
  try {
    // 1.调用authorize接口进行登录
    await handleAuthorize(String(route.params?.provider_name), String(route.query?.code ?? ''))

    // 2.更新用户授权数据并跳转到首页
    credentialStore.update(authorization.value)
    await router.replace({ path: '/home' })
  } catch (error) {
    // 3.出现错误则重定向到登录页面
    await router.replace({ path: '/auth/login' })
  }
})
</script>

<template>
  <div class="w-full min-h-screen flex items-center justify-center bg-white">
    <a-spin tip="第三方授权登录中..."></a-spin>
  </div>
</template>

<style scoped></style>
