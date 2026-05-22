import { get } from '@/utils/request'
import type {
  GetSkillResponse,
  GetSkillsCategoriesResponse,
  GetSkillsWithPageRequest,
  GetSkillsWithPageResponse,
} from '@/models/skill'

export const getSkillCategories = () => {
  return get<GetSkillsCategoriesResponse>('/skills/categories')
}

export const getSkillsWithPage = (params: GetSkillsWithPageRequest) => {
  return get<GetSkillsWithPageResponse>('/skills', { params })
}

export const getSkill = (skill_id: string) => {
  return get<GetSkillResponse>(`/skills/${skill_id}`)
}
