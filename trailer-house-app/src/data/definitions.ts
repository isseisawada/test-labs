// ============================================================
// マスターデータ定義（JSON形式で価格・仕様を管理）
// ============================================================

import type { ModuleDefinition, SkeletonDefinition } from '../types';

export const GRID_UNIT = 60; // px per grid cell (60px = 0.3m)

export const SKELETON_DEFINITIONS: SkeletonDefinition[] = [
  {
    id: '6.0m',
    label: '6.0m × 2.4m',
    lengthM: 6.0,
    widthM: 2.4,
    gridCols: 20, // 6.0m / 0.3m
    gridRows: 8,  // 2.4m / 0.3m
    basePrice: 4_500_000,
    description: 'コンパクトな1LDK向け。ソロや2人暮らしに最適。',
  },
  {
    id: '7.2m',
    label: '7.2m × 2.4m',
    lengthM: 7.2,
    widthM: 2.4,
    gridCols: 24,
    gridRows: 8,
    basePrice: 5_500_000,
    description: '標準サイズ。水回り完備＋居室が快適に確保できる。',
  },
  {
    id: '9.0m',
    label: '9.0m × 2.4m',
    lengthM: 9.0,
    widthM: 2.4,
    gridCols: 30,
    gridRows: 8,
    basePrice: 7_200_000,
    description: '広々とした空間設計。商業利用・ファミリー向け。',
  },
];

export const MODULE_DEFINITIONS: ModuleDefinition[] = [
  {
    type: 'kitchen',
    label: 'キッチン',
    category: '水回り',
    defaultGridW: 5,
    defaultGridH: 2,
    price: 650_000,
    color: '#B8D4E8',
    icon: '🍳',
    isWater: true,
    hasHeightConstraint: false,
    description: 'IHコンロ・シンク・収納付き。L型対応可。',
    minAisle: 2,
  },
  {
    type: 'toilet',
    label: 'トイレ',
    category: '水回り',
    defaultGridW: 2,
    defaultGridH: 3,
    price: 280_000,
    color: '#C8E6C9',
    icon: '🚽',
    isWater: true,
    hasHeightConstraint: false,
    description: 'タンクレストイレ標準装備。温水洗浄便座付き。',
    minAisle: 1,
  },
  {
    type: 'shower',
    label: 'シャワー',
    category: '水回り',
    defaultGridW: 2,
    defaultGridH: 2,
    price: 220_000,
    color: '#B3E5FC',
    icon: '🚿',
    isWater: true,
    hasHeightConstraint: false,
    description: 'ユニットシャワーブース。防水加工済み。',
    minAisle: 1,
  },
  {
    type: 'bathtub',
    label: 'バスタブ',
    category: '水回り',
    defaultGridW: 3,
    defaultGridH: 2,
    price: 380_000,
    color: '#80DEEA',
    icon: '🛁',
    isWater: true,
    hasHeightConstraint: false,
    description: 'ジェット機能付きバスタブ。追い炊き対応可。',
    minAisle: 1,
  },
  {
    type: 'loft',
    label: 'ロフト',
    category: '寝室',
    defaultGridW: 6,
    defaultGridH: 4,
    price: 420_000,
    color: '#FFE082',
    icon: '🏠',
    isWater: false,
    hasHeightConstraint: true,
    description: '天井高2.4m以上が必要。ハシゴ付き。収納兼用可。',
    minAisle: 2,
  },
  {
    type: 'sofa',
    label: 'ソファ',
    category: '家具',
    defaultGridW: 4,
    defaultGridH: 2,
    price: 180_000,
    color: '#FFCCBC',
    icon: '🛋️',
    isWater: false,
    hasHeightConstraint: false,
    description: '3人掛けファブリックソファ。カラー選択可。',
    minAisle: 2,
  },
  {
    type: 'sofabed',
    label: 'ソファベッド',
    category: '家具',
    defaultGridW: 4,
    defaultGridH: 2,
    price: 240_000,
    color: '#FFAB91',
    icon: '🛋️',
    isWater: false,
    hasHeightConstraint: false,
    description: '展開時シングル相当。来客対応に最適。',
    minAisle: 2,
  },
  {
    type: 'storage',
    label: '収納',
    category: '収納',
    defaultGridW: 2,
    defaultGridH: 1,
    price: 120_000,
    color: '#D7CCC8',
    icon: '🗄️',
    isWater: false,
    hasHeightConstraint: false,
    description: '壁面収納ユニット。高さ・幅カスタマイズ可。',
    minAisle: 1,
  },
  {
    type: 'desk',
    label: 'デスク',
    category: '家具',
    defaultGridW: 3,
    defaultGridH: 2,
    price: 95_000,
    color: '#F5F5F5',
    icon: '💻',
    isWater: false,
    hasHeightConstraint: false,
    description: 'ワーキングデスク＋チェア付き。USB給電対応。',
    minAisle: 2,
  },
  {
    type: 'bed',
    label: 'ベッド',
    category: '寝室',
    defaultGridW: 4,
    defaultGridH: 3,
    price: 160_000,
    color: '#E1BEE7',
    icon: '🛏️',
    isWater: false,
    hasHeightConstraint: false,
    description: 'セミダブルベッド標準。マットレス付き。',
    minAisle: 2,
  },
];

// 付帯費用定義
export const ANCILLARY_COSTS = {
  designFee: 350_000,      // 設計費
  permitFee: 180_000,      // 建築確認申請費
  foundationFee: 450_000,  // 基礎工事費
  installFee: 280_000,     // 設置費
  transportBase: 150_000,  // 輸送費（基本）
  transportPerKm: 500,     // 輸送費（km単価）
  taxRate: 0.10,           // 消費税率
};

// 都道府県リスト
export const PREFECTURES = [
  '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
  '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
  '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
  '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
  '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
  '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
  '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県',
];

export const USE_CASES = [
  '住居（個人）',
  '民泊・ゲストハウス',
  'オフィス・テレワーク',
  'カフェ・飲食店',
  'ショップ・店舗',
  'グランピング施設',
  '別荘・セカンドハウス',
  'その他',
];
