// ============================================================
// 3Dパース確認画面
// ============================================================

import React, { Suspense } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { Scene3D } from './Scene3D';

export const ThreeDView: React.FC = () => {
  const {
    timeOfDay, setTimeOfDay,
    material, setMaterial,
    cameraView, setCameraView,
    setCurrentView,
    skeleton, placedModules,
  } = useAppStore();

  return (
    <div className="threed-layout">
      {/* コントロールバー */}
      <div className="threed-controls">
        <div className="control-group">
          <span className="control-label">視点</span>
          {(['exterior', 'interior', 'top'] as const).map((v) => (
            <button
              key={v}
              className={`ctrl-btn ${cameraView === v ? 'active' : ''}`}
              onClick={() => setCameraView(v)}
            >
              {v === 'exterior' ? '🏠 外観' : v === 'interior' ? '🚪 内装' : '🦅 俯瞰'}
            </button>
          ))}
        </div>

        <div className="control-group">
          <span className="control-label">時間帯</span>
          <button
            className={`ctrl-btn ${timeOfDay === 'day' ? 'active' : ''}`}
            onClick={() => setTimeOfDay('day')}
          >
            ☀️ 昼
          </button>
          <button
            className={`ctrl-btn ${timeOfDay === 'night' ? 'active' : ''}`}
            onClick={() => setTimeOfDay('night')}
          >
            🌙 夜
          </button>
        </div>

        <div className="control-group">
          <span className="control-label">マテリアル</span>
          {(['wood', 'white', 'dark'] as const).map((m) => (
            <button
              key={m}
              className={`ctrl-btn ${material === m ? 'active' : ''}`}
              onClick={() => setMaterial(m)}
            >
              {m === 'wood' ? '🪵 木目' : m === 'white' ? '⬜ ホワイト' : '⬛ ダーク'}
            </button>
          ))}
        </div>
      </div>

      {/* 3Dビューポート */}
      <div className="threed-viewport">
        <Suspense fallback={
          <div className="loading-3d">
            <div className="loading-spinner" />
            <p>3Dモデルを読み込んでいます...</p>
          </div>
        }>
          <Scene3D timeOfDay={timeOfDay} material={material} cameraView={cameraView} />
        </Suspense>

        {/* オーバーレイ情報 */}
        <div className="viewport-overlay">
          <div className="overlay-info">
            <span>🖱️ ドラッグ：回転　ホイール：ズーム　右ドラッグ：移動</span>
          </div>
          <div className="overlay-spec">
            <span>スケルトン: {skeleton}</span>
            <span>オプション: {placedModules.length}個</span>
          </div>
        </div>
      </div>

      {/* ナビゲーション */}
      <div className="threed-nav">
        <button className="nav-btn back" onClick={() => setCurrentView('customizer')}>
          ← 間取りに戻る
        </button>
        <div className="nav-center">
          <p className="nav-hint">気に入ったデザインで見積もりを取得できます</p>
        </div>
        <button className="nav-btn next" onClick={() => setCurrentView('estimate')}>
          見積もりを確認する →
        </button>
      </div>
    </div>
  );
};
