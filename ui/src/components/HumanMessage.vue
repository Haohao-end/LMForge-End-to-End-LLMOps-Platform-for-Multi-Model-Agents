<script setup lang="ts">
// 1.定义自定义组件所需数据
const props = defineProps({
  account: {
    type: Object,
    default: () => {
      return {}
    },
    required: true,
  },
  query: { type: String, default: '', required: true },
})
</script>

<template>
  <div class="flex gap-2">
    <!-- 左侧头像 -->
    <a-avatar :size="30" shape="circle" class="flex-shrink-0" :image-url="props.account?.avatar" />
    <!-- 右侧昵称与消息 -->
    <div class="flex flex-col items-start gap-2">
      <!-- 账号昵称 -->
      <div class="text-gray-700 font-bold">{{ props.account?.name }}</div>
      <!-- 人类消息 -->
      <div class="bg-blue-100 border border-blue-200 text-gray-700 px-4 py-3 rounded-2xl break-all">
        {{ props.query }}
      </div>
    </div>
  </div>
</template>

<style scoped></style>
