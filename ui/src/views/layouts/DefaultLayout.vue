<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLogout } from '@/hooks/use-auth'
import LayoutSidebar from './components/LayoutSidebar.vue'
import { useGetCurrentUser } from '@/hooks/use-account'
import { useCredentialStore } from '@/stores/credential'
import { useAccountStore } from '@/stores/account'
import SettingModal from '@/views/layouts/components/SettingModal.vue'

// 1.定义页面所需数据
const settingModalVisible = ref(false)
const router = useRouter()
const credentialStore = useCredentialStore()
const accountStore = useAccountStore()
const { handleLogout: handleLogoutHook } = useLogout()
const { current_user, loadCurrentUser } = useGetCurrentUser()

// 2.退出登录按钮
const handleLogout = async () => {
  // 2.1 发起请求退出登录
  await handleLogoutHook()

  // 2.2 清空授权凭证+账号信息
  credentialStore.clear()
  accountStore.clear()

  // 2.3 跳转到授权认证页面
  await router.replace({ name: 'auth-login' })
}

// 3.页面DOM加载完成时获取当前登录账号信息
onMounted(async () => {
  await loadCurrentUser()
  accountStore.update(current_user.value)
})
</script>

<template>
  <a-layout has-sider class="h-full">
    <!-- 侧边栏 -->
    <a-layout-sider :width="240" class="min-h-screen bg-gray-50 p-2 shadow-none">
      <div class="bg-white h-full rounded-lg px-2 py-4 flex flex-col justify-between">
        <!-- 上半部分 -->
        <div class="">
          <!-- 顶部-->
          <div class="h-4 w-[110px]"></div>
          <!-- 创建AI应用按钮 -->
          <router-link :to="{ name: 'space-apps-list', query: { create_type: 'app' } }">
            <a-button type="primary" long class="rounded-lg mb-4">
              <template #icon>
                <icon-plus />
              </template>
              创建 AI 应用
            </a-button>
          </router-link>
          <!-- 侧边栏导航 -->
          <layout-sidebar />
        </div>
        <!-- 账号设置 -->
        <a-dropdown position="tl">
          <div
            class="flex items-center p-2 gap-2 transition-all cursor-pointer rounded-lg hover:bg-gray-100"
          >
            <!-- 头像 -->
            <a-avatar
              :size="32"
              class="text-sm bg-blue-700"
              :image-url="accountStore.account.avatar"
            >
              {{ accountStore.account.name[0] }}
            </a-avatar>
            <!-- 个人信息 -->
            <div class="flex flex-col">
              <div class="text-sm text-gray-900">{{ accountStore.account.name }}</div>
              <div class="text-xs text-gray-500">{{ accountStore.account.email }}</div>
            </div>
          </div>
          <template #content>
            <a-doption @click="settingModalVisible = true">
              <template #icon>
                <icon-settings />
              </template>
              账号设置
            </a-doption>
            <a-doption @click="handleLogout">
              <template #icon>
                <icon-poweroff />
              </template>
              退出登录
            </a-doption>
          </template>
        </a-dropdown>
      </div>
    </a-layout-sider>
    <!-- 右侧内容 -->
    <a-layout-content>
      <router-view />
    </a-layout-content>
    <!-- 设置模态窗 -->
    <setting-modal v-model:visible="settingModalVisible" />
  </a-layout>
</template>

<style scoped></style>
