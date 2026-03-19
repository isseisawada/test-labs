// ============================================================
// 中央：平面レイアウト編集エリア
// ============================================================

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SKELETON_DEFINITIONS, MODULE_DEFINITIONS, GRID_UNIT } from '../../data/definitions';
import { checkConstraints } from '../../utils/constraints';
import type { ModuleDefinition, PlacedModule } from '../../types';

interface FloorPlanProps {
  draggingDef: ModuleDefinition | null;
  onDragEnd: () => void;
}

function generateId(): string {
  return `mod-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
}

export const FloorPlan: React.FC<FloorPlanProps> = ({ draggingDef, onDragEnd }) => {
  const {
    skeleton,
    setSkeleton,
    placedModules,
    addModule,
    removeModule,
    rotateModule,
    updateModule,
    selectedModuleId,
    setSelectedModuleId,
    violations,
    setViolations,
  } = useAppStore();

  const canvasRef = useRef<HTMLDivElement>(null);
  const [hoveredCell, setHoveredCell] = useState<{ x: number; y: number } | null>(null);
  const [draggingPlaced, setDraggingPlaced] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const skDef = SKELETON_DEFINITIONS.find((s) => s.id === skeleton)!;
  const gridW = skDef.gridCols;
  const gridH = skDef.gridRows;

  // スケール係数（レスポンシブ対応）
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const updateScale = () => {
      if (canvasRef.current) {
        const available = canvasRef.current.parentElement?.clientWidth ?? 600;
        const needed = gridW * GRID_UNIT + 40;
        setScale(Math.min(1, (available - 40) / needed));
      }
    };
    updateScale();
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, [gridW]);

  const getCellFromEvent = useCallback((e: React.DragEvent | React.MouseEvent) => {
    if (!canvasRef.current) return null;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / (GRID_UNIT * scale));
    const y = Math.floor((e.clientY - rect.top) / (GRID_UNIT * scale));
    return { x, y };
  }, [scale]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const cell = getCellFromEvent(e);
    if (!cell || !draggingDef) return;

    const newModule: PlacedModule = {
      id: generateId(),
      type: draggingDef.type,
      position: {
        x: Math.max(0, Math.min(cell.x, gridW - draggingDef.defaultGridW)),
        y: Math.max(0, Math.min(cell.y, gridH - draggingDef.defaultGridH)),
      },
      rotation: 0,
      gridW: draggingDef.defaultGridW,
      gridH: draggingDef.defaultGridH,
    };

    addModule(newModule);
    const updated = [...placedModules, newModule];
    setViolations(checkConstraints(updated, skeleton));
    onDragEnd();
    setHoveredCell(null);
  }, [draggingDef, getCellFromEvent, addModule, placedModules, setViolations, skeleton, onDragEnd, gridW, gridH]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (!draggingDef) {
      setSelectedModuleId(null);
      return;
    }
    const cell = getCellFromEvent(e);
    if (!cell) return;

    const newModule: PlacedModule = {
      id: generateId(),
      type: draggingDef.type,
      position: {
        x: Math.max(0, Math.min(cell.x, gridW - draggingDef.defaultGridW)),
        y: Math.max(0, Math.min(cell.y, gridH - draggingDef.defaultGridH)),
      },
      rotation: 0,
      gridW: draggingDef.defaultGridW,
      gridH: draggingDef.defaultGridH,
    };

    addModule(newModule);
    const updated = [...placedModules, newModule];
    setViolations(checkConstraints(updated, skeleton));
    onDragEnd();
  }, [draggingDef, getCellFromEvent, addModule, placedModules, setViolations, skeleton, onDragEnd, gridW, gridH, setSelectedModuleId]);

  const handleModuleMouseDown = useCallback((e: React.MouseEvent, modId: string) => {
    e.stopPropagation();
    setSelectedModuleId(modId);
    setDraggingPlaced(modId);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mod = placedModules.find((m) => m.id === modId);
    if (!mod) return;
    setDragOffset({
      x: e.clientX - rect.left - mod.position.x * GRID_UNIT * scale,
      y: e.clientY - rect.top - mod.position.y * GRID_UNIT * scale,
    });
  }, [placedModules, scale, setSelectedModuleId]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const cell = getCellFromEvent(e);
    if (draggingDef && cell) {
      setHoveredCell(cell);
    }
    if (draggingPlaced && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const rawX = e.clientX - rect.left - dragOffset.x;
      const rawY = e.clientY - rect.top - dragOffset.y;
      const cellX = Math.round(rawX / (GRID_UNIT * scale));
      const cellY = Math.round(rawY / (GRID_UNIT * scale));
      const mod = placedModules.find((m) => m.id === draggingPlaced);
      if (!mod) return;
      const newX = Math.max(0, Math.min(cellX, gridW - mod.gridW));
      const newY = Math.max(0, Math.min(cellY, gridH - mod.gridH));
      if (newX !== mod.position.x || newY !== mod.position.y) {
        updateModule(draggingPlaced, { position: { x: newX, y: newY } });
      }
    }
  }, [draggingDef, draggingPlaced, getCellFromEvent, dragOffset, placedModules, updateModule, scale, gridW, gridH]);

  const handleMouseUp = useCallback(() => {
    if (draggingPlaced) {
      const updated = [...placedModules];
      setViolations(checkConstraints(updated, skeleton));
      setDraggingPlaced(null);
    }
  }, [draggingPlaced, placedModules, setViolations, skeleton]);

  const handleDeleteSelected = useCallback(() => {
    if (selectedModuleId) {
      removeModule(selectedModuleId);
      const updated = placedModules.filter((m) => m.id !== selectedModuleId);
      setViolations(checkConstraints(updated, skeleton));
    }
  }, [selectedModuleId, removeModule, placedModules, setViolations, skeleton]);

  const handleRotateSelected = useCallback(() => {
    if (selectedModuleId) {
      rotateModule(selectedModuleId);
      const updated = placedModules.map((m) => {
        if (m.id !== selectedModuleId) return m;
        return { ...m, gridW: m.gridH, gridH: m.gridW };
      });
      setViolations(checkConstraints(updated, skeleton));
    }
  }, [selectedModuleId, rotateModule, placedModules, setViolations, skeleton]);

  const violationModuleIds = new Set(violations.flatMap((v) => v.moduleIds));

  return (
    <div className="floor-plan-container">
      {/* サイズ切り替え */}
      <div className="size-switcher">
        <span className="size-label">スケルトンサイズ：</span>
        {SKELETON_DEFINITIONS.map((sk) => (
          <button
            key={sk.id}
            className={`size-btn ${skeleton === sk.id ? 'active' : ''}`}
            onClick={() => setSkeleton(sk.id)}
          >
            {sk.id}
          </button>
        ))}
      </div>

      {/* ツールバー */}
      {selectedModuleId && (
        <div className="toolbar">
          <span className="toolbar-label">選択中：
            {MODULE_DEFINITIONS.find(d => d.type === placedModules.find(m => m.id === selectedModuleId)?.type)?.label}
          </span>
          <button className="tool-btn" onClick={handleRotateSelected}>⟳ 回転</button>
          <button className="tool-btn danger" onClick={handleDeleteSelected}>🗑 削除</button>
        </div>
      )}

      {/* グリッドキャンバス */}
      <div className="grid-wrapper">
        <div
          ref={canvasRef}
          className={`grid-canvas ${draggingDef ? 'placing' : ''}`}
          style={{
            width: gridW * GRID_UNIT * scale,
            height: gridH * GRID_UNIT * scale,
            transform: `scale(1)`,
          }}
          onDragOver={(e) => { e.preventDefault(); const cell = getCellFromEvent(e); if (cell) setHoveredCell(cell); }}
          onDrop={handleDrop}
          onClick={handleClick}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={() => { setHoveredCell(null); setDraggingPlaced(null); }}
        >
          {/* グリッド線 */}
          <svg
            className="grid-svg"
            width={gridW * GRID_UNIT * scale}
            height={gridH * GRID_UNIT * scale}
          >
            {Array.from({ length: gridW + 1 }).map((_, i) => (
              <line
                key={`v${i}`}
                x1={i * GRID_UNIT * scale} y1={0}
                x2={i * GRID_UNIT * scale} y2={gridH * GRID_UNIT * scale}
                stroke={i % 5 === 0 ? '#bbb' : '#e0e0e0'} strokeWidth={i % 5 === 0 ? 1.5 : 0.5}
              />
            ))}
            {Array.from({ length: gridH + 1 }).map((_, i) => (
              <line
                key={`h${i}`}
                x1={0} y1={i * GRID_UNIT * scale}
                x2={gridW * GRID_UNIT * scale} y2={i * GRID_UNIT * scale}
                stroke={i % 5 === 0 ? '#bbb' : '#e0e0e0'} strokeWidth={i % 5 === 0 ? 1.5 : 0.5}
              />
            ))}
            {/* 寸法ラベル */}
            <text x={gridW * GRID_UNIT * scale / 2} y={gridH * GRID_UNIT * scale + 16}
              textAnchor="middle" fontSize={10} fill="#999">
              {skDef.lengthM}m
            </text>
            <text x={-10} y={gridH * GRID_UNIT * scale / 2}
              textAnchor="middle" fontSize={10} fill="#999"
              transform={`rotate(-90, ${-10}, ${gridH * GRID_UNIT * scale / 2})`}>
              {skDef.widthM}m
            </text>
          </svg>

          {/* ドロップ時のホバーハイライト */}
          {hoveredCell && draggingDef && (
            <div
              className="drop-preview"
              style={{
                left: Math.max(0, Math.min(hoveredCell.x, gridW - draggingDef.defaultGridW)) * GRID_UNIT * scale,
                top: Math.max(0, Math.min(hoveredCell.y, gridH - draggingDef.defaultGridH)) * GRID_UNIT * scale,
                width: draggingDef.defaultGridW * GRID_UNIT * scale,
                height: draggingDef.defaultGridH * GRID_UNIT * scale,
                backgroundColor: draggingDef.color + '88',
              }}
            />
          )}

          {/* 配置済みモジュール */}
          {placedModules.map((mod) => {
            const def = MODULE_DEFINITIONS.find((d) => d.type === mod.type)!;
            const isSelected = mod.id === selectedModuleId;
            const hasViolation = violationModuleIds.has(mod.id);
            return (
              <div
                key={mod.id}
                className={`placed-module ${isSelected ? 'selected' : ''} ${hasViolation ? 'violation' : ''}`}
                style={{
                  left: mod.position.x * GRID_UNIT * scale,
                  top: mod.position.y * GRID_UNIT * scale,
                  width: mod.gridW * GRID_UNIT * scale,
                  height: mod.gridH * GRID_UNIT * scale,
                  backgroundColor: def.color,
                  cursor: draggingPlaced === mod.id ? 'grabbing' : 'grab',
                }}
                onMouseDown={(e) => handleModuleMouseDown(e, mod.id)}
              >
                <span className="placed-icon">{def.icon}</span>
                <span className="placed-label">{def.label}</span>
                {hasViolation && <span className="violation-badge">⚠</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* 寸法メモ */}
      <div className="dimension-info">
        <span>1マス = 0.3m × 0.3m</span>
        <span>フロア: {skDef.lengthM}m × {skDef.widthM}m</span>
      </div>
    </div>
  );
};
