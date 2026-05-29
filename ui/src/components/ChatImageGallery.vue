<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ChatArtifact } from '@/views/shared/chat-output'

type GalleryImage = Pick<ChatArtifact, 'name' | 'url' | 'mime_type' | 'extension'>

const props = defineProps({
  images: {
    type: Array as PropType<GalleryImage[]>,
    default: () => [],
  },
  title: {
    type: String,
    default: '',
  },
})
const { t } = useI18n()

const selectedIndex = ref(0)

const normalizedImages = computed(() => {
  return props.images.filter((image): image is GalleryImage => {
    return Boolean(image && String(image.url || '').trim())
  })
})

watch(
  () => normalizedImages.value.map(image => image.url).join('|'),
  () => {
    selectedIndex.value = 0
  },
  { immediate: true },
)

const activeImage = computed(() => {
  return normalizedImages.value[selectedIndex.value] || normalizedImages.value[0] || null
})

const hasMultipleImages = computed(() => normalizedImages.value.length > 1)

const activeMeta = computed(() => {
  const image = activeImage.value
  if (!image) return ''

  const metaParts = [
    image.extension || '',
    image.mime_type || '',
  ].filter(Boolean)

  return metaParts.join(' · ')
})

const sanitizeFilename = (value: string) => {
  return String(value || '')
    .trim()
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .replace(/\.+$/u, '')
}

const getUrlFilename = (url: string) => {
  try {
    return new URL(url).pathname.split('/').pop() || ''
  } catch {
    return ''
  }
}

const getExtension = (value: string) => {
  const normalized = String(value || '').trim()
  if (!normalized)
    return ''
  const index = normalized.lastIndexOf('.')
  if (index <= 0 || index >= normalized.length - 1)
    return ''
  return normalized.slice(index + 1)
}

const downloadFilename = computed(() => {
  const image = activeImage.value
  if (!image)
    return 'image'

  const fallbackName = sanitizeFilename(image.name || props.title || getUrlFilename(image.url) || 'image')
  const urlName = getUrlFilename(image.url)
  const extension = String(image.extension || '').trim().replace(/^\./, '') || getExtension(urlName) || getExtension(image.name || '')
  if (!extension)
    return fallbackName || 'image'

  const baseName = fallbackName.replace(new RegExp(`\\.${extension}$`, 'i'), '') || fallbackName
  return `${baseName}.${extension}`
})

const triggerDownloadLink = (href: string, filename: string) => {
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.rel = 'noreferrer'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const handleDownload = async () => {
  const image = activeImage.value
  if (!image)
    return

  const filename = downloadFilename.value
  const fetcher = globalThis.fetch
  if (typeof fetcher === 'function') {
    try {
      const response = await fetcher(image.url, { mode: 'cors' })
      if (!response.ok)
        throw new Error(`HTTP ${response.status}`)

      const blob = await response.blob()
      if (typeof URL.createObjectURL === 'function') {
        const objectUrl = URL.createObjectURL(blob)
        triggerDownloadLink(objectUrl, filename)
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
        return
      }
    } catch {
      // 回退到直链下载
    }
  }

  triggerDownloadLink(image.url, filename)
}

const selectImage = (index: number) => {
  selectedIndex.value = index
}
</script>

<template>
  <div
    v-if="normalizedImages.length > 0"
    class="chat-image-gallery"
  >
    <div class="chat-image-gallery__main">
      <div class="chat-image-gallery__frame">
        <a-image
          v-if="activeImage"
          class="chat-image-gallery__preview"
          :src="activeImage.url"
          :preview="true"
        />
        <div class="chat-image-gallery__actions">
          <button
            v-if="activeImage"
            type="button"
            class="chat-image-gallery__download"
            :data-download-filename="downloadFilename"
            :aria-label="t('chat.gallery.downloadAria', { filename: downloadFilename })"
            @click="handleDownload"
          >
            {{ t('chat.gallery.download') }}
          </button>
          <div
            v-if="hasMultipleImages"
            class="chat-image-gallery__counter"
          >
            {{ selectedIndex + 1 }}/{{ normalizedImages.length }}
          </div>
        </div>
      </div>

      <div class="chat-image-gallery__caption">
        <div class="chat-image-gallery__title">
          {{ title || activeImage?.name || t('chat.gallery.image') }}
        </div>
        <div
          v-if="activeMeta"
          class="chat-image-gallery__meta"
        >
          {{ activeMeta }}
        </div>
      </div>
    </div>

    <div
      v-if="hasMultipleImages"
      class="chat-image-gallery__thumbs"
    >
      <button
        v-for="(image, index) in normalizedImages"
        :key="`${image.url}-${index}`"
        type="button"
        :class="[
          'chat-image-gallery__thumb',
          index === selectedIndex ? 'chat-image-gallery__thumb--active' : '',
        ]"
        :aria-label="image.name || t('chat.gallery.imageIndexed', { index: index + 1 })"
        @click="selectImage(index)"
      >
        <img
          :src="image.url"
          :alt="image.name || t('chat.gallery.imageIndexed', { index: index + 1 })"
          class="chat-image-gallery__thumb-image"
        >
        <span class="chat-image-gallery__thumb-index">{{ index + 1 }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-image-gallery {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 3.2fr) 76px;
  gap: 14px;
  align-items: start;
}

.chat-image-gallery__main {
  min-width: 0;
}

.chat-image-gallery__frame {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.98));
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  aspect-ratio: 4 / 3;
}

.chat-image-gallery__preview {
  width: 100%;
  height: 100%;
}

.chat-image-gallery__actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  z-index: 2;
}

.chat-image-gallery__counter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.chat-image-gallery__download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.22);
  background: rgba(255, 255, 255, 0.9);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.chat-image-gallery__download:hover {
  transform: translateY(-1px);
  background: rgba(239, 246, 255, 0.98);
  border-color: rgba(37, 99, 235, 0.34);
}

.chat-image-gallery__caption {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-image-gallery__title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-word;
}

.chat-image-gallery__meta {
  font-size: 11px;
  color: #64748b;
  word-break: break-word;
}

.chat-image-gallery__thumbs {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  width: 76px;
  min-width: 76px;
  justify-content: end;
  align-content: start;
  max-height: 100%;
  overflow-y: auto;
  padding: 8px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.chat-image-gallery__thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  border-radius: 14px;
  border: 2px solid transparent;
  padding: 0;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.chat-image-gallery__thumb:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
}

.chat-image-gallery__thumb--active {
  border-color: rgba(37, 99, 235, 0.68);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.18);
}

.chat-image-gallery__thumb-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.chat-image-gallery__thumb-index {
  position: absolute;
  left: 4px;
  bottom: 4px;
  display: inline-flex;
  min-width: 16px;
  height: 16px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0 4px;
  font-size: 8px;
  font-weight: 700;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.9);
}

@media (max-width: 360px) {
  .chat-image-gallery {
    grid-template-columns: minmax(0, 1fr);
  }

  .chat-image-gallery__thumbs {
    display: flex;
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    width: auto;
    min-width: 0;
    padding-right: 0;
    padding-bottom: 2px;
  }

  .chat-image-gallery__thumb {
    width: 72px;
    min-width: 72px;
  }
}
</style>
