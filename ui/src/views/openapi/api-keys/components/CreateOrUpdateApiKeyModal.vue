<script setup lang="ts">
import { ref, watch } from 'vue'
import { type ValidatedError } from '@arco-design/web-vue'
import { useCreateApiKey, useUpdateApiKey } from '@/hooks/use-api-key'

// 1.定义自定义组件所需数据
const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  api_key_id: { type: String, default: '', required: true },
  is_active: { type: Boolean, default: false, required: true },
  remark: { type: String, default: '', required: true },
  callback: { type: Function, required: false },
})
const emits = defineEmits([
  'update:visible',
  'update:api_key_id',
  'update:is_active',
  'update:remark',
])
const form = ref<Record<string, any>>({})
const formRef = ref(null)
const { loading: updateApiKeyLoading, handleUpdateApiKey } = useUpdateApiKey()
const { loading: createApiKeyLoading, handleCreateApiKey } = useCreateApiKey()

// 2.定义隐藏模态窗函数
const hideModal = () => {
  emits('update:visible', false)
}

// 3.定义表单提交函数
const saveApiKey = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  // 3.1 判断表单是否出错
  if (errors) return

  // 3.2 检测是新增还是更新，执行不同的操作
  if (props.api_key_id) {
    // 3.3 执行更新操作
    await handleUpdateApiKey(props.api_key_id, {
      is_active: Boolean(form.value?.is_active),
      remark: String(form.value?.remark),
    })
  } else {
    // 3.4 执行新增操作
    await handleCreateApiKey({
      is_active: Boolean(form.value?.is_active),
      remark: String(form.value?.remark),
    })
  }

  // 3.5 隐藏模态窗
  hideModal()
  props.callback && props.callback()
}

// 4.监听模态窗的显示or隐藏状态
watch(
  () => props.visible,
  (newValue) => {
    if (newValue) {
      // 4.1 显示模态窗的时候，将对应的值赋值给表单
      form.value = {
        is_active: props.is_active,
        remark: props.remark,
      }
    } else {
      // 4.2 隐藏模态窗的时候，将值清空
      emits('update:api_key_id', '')
      emits('update:is_active', false)
      emits('update:remark', '')
    }
  },
)
</script>

<template>
  <a-modal
    :visible="props.visible"
    @update:visible="(value) => emits('update:visible', value)"
    hide-title
    :footer="false"
  >
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <div class="text-lg font-bold text-gray-700">{{ api_key_id ? '更新' : '新增' }}秘钥</div>
      <a-button
        type="text"
        class="!text-gray-700"
        size="small"
        @click="() => emits('update:visible', false)"
      >
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>
    <!-- 中间表单 -->
    <div class="pt-6">
      <a-form ref="formRef" :model="form" layout="vertical" @submit="saveApiKey">
        <a-form-item field="is_active" label="秘钥状态">
          <a-switch v-model:model-value="form.is_active" />
        </a-form-item>
        <a-form-item field="remark" label="秘钥备注">
          <a-textarea
            v-model:model-value="form.remark"
            :max-length="100"
            show-word-limit
            placeholder="请输入秘钥备注，用于描述秘钥基础信息"
          />
        </a-form-item>
        <!-- 底部按钮 -->
        <div class="flex items-center justify-between">
          <div class=""></div>
          <a-space :size="16">
            <a-button class="rounded-lg" @click="() => emits('update:visible', false)">
              取消
            </a-button>
            <a-button
              :loading="updateApiKeyLoading || createApiKeyLoading"
              type="primary"
              html-type="submit"
              class="rounded-lg"
            >
              保存
            </a-button>
          </a-space>
        </div>
      </a-form>
    </div>
  </a-modal>
</template>

<style scoped></style>
