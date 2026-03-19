// ============================================================
// 見積もり計算ロジック
// ============================================================

import type { PlacedModule, SkeletonSize, EstimateItem } from '../types';
import { SKELETON_DEFINITIONS, MODULE_DEFINITIONS, ANCILLARY_COSTS } from '../data/definitions';

export function calculateEstimate(
  skeleton: SkeletonSize,
  modules: PlacedModule[],
  distance: number
): {
  items: EstimateItem[];
  subtotal: number;
  tax: number;
  total: number;
} {
  const skDef = SKELETON_DEFINITIONS.find((s) => s.id === skeleton)!;

  const items: EstimateItem[] = [];

  // 本体価格
  items.push({
    label: `本体（スケルトン ${skDef.label}）`,
    amount: skDef.basePrice,
    note: '基礎構造・外装・断熱・電気配線基本工事含む',
  });

  // オプション費用
  for (const placed of modules) {
    const def = MODULE_DEFINITIONS.find((d) => d.type === placed.type);
    if (def) {
      items.push({
        label: `　${def.label}`,
        amount: def.price,
        note: def.description,
      });
    }
  }

  // 付帯費用
  items.push({
    label: '設計・監理費',
    amount: ANCILLARY_COSTS.designFee,
    note: '基本設計・実施設計・工事監理',
  });
  items.push({
    label: '建築確認申請費',
    amount: ANCILLARY_COSTS.permitFee,
    note: '法的手続き代行費用',
  });
  items.push({
    label: '基礎工事費',
    amount: ANCILLARY_COSTS.foundationFee,
    note: '標準的な平地設置の場合',
  });
  items.push({
    label: '設置・搬入費',
    amount: ANCILLARY_COSTS.installFee,
    note: '設置調整・アンカー固定・接続工事',
  });

  // 輸送費
  const transportFee = ANCILLARY_COSTS.transportBase + distance * ANCILLARY_COSTS.transportPerKm;
  items.push({
    label: `輸送費（約${distance}km）`,
    amount: transportFee,
    note: '工場からの搬送費（地域・道路条件により変動）',
  });

  const subtotal = items.reduce((sum, item) => sum + item.amount, 0);
  const tax = Math.floor(subtotal * ANCILLARY_COSTS.taxRate);
  const total = subtotal + tax;

  return { items, subtotal, tax, total };
}

export function formatPrice(amount: number): string {
  return `¥${amount.toLocaleString('ja-JP')}`;
}
