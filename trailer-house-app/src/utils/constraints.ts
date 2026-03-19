// ============================================================
// 制約チェックロジック
// ============================================================

import type { PlacedModule, ConstraintViolation, SkeletonSize } from '../types';
import { SKELETON_DEFINITIONS, MODULE_DEFINITIONS } from '../data/definitions';

function getSkeletonDef(size: SkeletonSize) {
  return SKELETON_DEFINITIONS.find((s) => s.id === size)!;
}

function getModuleDef(type: string) {
  return MODULE_DEFINITIONS.find((m) => m.type === type);
}

// 2つのモジュールが重なっているか
function overlaps(a: PlacedModule, b: PlacedModule): boolean {
  return (
    a.position.x < b.position.x + b.gridW &&
    a.position.x + a.gridW > b.position.x &&
    a.position.y < b.position.y + b.gridH &&
    a.position.y + a.gridH > b.position.y
  );
}

// 水回りモジュールが隣接しているか（1グリッド以内）
function isAdjacentWater(a: PlacedModule, b: PlacedModule): boolean {
  const margin = 2; // 2グリッド以内
  return (
    Math.abs(a.position.x - b.position.x) <= a.gridW + margin &&
    Math.abs(a.position.y - b.position.y) <= a.gridH + margin
  );
}

export function checkConstraints(
  modules: PlacedModule[],
  skeleton: SkeletonSize
): ConstraintViolation[] {
  const violations: ConstraintViolation[] = [];
  const skDef = getSkeletonDef(skeleton);

  // 境界チェック
  for (const mod of modules) {
    if (
      mod.position.x < 0 ||
      mod.position.y < 0 ||
      mod.position.x + mod.gridW > skDef.gridCols ||
      mod.position.y + mod.gridH > skDef.gridRows
    ) {
      violations.push({
        id: `oob-${mod.id}`,
        type: 'out_of_bounds',
        message: `「${getModuleDef(mod.type)?.label}」がフロア外に配置されています`,
        moduleIds: [mod.id],
      });
    }
  }

  // 衝突チェック
  for (let i = 0; i < modules.length; i++) {
    for (let j = i + 1; j < modules.length; j++) {
      if (overlaps(modules[i], modules[j])) {
        violations.push({
          id: `col-${modules[i].id}-${modules[j].id}`,
          type: 'collision',
          message: `「${getModuleDef(modules[i].type)?.label}」と「${getModuleDef(modules[j].type)?.label}」が重複しています`,
          moduleIds: [modules[i].id, modules[j].id],
        });
      }
    }
  }

  // 動線チェック（簡易版：通路幅チェック）
  // 配置モジュールの列が全グリッド幅を埋めていないか確認
  const waterModules = modules.filter((m) => {
    const def = getModuleDef(m.type);
    return def?.isWater;
  });

  // 水回りの近接チェック（給排水の集約）
  if (waterModules.length >= 2) {
    const firstWater = waterModules[0];
    for (let i = 1; i < waterModules.length; i++) {
      if (!isAdjacentWater(firstWater, waterModules[i])) {
        violations.push({
          id: `water-${waterModules[i].id}`,
          type: 'water',
          message: `水回り設備は給排水の効率化のため、できるだけ近接配置を推奨します`,
          moduleIds: [firstWater.id, waterModules[i].id],
        });
      }
    }
  }

  // ロフト高さチェック（天井高の関係で他の大型設備と同一エリア不可）
  const loftModules = modules.filter((m) => m.type === 'loft');
  for (const loft of loftModules) {
    const conflicting = modules.filter((m) => {
      if (m.id === loft.id) return false;
      // ロフト直下にバスタブ等の高さのあるものは不可
      if (m.type === 'bathtub' || m.type === 'shower') {
        return overlaps(loft, m);
      }
      return false;
    });
    if (conflicting.length > 0) {
      violations.push({
        id: `height-${loft.id}`,
        type: 'height',
        message: 'ロフト直下に高さのある設備は設置できません（天井高不足）',
        moduleIds: [loft.id, ...conflicting.map((m) => m.id)],
      });
    }
  }

  return violations;
}
