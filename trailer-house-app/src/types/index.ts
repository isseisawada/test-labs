// ============================================================
// トレーラーハウス カスタマイザー - 型定義
// ============================================================

export type SkeletonSize = '6.0m' | '7.2m' | '9.0m';

export type ModuleCategory = '水回り' | '家具' | '収納' | '寝室';

export type ModuleType =
  | 'kitchen'
  | 'toilet'
  | 'shower'
  | 'bathtub'
  | 'loft'
  | 'sofa'
  | 'sofabed'
  | 'storage'
  | 'desk'
  | 'bed';

export type View = 'customizer' | '3d' | 'estimate';

export interface GridPosition {
  x: number; // グリッド列（0始まり）
  y: number; // グリッド行（0始まり）
}

export interface PlacedModule {
  id: string;
  type: ModuleType;
  position: GridPosition;
  rotation: 0 | 90 | 180 | 270; // 度
  gridW: number; // 占有グリッド幅
  gridH: number; // 占有グリッド高さ
}

export interface ModuleDefinition {
  type: ModuleType;
  label: string;
  category: ModuleCategory;
  defaultGridW: number;
  defaultGridH: number;
  price: number; // 円
  color: string; // プレビュー用
  icon: string;
  isWater: boolean; // 給排水必要
  hasHeightConstraint: boolean; // 高さ制約あり（ロフトなど）
  description: string;
  minAisle: number; // 最小動線（グリッド数）
}

export interface SkeletonDefinition {
  id: SkeletonSize;
  label: string;
  lengthM: number; // m
  widthM: number;  // m
  gridCols: number;
  gridRows: number;
  basePrice: number; // 円
  description: string;
}

export interface ConstraintViolation {
  id: string;
  type: 'collision' | 'aisle' | 'water' | 'height' | 'out_of_bounds';
  message: string;
  moduleIds: string[];
}

export interface EstimateItem {
  label: string;
  amount: number;
  note?: string;
}

export interface ContactForm {
  name: string;
  company: string;
  email: string;
  phone: string;
  prefecture: string;
  distance: number; // km（搬入距離）
  message: string;
  useCase: string;
}

export interface AppState {
  // 現在の画面
  currentView: View;
  setCurrentView: (view: View) => void;

  // スケルトンサイズ
  skeleton: SkeletonSize;
  setSkeleton: (size: SkeletonSize) => void;

  // 配置済みモジュール
  placedModules: PlacedModule[];
  addModule: (module: PlacedModule) => void;
  removeModule: (id: string) => void;
  updateModule: (id: string, updates: Partial<PlacedModule>) => void;
  rotateModule: (id: string) => void;

  // 選択中モジュール
  selectedModuleId: string | null;
  setSelectedModuleId: (id: string | null) => void;

  // 制約違反
  violations: ConstraintViolation[];
  setViolations: (violations: ConstraintViolation[]) => void;

  // 3Dビュー設定
  timeOfDay: 'day' | 'night';
  setTimeOfDay: (t: 'day' | 'night') => void;
  material: 'wood' | 'white' | 'dark';
  setMaterial: (m: 'wood' | 'white' | 'dark') => void;
  cameraView: 'exterior' | 'interior' | 'top';
  setCameraView: (v: 'exterior' | 'interior' | 'top') => void;

  // お問い合わせフォーム
  contactForm: ContactForm;
  updateContactForm: (updates: Partial<ContactForm>) => void;

  // 見積もり保存フラグ
  estimateSaved: boolean;
  setEstimateSaved: (b: boolean) => void;
}
