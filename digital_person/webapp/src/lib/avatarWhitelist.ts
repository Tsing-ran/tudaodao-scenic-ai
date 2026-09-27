// 唇形已体检白名单；GPU 体检通过后在此扩充。
// 背景：未经体检的底图（含人形/面孔剪影的合成图）会毒化 Ditto 源处理、导致上镜时嘴唇坍缩（step 4 风险）。
// 与 kiosk 同一道理——游客端只允许切换到已过 lipmatrix 开口体检的形象；其余置灰不可选。
export const LIP_VETTED = new Set<string>([
  'dh_lingshan', 'dh_gugong', 'F1_modern', 'F2_hanfu', 'M1_modern', 'custom_20260713_201715',
  // 2026-07-14 lipmatrix 逐帧体检通过（开口清晰、无坍缩）：
  'F4_qipao', 'F5_ethnic', 'F6_mature', 'M3_youth', 'M4_business',
  // 体检偏弱（几乎不张口）暂不放：F3_youth / M2_scholar / custom_20260713_183121
])

export const isLipVetted = (id: string): boolean => LIP_VETTED.has(id)
