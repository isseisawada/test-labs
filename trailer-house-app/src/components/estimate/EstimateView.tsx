// ============================================================
// 詳細見積もり・お問い合わせ画面
// ============================================================

import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { calculateEstimate, formatPrice } from '../../utils/estimate';
import { PREFECTURES, USE_CASES } from '../../data/definitions';

export const EstimateView: React.FC = () => {
  const {
    skeleton,
    placedModules,
    contactForm,
    updateContactForm,
    setCurrentView,
    setEstimateSaved,
  } = useAppStore();

  const [formSubmitted, setFormSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState<'estimate' | 'contact'>('estimate');

  const { items, subtotal, tax, total } = calculateEstimate(
    skeleton,
    placedModules,
    contactForm.distance
  );

  const handlePrint = () => {
    window.print();
  };

  const handleSave = () => {
    const data = {
      skeleton,
      modules: placedModules,
      estimate: { items, subtotal, tax, total },
      savedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trailerhause_estimate_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setEstimateSaved(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 実際の実装ではAPIに送信
    setFormSubmitted(true);
  };

  return (
    <div className="estimate-view">
      {/* タブ */}
      <div className="estimate-tabs">
        <button
          className={`est-tab ${activeTab === 'estimate' ? 'active' : ''}`}
          onClick={() => setActiveTab('estimate')}
        >
          見積もり詳細
        </button>
        <button
          className={`est-tab ${activeTab === 'contact' ? 'active' : ''}`}
          onClick={() => setActiveTab('contact')}
        >
          お問い合わせ
        </button>
      </div>

      {activeTab === 'estimate' ? (
        <div className="estimate-detail">
          {/* ヘッダー */}
          <div className="estimate-header">
            <div>
              <h1 className="estimate-title">見積もり明細</h1>
              <p className="estimate-date">発行日：{new Date().toLocaleDateString('ja-JP')}</p>
            </div>
            <div className="estimate-actions">
              <button className="action-btn" onClick={handlePrint}>🖨️ 印刷・PDF</button>
              <button className="action-btn" onClick={handleSave}>💾 保存</button>
            </div>
          </div>

          {/* スペック */}
          <div className="spec-card">
            <div className="spec-row">
              <span className="spec-key">スケルトンサイズ</span>
              <span className="spec-val">{skeleton}</span>
            </div>
            <div className="spec-row">
              <span className="spec-key">オプション数</span>
              <span className="spec-val">{placedModules.length}個</span>
            </div>
            <div className="spec-row">
              <span className="spec-key">搬入距離（仮）</span>
              <span className="spec-val">{contactForm.distance}km</span>
            </div>
          </div>

          {/* 距離スライダー */}
          <div className="distance-slider-box">
            <label className="slider-label">
              搬入距離を調整（輸送費に反映）：<strong>{contactForm.distance}km</strong>
            </label>
            <input
              type="range"
              min={10}
              max={500}
              step={10}
              value={contactForm.distance}
              onChange={(e) => updateContactForm({ distance: Number(e.target.value) })}
              className="slider"
            />
            <div className="slider-range">
              <span>10km</span>
              <span>500km</span>
            </div>
          </div>

          {/* 明細テーブル */}
          <table className="estimate-table">
            <thead>
              <tr>
                <th>項目</th>
                <th>金額</th>
                <th>備考</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i}>
                  <td>{item.label}</td>
                  <td className="amount-cell">{formatPrice(item.amount)}</td>
                  <td className="note-cell">{item.note}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="subtotal-row">
                <td>小計</td>
                <td className="amount-cell">{formatPrice(subtotal)}</td>
                <td></td>
              </tr>
              <tr className="tax-row">
                <td>消費税（10%）</td>
                <td className="amount-cell">{formatPrice(tax)}</td>
                <td></td>
              </tr>
              <tr className="total-row">
                <td><strong>合計（税込）</strong></td>
                <td className="amount-cell total-amount">{formatPrice(total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>

          {/* 注記 */}
          <div className="estimate-notes">
            <p>※ 本見積もりは概算です。現地調査・詳細設計後に正式見積もりを提出します。</p>
            <p>※ 基礎工事費は標準的な平地設置の場合です。地盤条件により変動します。</p>
            <p>※ 輸送費は工場からの距離を基準とした概算です。実際の経路・道路条件により変動します。</p>
            <p>※ 本見積もりの有効期限は発行日より30日間です。</p>
          </div>

          {/* CTA */}
          <div className="estimate-cta-bar">
            <div className="cta-highlight">
              <span className="cta-label">この設計でお問い合わせ</span>
              <span className="cta-price">{formatPrice(total)}</span>
            </div>
            <button className="cta-main-btn" onClick={() => setActiveTab('contact')}>
              無料相談・お問い合わせ →
            </button>
          </div>
        </div>
      ) : (
        <div className="contact-section">
          {formSubmitted ? (
            <div className="submit-success">
              <div className="success-icon">✅</div>
              <h2>お問い合わせありがとうございます</h2>
              <p>担当者より3営業日以内にご連絡いたします。</p>
              <p>お急ぎの場合は <strong>0120-XXX-XXXX</strong> までお電話ください。</p>
              <button className="back-btn" onClick={() => setCurrentView('customizer')}>
                間取り設計に戻る
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="contact-form">
              <div className="form-header">
                <h2 className="form-title">お問い合わせフォーム</h2>
                <p className="form-sub">見積もりデータを添えて送信されます。無料でご相談いただけます。</p>
              </div>

              <div className="form-grid">
                <div className="form-group required">
                  <label>お名前</label>
                  <input
                    type="text"
                    required
                    placeholder="山田 太郎"
                    value={contactForm.name}
                    onChange={(e) => updateContactForm({ name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>会社名・屋号</label>
                  <input
                    type="text"
                    placeholder="株式会社〇〇"
                    value={contactForm.company}
                    onChange={(e) => updateContactForm({ company: e.target.value })}
                  />
                </div>
                <div className="form-group required">
                  <label>メールアドレス</label>
                  <input
                    type="email"
                    required
                    placeholder="example@email.com"
                    value={contactForm.email}
                    onChange={(e) => updateContactForm({ email: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>電話番号</label>
                  <input
                    type="tel"
                    placeholder="090-1234-5678"
                    value={contactForm.phone}
                    onChange={(e) => updateContactForm({ phone: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>設置予定都道府県</label>
                  <select
                    value={contactForm.prefecture}
                    onChange={(e) => updateContactForm({ prefecture: e.target.value })}
                  >
                    <option value="">選択してください</option>
                    {PREFECTURES.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>利用用途</label>
                  <select
                    value={contactForm.useCase}
                    onChange={(e) => updateContactForm({ useCase: e.target.value })}
                  >
                    <option value="">選択してください</option>
                    {USE_CASES.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group full">
                <label>ご要望・ご質問</label>
                <textarea
                  rows={5}
                  placeholder="設置場所の状況、ご要望など自由にご記入ください"
                  value={contactForm.message}
                  onChange={(e) => updateContactForm({ message: e.target.value })}
                />
              </div>

              {/* 見積もりサマリー（確認用） */}
              <div className="form-estimate-summary">
                <div className="summary-label">送信される見積もり内容</div>
                <div className="summary-line">
                  <span>スケルトン: {skeleton}</span>
                  <span>オプション: {placedModules.length}個</span>
                  <span className="summary-total">合計（税込）: {formatPrice(total)}</span>
                </div>
              </div>

              <div className="form-submit">
                <p className="privacy-note">
                  ※ 送信いただいた情報は見積もり・相談対応のみに使用します。
                  <a href="#">プライバシーポリシー</a>
                </p>
                <button type="submit" className="submit-btn">
                  無料でお問い合わせする →
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* 下部ナビ */}
      <div className="estimate-bottom-nav">
        <button className="back-nav-btn" onClick={() => setCurrentView('3d')}>
          ← 3Dパースに戻る
        </button>
        <div className="trust-badges">
          <span>🏆 施工実績 200棟以上</span>
          <span>⭐ 顧客満足度 98.2%</span>
          <span>🛡️ 10年保証</span>
        </div>
      </div>
    </div>
  );
};
