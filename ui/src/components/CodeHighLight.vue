<script setup lang="ts">
import { onMounted, ref } from 'vue'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github.css'

// 1.定义自定义组件所需数据
const props = defineProps({
  language: { type: String, default: '', required: true },
})
const codeElement = ref(null)

// 2.组件在挂载成功后高亮代码
onMounted(() => {
  if (codeElement.value) hljs.highlightElement(codeElement.value)
})
</script>

<template>
  <pre
    class="mb-4"
  ><code ref="codeElement" :class="`language-${props.language} whitespace-pre`"><slot></slot></code></pre>
</template>

<style scoped></style>
