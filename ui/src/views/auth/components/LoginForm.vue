<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCredentialStore } from '@/stores/credential'
import { Message, type ValidatedError } from '@arco-design/web-vue'
import { usePasswordLogin } from '@/hooks/use-auth'
import { useProvider } from '@/hooks/use-oauth'

// 1.定义自定义组件所需数据
const errorMessage = ref('')
const loginForm = ref({ email: '', password: '' })
const credentialStore = useCredentialStore()
const router = useRouter()
const { loading: passwordLoginLoading, authorization, handlePasswordLogin } = usePasswordLogin()
const { loading: providerLoading, redirect_url, handleProvider } = useProvider()

// 2.定义忘记密码点击事件
const forgetPassword = () => Message.error('忘记密码可以重新创建新账号,登陆账号不能和之前的重复')

const TodoMessage = () => Message.error('暂未提供该服务,请使用账号密码或者GitHub登陆')

// 3.定义github第三方授权认证登录
const githubLogin = async () => {
  // 3.1 调用处理器获取提供者重定向地址
  await handleProvider('github')

  // 3.2 跳转到重定向地址
  window.location.href = redirect_url.value
}

// 4.账号密码登录
const handleSubmit = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  // 4.1 判断表单是否校验成功
  if (errors) return

  // 4.2 如果没有出错则发起请求进行登录
  try {
    // 4.3 发起账号密码登录，并且将loading设置为true
    await handlePasswordLogin(loginForm.value.email, loginForm.value.password)
    Message.success('登录成功，正在跳转')
    credentialStore.update(authorization.value)
    await router.replace({ path: '/home' })
  } catch (error: any) {
    // 4.4 添加错误信息并清除密码
    errorMessage.value = error.message
    loginForm.value.password = ''
  }
}
</script>
<template>
  <div class="w-full h-full flex items-center justify-center bg-white from-gray-100 to-white px-4 py-8">
    <div class="bg-white shadow-xl rounded-2xl p-8 w-full max-w-xl space-y-6 transition-all duration-300">
      <!-- 标题 -->
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Open Coze</h1>
        <p class="text-sm text-gray-500 mt-1">开发你的 AI Agent</p>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
        {{ errorMessage }}
      </div>

      <!-- 登录表单 -->
      <a-form
        :model="loginForm"
        @submit="handleSubmit"
        layout="vertical"
        size="large"
        class="space-y-4"
      >
        <a-form-item
          field="email"
          :rules="[{ type: 'email', required: true, message: '登录账号必须是合法的邮箱' }]"
          :validate-trigger="['change', 'blur']"
          hide-label
        >
          <a-input v-model="loginForm.email" size="large" placeholder="登录账号">
            <template #prefix><icon-user /></template>
          </a-input>
        </a-form-item>

        <a-form-item
          field="password"
          :rules="[{ required: true, message: '账号密码不能为空' }]"
          :validate-trigger="['change', 'blur']"
          hide-label
        >
          <a-input-password v-model="loginForm.password" size="large" placeholder="账号密码">
            <template #prefix><icon-lock /></template>
          </a-input-password>
        </a-form-item>

        <div class="flex justify-between text-sm text-gray-600">
          <a-checkbox>记住密码</a-checkbox>
          <a-link @click="forgetPassword">忘记密码?</a-link>
        </div>

        <a-button
          :loading="passwordLoginLoading"
          size="large"
          type="primary"
          html-type="submit"
          long
          class="mt-2"
        >
          登录
        </a-button>

        <a-divider class="my-4">第三方授权</a-divider>

        <div class="grid grid-cols-2 gap-3">
          <a-button @click="TodoMessage" size="large" type="dashed" long>
            <template  #icon><icon-wechat /></template> 微信
          </a-button>
          <a-button @click="TodoMessage" size="large" type="dashed" long>
            <template #icon><icon-qq /></template> QQ
          </a-button>
          <a-button @click="TodoMessage" size="large" type="dashed" long>
            <template #icon><icon-google /></template> Google
          </a-button>
          <a-button
            :loading="providerLoading"
            :disabled="providerLoading"
            size="large"
            type="dashed"
            long
            @click="githubLogin"
          >
            <template #icon><icon-github /></template> GitHub
          </a-button>
        </div>
      </a-form>

      <!-- Footer -->
      <div class="pt-4 text-xs text-center text-gray-400 border-t">
        © {{ new Date().getFullYear() }} Powered by AI Agent
      </div>
    </div>
  </div>
</template>

<style scoped></style>
