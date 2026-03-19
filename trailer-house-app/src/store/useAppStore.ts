// ============================================================
// Zustand グローバルストア
// ============================================================

import { create } from 'zustand';
import type { AppState, PlacedModule, SkeletonSize, View, ContactForm, ConstraintViolation } from '../types';

export const useAppStore = create<AppState>((set) => ({
  // 画面
  currentView: 'customizer',
  setCurrentView: (view: View) => set({ currentView: view }),

  // スケルトン
  skeleton: '7.2m',
  setSkeleton: (size: SkeletonSize) => set({ skeleton: size, placedModules: [] }),

  // モジュール
  placedModules: [],
  addModule: (module: PlacedModule) =>
    set((state) => ({ placedModules: [...state.placedModules, module] })),
  removeModule: (id: string) =>
    set((state) => ({ placedModules: state.placedModules.filter((m) => m.id !== id), selectedModuleId: null })),
  updateModule: (id: string, updates: Partial<PlacedModule>) =>
    set((state) => ({
      placedModules: state.placedModules.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),
  rotateModule: (id: string) =>
    set((state) => ({
      placedModules: state.placedModules.map((m) => {
        if (m.id !== id) return m;
        const newRot = ((m.rotation + 90) % 360) as 0 | 90 | 180 | 270;
        // 回転時はW/Hを入れ替え
        return { ...m, rotation: newRot, gridW: m.gridH, gridH: m.gridW };
      }),
    })),

  // 選択
  selectedModuleId: null,
  setSelectedModuleId: (id) => set({ selectedModuleId: id }),

  // 制約違反
  violations: [],
  setViolations: (violations: ConstraintViolation[]) => set({ violations }),

  // 3Dビュー
  timeOfDay: 'day',
  setTimeOfDay: (t) => set({ timeOfDay: t }),
  material: 'wood',
  setMaterial: (m) => set({ material: m }),
  cameraView: 'exterior',
  setCameraView: (v) => set({ cameraView: v }),

  // お問い合わせ
  contactForm: {
    name: '',
    company: '',
    email: '',
    phone: '',
    prefecture: '',
    distance: 50,
    message: '',
    useCase: '',
  },
  updateContactForm: (updates: Partial<ContactForm>) =>
    set((state) => ({ contactForm: { ...state.contactForm, ...updates } })),

  estimateSaved: false,
  setEstimateSaved: (b) => set({ estimateSaved: b }),
}));
