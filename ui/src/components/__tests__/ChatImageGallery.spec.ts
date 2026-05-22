import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import ChatImageGallery from '../ChatImageGallery.vue'

describe('ChatImageGallery.vue', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  const mountGallery = (props: Record<string, unknown> = {}) =>
    mount(ChatImageGallery, {
      props: {
        images: [],
        ...props,
      },
      global: {
        stubs: {
          'a-image': {
            props: ['src', 'preview'],
            template: '<div class="image-stub" :data-src="src"></div>',
          },
        },
      },
    })

  it('shows a thumbnail strip and switches the active preview when a thumbnail is clicked', async () => {
    const wrapper = mountGallery({
      title: '上海初夏旅行穿搭',
      images: [
        { name: 'img-1.png', url: 'https://example.com/1.png', extension: 'png' },
        { name: 'img-2.png', url: 'https://example.com/2.png', extension: 'png' },
        { name: 'img-3.png', url: 'https://example.com/3.png', extension: 'png' },
      ],
    })

    expect(wrapper.find('.chat-image-gallery').exists()).toBe(true)
    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/1.png')
    expect(wrapper.findAll('.chat-image-gallery__thumb')).toHaveLength(3)
    expect(wrapper.text()).toContain('1/3')

    await wrapper.findAll('.chat-image-gallery__thumb')[2].trigger('click')

    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/3.png')
    expect(wrapper.text()).toContain('3/3')
  })

  it('hides thumbnails when only one image exists', () => {
    const wrapper = mountGallery({
      images: [{ name: 'img-1.png', url: 'https://example.com/1.png', extension: 'png' }],
    })

    expect(wrapper.find('.chat-image-gallery').exists()).toBe(true)
    expect(wrapper.find('.chat-image-gallery__thumbs').exists()).toBe(false)
    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/1.png')
  })

  it('exposes a download action for the active image and updates the filename when selection changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(new Blob(['image'], { type: 'image/png' })),
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    const wrapper = mountGallery({
      title: '上海初夏旅行穿搭',
      images: [
        { name: 'img-1.png', url: 'https://example.com/1.png', extension: 'png' },
        { name: 'detail.png', url: 'https://example.com/2.png', extension: 'png' },
      ],
    })

    const downloadButton = wrapper.get('.chat-image-gallery__download')
    expect(downloadButton.attributes('data-download-filename')).toBe('img-1.png')

    await wrapper.findAll('.chat-image-gallery__thumb')[1].trigger('click')

    expect(wrapper.get('.chat-image-gallery__download').attributes('data-download-filename')).toBe('detail.png')

    await wrapper.get('.chat-image-gallery__download').trigger('click')
    expect(fetchMock).toHaveBeenCalledWith('https://example.com/2.png', { mode: 'cors' })
  })
})
