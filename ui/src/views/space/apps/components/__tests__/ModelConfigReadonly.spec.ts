import { describe, expect, it } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import ModelConfigReadonly from '@/views/space/apps/components/ModelConfigReadonly.vue'

const slotStub = {
  template: '<div><slot /></div>',
}

describe('ModelConfigReadonly', () => {
  it('only renders the model name without dialog rounds', () => {
    const wrapper = shallowMount(ModelConfigReadonly, {
      props: {
        model_config: {
          model: 'gpt-4o',
        },
      },
      global: {
        stubs: {
          'a-tag': slotStub,
          'icon-robot': slotStub,
        },
      },
    })

    expect(wrapper.text()).toContain('gpt-4o')
    expect(wrapper.text()).not.toContain('对话轮次')
  })
})
