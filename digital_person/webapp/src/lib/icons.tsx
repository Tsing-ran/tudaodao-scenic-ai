// 语义图标注册表：全站统一 Phosphor 图标体系（2026-06-13 起，替代 emoji）。
// 约定：语义/内容图标用 weight="duotone"（视觉温度），功能图标用默认 regular 笔画；
// 颜色一律走 currentColor（外层容器给 text-primary/text-sweet），深浅色模式自适应。
import type { Icon } from '@phosphor-icons/react'
import {
  PersonSimpleWalk, Baby, PersonSimpleTaiChi, Heart,
  Bank, Mountains, Camera, BowlFood, FlowerLotus,
  Ticket, Compass, ChatCircleDots, GraduationCap, Trophy,
  Toilet, Armchair, FirstAid, Wheelchair,
  Smiley, SmileyWink, SmileyMeh, Binoculars, HeartStraight, HandsPraying,
  Student, Person, Hourglass, Path, BabyCarriage, PersonSimpleHike,
  Confetti, Coffee, Flag, ArrowsClockwise, Sun, Footprints,
} from '@phosphor-icons/react'

// 同行人（id 对应 i18n GROUPS）
export const GROUP_ICONS: Record<string, Icon> = {
  adult: PersonSimpleWalk,
  family_kids: Baby,
  senior: PersonSimpleTaiChi,
  couple: Heart,
}

// 兴趣（id 对应 i18n INTERESTS）
export const INTEREST_ICONS: Record<string, Icon> = {
  history: Bank,
  nature: Mountains,
  photo: Camera,
  food: BowlFood,
  culture: FlowerLotus,
}

// 足迹成就徽章（id 对应 trace.ts badges）
export const BADGE_ICONS: Record<string, Icon> = {
  meet: Ticket,
  footprint: Footprints,
  explorer: Compass,
  curious: ChatCircleDots,
  scholar: GraduationCap,
  shutter: Camera,
  pilgrim: Trophy,
}

// 设施速查（id 对应后端 /tour/facilities 的分组 id；后端 emoji 字段不再使用）
export const FACILITY_ICONS: Record<string, Icon> = {
  toilet: Toilet,
  food: BowlFood,
  rest: Armchair,
  medical: FirstAid,
  baby: Baby,
  access: Wheelchair,
}

// 自身情况标签（id 对应 i18n AGES/PACES/MOBILITIES/PURPOSES/FIRSTTIMES）
export const AGE_ICONS: Record<string, Icon> = {
  teen: Student, youth: PersonSimpleWalk, middle: Person, elder: PersonSimpleTaiChi,
}
export const PACE_ICONS: Record<string, Icon> = {
  half: Hourglass, day: Sun, deep: Path,
}
export const MOBILITY_ICONS: Record<string, Icon> = {
  stroller: BabyCarriage, wheelchair: Wheelchair, normal: PersonSimpleWalk, hiker: PersonSimpleHike,
}
export const PURPOSE_ICONS: Record<string, Icon> = {
  photo: Camera, kids_fun: Confetti, pray: HandsPraying, relax: Coffee, study: GraduationCap,
}
export const FIRSTTIME_ICONS: Record<string, Icon> = {
  first: Flag, return: ArrowsClockwise,
}

// 数字人情绪 → 图标 + 中文标签（对应 RAG [情绪:X]）
export const EMO_META: Record<string, { Icon: Icon; label: string }> = {
  happy: { Icon: Smiley, label: '开心' },
  excited: { Icon: SmileyWink, label: '兴奋' },
  neutral: { Icon: SmileyMeh, label: '平静' },
  calm: { Icon: SmileyMeh, label: '平静' },
  curious: { Icon: Binoculars, label: '好奇' },
  empathetic: { Icon: HeartStraight, label: '关切' },
  concerned: { Icon: HeartStraight, label: '关切' },
  apologetic: { Icon: HandsPraying, label: '抱歉' },
}
