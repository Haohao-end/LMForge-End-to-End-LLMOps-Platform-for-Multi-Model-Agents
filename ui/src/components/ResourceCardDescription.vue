<script setup lang="ts">
import { useI18n } from 'vue-i18n'

withDefaults(defineProps<{
  text?: string
  fallback?: string
}>(), {
  text: '',
  fallback: '',
})
const { t } = useI18n()
</script>

<template>
  <div class="text-sm text-gray-600 h-[60px] line-clamp-3">
    {{ text || fallback || t('chat.resource.noDescription') }}
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
