// ============================================================
// 右パネル：リアルタイム見積もり
// ============================================================

import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SKELETON_DEFINITIONS, MODULE_DEFINITIONS } from '../../data/definitions';
import { calculateEstimate, formatPrice } from '../../utils/estimate';

export const EstimatePanel: React.FC = () => {
  const { skeleton, placedModules, violations, setCurrentView } = useAppStore();

  const { subtotal, tax, total } = calculateEstimate(skeleton, placedModules, 50);
  const skDef = SKELETON_DEFINITIONS.find((s) => s.id === skeleton)!;

  const optionTotal = placedModules.reduce((sum, m) => {
    const def = MODULE_DEFINITIONS.find((d) => d.type === m.type);
    return sum + (def?.price ?? 0);
  }, 0);

  return (
    <div className="estimate-panel">
      <div className="panel-header">
        <h2 className="panel-title">リアルタイム見積もり</h2>
        <p className="panel-hint">配置に応じて自動更新</p>
      </div>

      {/* サマリー */}
      <div className="estimate-summary">
        <div className="summary-row">
          <span>本体価格</span>
          <span>{formatPrice(skDef.basePrice)}</span>
        </div>
        <div className="summary-row">
          <span>オプション合計</span>
          <span>{formatPrice(optionTotal)}</span>
        </div>
        <div className="summary-row">
          <span>付帯費用（概算）</span>
          <span>{formatPrice(total - skDef.basePrice - optionTotal - Math.floor((total - skDef.basePrice - optionTotal) * 0.1))}</span>
        </div>
        <div className="summary-divider" />
        <div className="summary-row sub">
          <span>小計</span>
          <span>{formatPrice(subtotal)}</span>
        </div>
        <div className="summary-row sub">
          <span>消費税（10%）</span>
          <span>{formatPrice(tax)}</span>
        </div>
        <div className="summary-row total">
          <span>合計（税込）</span>
          <span className="total-amount">{formatPrice(total)}</span>
        </div>
      </div>

      {/* 配置済みオプション */}
      {placedModules.length > 0 && (
        <div className="option-breakdown">
          <h3 className="breakdown-title">配置済みオプション</h3>
          {placedModules.map((mod) => {
            const def = MODULE_DEFINITIONS.find((d) => d.type === mod.type);
            if (!def) return null;
            return (
              <div key={mod.id} className="breakdown-row">
                <span>{def.icon} {def.label}</span>
                <span>{formatPrice(def.price)}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* 制約違反 */}
      {violations.length > 0 && (
        <div className="violations-box">
          <div className="violations-title">⚠ 配置の注意点</div>
          {violations.map((v) => (
            <div key={v.id} className="violation-item">{v.message}</div>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="estimate-cta">
        <button
          className="cta-btn primary"
          onClick={() => setCurrentView('3d')}
        >
          3Dパースで確認する →
        </button>
        <button
          className="cta-btn secondary"
          onClick={() => setCurrentView('estimate')}
        >
          詳細見積もりを見る
        </button>
      </div>

      <p className="estimate-note">
        ※ 上記は概算です。実際の価格は現地調査・詳細設計後に確定します。
      </p>
    </div>
  );
};
