<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// 只读版本的模型配置组件
const { t } = useI18n()
const props = defineProps({
  model_config: {
    type: Object,
    default: () => {
      return {}
    },
    required: true,
  },
})

const modelDisplayName = computed(() => {
  if (!props.model_config?.model) return t('appStudio.modelConfig.unsetModel')
  return props.model_config.model
})
</script>

<template>
  <div class="flex items-center gap-2">
    <a-tag color="blue" size="small">
      <template #icon>
        <icon-robot />
      </template>
      {{ modelDisplayName }}
    </a-tag>
  </div>
</template>

<style scoped></style>
