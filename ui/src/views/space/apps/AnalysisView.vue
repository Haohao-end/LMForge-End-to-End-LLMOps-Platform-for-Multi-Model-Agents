<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { GridComponent, TooltipComponent } from 'echarts/components'
import moment from 'moment'
import { useGetAppAnalysis } from '@/hooks/use-analysis'
import OverviewIndicator from '@/components/OverviewIndicator.vue'

use([GridComponent, LineChart, CanvasRenderer, TooltipComponent])

// 1.定义页面所需数据
const route = useRoute()
const { loading: getAppAnalysisLoading, app_analysis, loadAppAnalysis } = useGetAppAnalysis()

// 2.计算趋势数据，让其符合ECharts的格式
const trendOption = computed(() => {
  const fields = [
    'total_messages_trend',
    'active_accounts_trend',
    'avg_of_conversation_messages_trend',
    'cost_consumption_trend',
  ]

  if (app_analysis.value) {
    return fields.reduce(
      (acc, field) => {
        acc[field] = {
          // 网格选项，设置上下左右间距
          grid: {
            top: 20,
            bottom: 20,
            left: 30,
            right: 30,
          },
          // 工具提示信息，鼠标移动到选项时显示卡片信息
          tooltip: {
            trigger: 'item', // 触发类型：'axis' 表示在坐标轴上触发，'item' 表示在数据项上触发
            axisPointer: {
              type: 'shadow', // 显示阴影指示器，表示在轴上
            },
          },
          // x轴设置为类别，并且将时间戳转换成日期
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: app_analysis.value[field]?.x_axis?.map((value: number) => {
              return moment(value * 1000).format('MMM D, YYYY')
            }),
            splitLine: {
              show: true, // 显示垂直网格线
              lineStyle: {
                color: '#eeeeee', // 网格线颜色
                width: 1, // 网格线宽度
                type: 'solid', // 网格线类型，'solid', 'dashed', 'dotted'
              },
            },
          },
          // y轴数据为值
          yAxis: {
            type: 'value',
          },
          // 添加y轴的数据系列
          series: [
            {
              data: app_analysis.value?.[field]?.y_axis,
              type: 'line',
            },
          ],
        }
        return acc
      },
      {} as Record<string, any>,
    )
  }
  return fields.reduce(
    (acc, field) => {
      acc[field] = {}
      return acc
    },
    {} as Record<string, any>,
  )
})

onMounted(() => {
  loadAppAnalysis(String(route.params?.app_id))
})
</script>

