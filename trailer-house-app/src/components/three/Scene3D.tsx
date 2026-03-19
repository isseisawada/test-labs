// ============================================================
// Three.js 3Dシーン
// ============================================================

import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Sky } from '@react-three/drei';
import { useAppStore } from '../../store/useAppStore';
import { SKELETON_DEFINITIONS } from '../../data/definitions';

// マテリアル定義
const MATERIALS = {
  wood: { wall: '#D4A574', floor: '#8B6914', roof: '#6B4226' },
  white: { wall: '#F5F5F0', floor: '#E8E8E0', roof: '#C8C8C0' },
  dark: { wall: '#2C2C2C', floor: '#1A1A1A', roof: '#333333' },
};

// モジュールカラー（3D用）
const MODULE_3D_COLORS: Record<string, string> = {
  kitchen: '#90CAF9',
  toilet: '#A5D6A7',
  shower: '#80DEEA',
  bathtub: '#4FC3F7',
  loft: '#FFD54F',
  sofa: '#FFAB91',
  sofabed: '#FF8A65',
  storage: '#BCAAA4',
  desk: '#EEEEEE',
  bed: '#CE93D8',
};

// モジュールの3D高さ
const MODULE_HEIGHTS: Record<string, number> = {
  kitchen: 0.9,
  toilet: 0.8,
  shower: 2.1,
  bathtub: 0.6,
  loft: 2.4,
  sofa: 0.8,
  sofabed: 0.5,
  storage: 1.8,
  desk: 0.75,
  bed: 0.5,
};

const GRID_M = 0.3; // 1グリッド = 0.3m

// トレーラー本体
const TrailerSkeleton: React.FC<{ cols: number; rows: number; matColors: { wall: string; floor: string; roof: string } }> = ({ cols, rows, matColors }) => {
  const length = cols * GRID_M;
  const width = rows * GRID_M;
  const wallH = 2.4;
  const wallT = 0.05;

  return (
    <group>
      {/* 床 */}
      <mesh position={[length / 2, 0, width / 2]} receiveShadow>
        <boxGeometry args={[length, 0.05, width]} />
        <meshStandardMaterial color={matColors.floor} />
      </mesh>

      {/* 壁：前 */}
      <mesh position={[0, wallH / 2, width / 2]} castShadow>
        <boxGeometry args={[wallT, wallH, width]} />
        <meshStandardMaterial color={matColors.wall} />
      </mesh>
      {/* 壁：後 */}
      <mesh position={[length, wallH / 2, width / 2]} castShadow>
        <boxGeometry args={[wallT, wallH, width]} />
        <meshStandardMaterial color={matColors.wall} />
      </mesh>
      {/* 壁：左 */}
      <mesh position={[length / 2, wallH / 2, 0]} castShadow>
        <boxGeometry args={[length, wallH, wallT]} />
        <meshStandardMaterial color={matColors.wall} />
      </mesh>
      {/* 壁：右 */}
      <mesh position={[length / 2, wallH / 2, width]} castShadow>
        <boxGeometry args={[length, wallH, wallT]} />
        <meshStandardMaterial color={matColors.wall} />
      </mesh>

      {/* 屋根 */}
      <mesh position={[length / 2, wallH + 0.1, width / 2]} receiveShadow>
        <boxGeometry args={[length + 0.2, 0.15, width + 0.2]} />
        <meshStandardMaterial color={matColors.roof} />
      </mesh>

      {/* タイヤ（装飾） */}
      {[0.5, length - 0.5].map((x, i) => (
        <group key={i} position={[x, -0.25, -0.2]}>
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.25, 0.1, 8, 16]} />
            <meshStandardMaterial color="#333" />
          </mesh>
        </group>
      ))}

      {/* フレーム（シャーシ） */}
      <mesh position={[length / 2, -0.05, width / 2]}>
        <boxGeometry args={[length + 0.1, 0.1, width * 0.6]} />
        <meshStandardMaterial color="#555" metalness={0.8} roughness={0.3} />
      </mesh>
    </group>
  );
};

