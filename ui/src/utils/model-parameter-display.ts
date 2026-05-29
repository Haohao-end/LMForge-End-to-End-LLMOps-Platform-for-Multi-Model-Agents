import type { ComposerTranslation } from 'vue-i18n'

type TranslateFn = ComposerTranslation

const PARAMETER_LABEL_KEY_MAP: Record<string, string> = {
  temperature: 'appStudio.modelConfig.parameterLabels.temperature',
  top_p: 'appStudio.modelConfig.parameterLabels.topP',
  max_tokens: 'appStudio.modelConfig.parameterLabels.maxTokens',
  frequency_penalty: 'appStudio.modelConfig.parameterLabels.frequencyPenalty',
  presence_penalty: 'appStudio.modelConfig.parameterLabels.presencePenalty',
}

const PARAMETER_HELP_KEY_MAP: Record<string, string> = {
  temperature: 'appStudio.modelConfig.parameterHelps.temperature',
  top_p: 'appStudio.modelConfig.parameterHelps.topP',
  max_tokens: 'appStudio.modelConfig.parameterHelps.maxTokens',
  frequency_penalty: 'appStudio.modelConfig.parameterHelps.frequencyPenalty',
  presence_penalty: 'appStudio.modelConfig.parameterHelps.presencePenalty',
}

export const getModelParameterDisplayLabel = (
  parameterName: string,
  fallbackLabel: string,
  t: TranslateFn,
) => {
  const key = PARAMETER_LABEL_KEY_MAP[parameterName]
  return key ? t(key) : (fallbackLabel || parameterName)
}

export const getModelParameterDisplayHelp = (
  parameterName: string,
  fallbackHelp: string,
  t: TranslateFn,
) => {
  const key = PARAMETER_HELP_KEY_MAP[parameterName]
  return key ? t(key) : fallbackHelp
}

export const getModelParameterLabelKey = (parameterName: string) => {
  return PARAMETER_LABEL_KEY_MAP[parameterName] || ''
}