<template>
  <div class="px-6 py-5 overflow-scroll scrollbar-w-none">
    <!-- 概览指标 -->
    <div class="flex flex-col gap-5 mb-5">
      <!-- 标题 -->
      <div class="flex items-baseline gap-1">
        <div class="text-base text-gray-700 font-semibold">概览指标</div>
        <div class="text-xs text-gray-500">(过去7天)</div>
      </div>
      <!-- 指标卡片 -->
      <a-spin :loading="getAppAnalysisLoading">
        <div class="flex items-center gap-4">
          <overview-indicator
            title="全部会话数"
            help="反映 AI 每天的会话消息总数，在指定的时间范围内，用户对应用发起的请求总次数，一问一答记一次，用于衡量用户活跃度。"
            unit="次"
            :data="app_analysis?.total_messages?.data"
            :pop="app_analysis?.total_messages?.pop"
          >
            <template #icon>
              <icon-dashboard class="text-black" />
            </template>
          </overview-indicator>
          <overview-indicator
            title="活跃用户数"
            help="指定的发布渠道和时间范围内，至少完成一轮对话的总使用用户数量，用于衡量应用吸引力。"
            unit="人"
            :data="app_analysis?.active_accounts?.data"
            :pop="app_analysis?.active_accounts?.pop"
          >
            <template #icon>
              <icon-computer class="text-black" />
            </template>
          </overview-indicator>
          <overview-indicator
            title="平均会话互动数"
            help="反映每个会话用户的持续沟通次数，如果用户与 AI 进行了 10 轮对话，即为 10，该指标反映了用户粘性。"
            unit="次"
            :data="app_analysis?.avg_of_conversation_messages?.data"
            :pop="app_analysis?.avg_of_conversation_messages?.pop"
          >
            <template #icon>
              <icon-bulb class="text-black" />
            </template>
          </overview-indicator>
          <overview-indicator
            title="Token输出速度"
            help="衡量 LLM 的性能，统计 LLM 从请求到输出完毕这段期间内的 Tokens 输出速度。"
            unit="Ts/秒"
            :data="app_analysis?.token_output_rate?.data"
            :pop="app_analysis?.token_output_rate?.pop"
          >
            <template #icon>
              <icon-language class="text-black" />
            </template>
          </overview-indicator>
          <overview-indicator
            title="费用消耗"
            help="反映每日该应用请求语言模型的 Tokens 花费，用于成本控制。"
            unit="RMB"
            :data="app_analysis?.cost_consumption?.data"
            :pop="app_analysis?.cost_consumption?.pop"
          >
            <template #icon>
              <icon-code class="text-black" />
            </template>
          </overview-indicator>
        </div>
      </a-spin>
    </div>
    <!-- 指标详情 -->
    <div class="flex flex-col gap-5">
      <!-- 标题 -->
      <div class="flex items-baseline gap-1">
        <div class="text-base text-gray-700 font-semibold">详细指标</div>
        <div class="text-xs text-gray-500">(过去7天)</div>
      </div>
      <!-- 可视化图表 -->
      <a-spin :loading="getAppAnalysisLoading">
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col bg-white rounded-lg border border-gray-200 p-4 h-[300px]">
            <!-- 标题 -->
            <div class="flex items-center gap-2 mb-1 flex-shrink-0">
              <div class="text-gray-700 font-bold">全部会话数</div>
              <a-tooltip
                content="反映 AI 每天的会话消息总数，在指定的时间范围内，用户对应用发起的请求总次数，一问一答记一次，用于衡量用户活跃度。"
              >
                <icon-question-circle-fill />
              </a-tooltip>
            </div>
            <!-- 副标题 -->
            <div class="text-gray-500 mb-1 flex-shrink-0">过去7天</div>
            <!-- 可视化图表 -->
            <div class="w-full flex-1">
              <v-chart
                :init-options="{}"
                :option="trendOption?.total_messages_trend"
                :autoresize="true"
              />
            </div>
          </div>
          <div class="flex flex-col bg-white rounded-lg border border-gray-200 p-4 h-[300px]">
            <!-- 标题 -->
            <div class="flex items-center gap-2 mb-1 flex-shrink-0">
              <div class="text-gray-700 font-bold">活跃用户数</div>
              <a-tooltip
                content="指定的发布渠道和时间范围内，至少完成一轮对话的总使用用户数量，用于衡量应用吸引力。"
              >
                <icon-question-circle-fill />
              </a-tooltip>
            </div>
            <!-- 副标题 -->
            <div class="text-gray-500 mb-1 flex-shrink-0">过去7天</div>
            <!-- 可视化图表 -->
            <div class="w-full flex-1">
              <v-chart
                :init-options="{}"
                :option="trendOption?.active_accounts_trend"
                :autoresize="true"
              />
            </div>
          </div>
          <div class="flex flex-col bg-white rounded-lg border border-gray-200 p-4 h-[300px]">
            <!-- 标题 -->
            <div class="flex items-center gap-2 mb-1 flex-shrink-0">
              <div class="text-gray-700 font-bold">平均会话互动数</div>
              <a-tooltip
                content="反映每个会话用户的持续沟通次数，如果用户与 AI 进行了 10 轮对话，即为 10，该指标反映了用户粘性。"
              >
                <icon-question-circle-fill />
              </a-tooltip>
            </div>
            <!-- 副标题 -->
            <div class="text-gray-500 mb-1 flex-shrink-0">过去7天</div>
            <!-- 可视化图表 -->
            <div class="w-full flex-1">
              <v-chart
                :init-options="{}"
                :option="trendOption?.avg_of_conversation_messages_trend"
                :autoresize="true"
              />
            </div>
          </div>
          <div class="flex flex-col bg-white rounded-lg border border-gray-200 p-4 h-[300px]">
            <!-- 标题 -->
            <div class="flex items-center gap-2 mb-1 flex-shrink-0">
              <div class="text-gray-700 font-bold">费用消耗</div>
              <a-tooltip content="反映每日该应用请求语言模型的 Tokens 花费，用于成本控制。">
                <icon-question-circle-fill />
              </a-tooltip>
            </div>
            <!-- 副标题 -->
            <div class="text-gray-500 mb-1 flex-shrink-0">过去7天</div>
            <!-- 可视化图表 -->
            <div class="w-full flex-1">
              <v-chart
                :init-options="{}"
                :option="trendOption?.cost_consumption_trend"
                :autoresize="true"
              />
            </div>
          </div>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped></style>