// 配置モジュール3D表現
const Module3D: React.FC<{ type: string; x: number; y: number; w: number; h: number }> = ({ type, x, y, w, h }) => {
  const posX = (x + w / 2) * GRID_M;
  const posZ = (y + h / 2) * GRID_M;
  const width = w * GRID_M;
  const depth = h * GRID_M;
  const height = MODULE_HEIGHTS[type] ?? 0.5;
  const color = MODULE_3D_COLORS[type] ?? '#aaa';

  return (
    <mesh position={[posX, height / 2, posZ]} castShadow receiveShadow>
      <boxGeometry args={[width - 0.02, height, depth - 0.02]} />
      <meshStandardMaterial color={color} opacity={0.85} transparent />
    </mesh>
  );
};


// 地面グリッド
const Ground: React.FC = () => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
    <planeGeometry args={[50, 50]} />
    <meshStandardMaterial color="#c8d4c0" />
  </mesh>
);

interface Scene3DProps {
  timeOfDay: 'day' | 'night';
  material: 'wood' | 'white' | 'dark';
  cameraView: 'exterior' | 'interior' | 'top';
}

export const Scene3D: React.FC<Scene3DProps> = ({ timeOfDay, material, cameraView }) => {
  const { skeleton, placedModules } = useAppStore();
  const skDef = SKELETON_DEFINITIONS.find((s) => s.id === skeleton)!;
  const matColors = MATERIALS[material];

  const length = skDef.gridCols * GRID_M;
  const width = skDef.gridRows * GRID_M;

  const cameraPositions = {
    exterior: [length * 1.5, length * 0.8, width * 2] as [number, number, number],
    interior: [length * 0.2, 1.6, width / 2] as [number, number, number],
    top: [length / 2, length * 1.5, width * 0.1] as [number, number, number],
  };

  const cameraTargets = {
    exterior: [length / 2, 1, width / 2] as [number, number, number],
    interior: [length * 0.7, 1.6, width / 2] as [number, number, number],
    top: [length / 2, 0, width / 2] as [number, number, number],
  };

  return (
    <Canvas shadows dpr={[1, 2]} style={{ background: timeOfDay === 'night' ? '#0a0a1a' : '#c9e3f7' }}>
      <PerspectiveCamera
        makeDefault
        position={cameraPositions[cameraView]}
        fov={60}
      />
      <OrbitControls
        target={cameraTargets[cameraView]}
        enablePan={true}
        minDistance={1}
        maxDistance={30}
      />

      {/* 照明 */}
      <ambientLight intensity={timeOfDay === 'night' ? 0.2 : 0.6} />
      <directionalLight
        position={[10, 20, 10]}
        intensity={timeOfDay === 'night' ? 0.1 : 1.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
        color={timeOfDay === 'night' ? '#3040ff' : '#fff8e0'}
      />
      {timeOfDay === 'night' && (
        <>
          <pointLight position={[length / 2, 2, width / 2]} intensity={2} color="#ffcc66" distance={10} />
          <pointLight position={[length * 0.2, 2, width / 2]} intensity={1} color="#ffaa33" distance={5} />
        </>
      )}

      {/* 空 */}
      {timeOfDay === 'day' && <Sky sunPosition={[100, 20, 100]} />}

      {/* 地面 */}
      <Ground />

      {/* トレーラー本体 */}
      <TrailerSkeleton
        cols={skDef.gridCols}
        rows={skDef.gridRows}
        matColors={matColors}
      />

      {/* 配置モジュール */}
      {placedModules.map((mod) => (
        <Module3D
          key={mod.id}
          type={mod.type}
          x={mod.position.x}
          y={mod.position.y}
          w={mod.gridW}
          h={mod.gridH}
        />
      ))}

      {/* 霧（ムード） */}
      {timeOfDay === 'night' && <fog attach="fog" args={['#0a0a1a', 5, 30]} />}
    </Canvas>
  );
};
