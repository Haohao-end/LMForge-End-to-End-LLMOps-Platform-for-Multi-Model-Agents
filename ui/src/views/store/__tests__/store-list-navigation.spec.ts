import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import PublicAppsListView from '@/views/store/public-apps/ListView.vue'
import WorkflowsListView from '@/views/store/workflows/ListView.vue'

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  getPublicApps: vi.fn(),
  getAppTags: vi.fn(),
  forkPublicApp: vi.fn(),
  getPublicWorkflows: vi.fn(),
  forkPublicWorkflow: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mocks.routerPush,
  }),
}))

vi.mock('@/services/public-app', () => ({
  getPublicApps: mocks.getPublicApps,
  getAppTags: mocks.getAppTags,
  forkPublicApp: mocks.forkPublicApp,
}))

vi.mock('@/services/public-workflow', () => ({
  getPublicWorkflows: mocks.getPublicWorkflows,
  forkPublicWorkflow: mocks.forkPublicWorkflow,
}))

const slotStub = {
  template: '<div><slot /></div>',
}

const globalStubs = {
  'a-spin': slotStub,
  'a-avatar': slotStub,
  'a-input-search': {
    template: '<input />',
  },
  'a-tag': slotStub,
  'a-tooltip': slotStub,
  'a-space': slotStub,
  'a-button': {
    template: '<button><slot /></button>',
  },
  'a-card': slotStub,
  'a-col': slotStub,
  'a-empty': slotStub,
  'a-row': slotStub,
  'a-pagination': slotStub,
  'icon-apps': slotStub,
  'icon-relation': slotStub,
  'icon-heart': slotStub,
  'icon-star': slotStub,
  'icon-branch': slotStub,
}

describe('store list navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mocks.getAppTags.mockResolvedValue({
      data: {
        tags: [{ id: 'assistant', name: '助手', priority: 1 }],
      },
    })

    mocks.getPublicApps.mockResolvedValue({
      data: {
        list: [
          {
            id: 'app-1',
            name: '应用一',
            icon: '',
            description: '应用描述',
            tags: [],
            creator_name: 'tester',
            creator_avatar: '',
            published_at: 1700000000,
            created_at: 1700000000,
            is_forked: false,
          },
        ],
        paginator: {
          total_record: 1,
        },
      },
    })

    mocks.getPublicWorkflows.mockResolvedValue({
      data: {
        list: [
          {
            id: 'workflow-1',
            name: '工作流一',
            icon: '',
            description: '工作流描述',
            tags: [],
            published_at: 1700000000,
            created_at: 1700000000,
            account_name: 'tester',
            account_avatar: '',
            is_forked: false,
          },
        ],
        paginator: {
          total_record: 1,
        },
      },
    })
  })

  it('navigates when clicking a public app card button', async () => {
    const wrapper = shallowMount(PublicAppsListView, {
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()

    const previewButton = wrapper.find('button.w-full')
    expect(previewButton.exists()).toBe(true)
    expect(previewButton.attributes('type')).toBe('button')

    await previewButton.trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith({
      name: 'store-public-apps-preview',
      params: { app_id: 'app-1' },
    })
  })

  it('navigates when clicking a workflow card button', async () => {
    const wrapper = shallowMount(WorkflowsListView, {
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()

    const previewButton = wrapper.find('button.w-full')
    expect(previewButton.exists()).toBe(true)
    expect(previewButton.attributes('type')).toBe('button')

    await previewButton.trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith({
      name: 'store-workflows-preview',
      params: { workflow_id: 'workflow-1' },
    })
  })

  it('renders fork actions without copy text', async () => {
    const appWrapper = shallowMount(PublicAppsListView, {
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()
    expect(appWrapper.text()).not.toContain('复制')
    expect(appWrapper.text()).not.toContain('已复制')

    const workflowWrapper = shallowMount(WorkflowsListView, {
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()
    expect(workflowWrapper.text()).not.toContain('复制')
    expect(workflowWrapper.text()).not.toContain('已复制')
  })
})
