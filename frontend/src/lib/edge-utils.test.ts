import { describe, it, expect } from 'vitest';
import {
  getNodeDimensions,
  getNodeAbsolutePosition,
  getNodeCenter,
  calculateConnectionInfo,
  getSideRotation,
  buildOrthogonalPath,
  calculateMarkerPosition,
  type Side
} from './edge-utils';

describe('getNodeDimensions', () => {
  it('returns default dimensions for null node', () => {
    expect(getNodeDimensions(null)).toEqual({ width: 320, height: 200 });
  });

  it('uses measured dimensions when available', () => {
    const node = {
      measured: { width: 400, height: 300 }
    };
    expect(getNodeDimensions(node)).toEqual({ width: 400, height: 300 });
  });

  it('falls back to data.width when measured not available', () => {
    const node = {
      data: { width: 350, panelHeight: 250 }
    };
    expect(getNodeDimensions(node)).toEqual({ width: 350, height: 350 }); // 250 + 100
  });

  it('uses default width (320) when not specified', () => {
    const node = { data: {} };
    expect(getNodeDimensions(node).width).toBe(320);
  });

  it('calculates collapsed height correctly', () => {
    const node = {
      data: { collapsed: true, panelHeight: 200 }
    };
    expect(getNodeDimensions(node).height).toBe(40);
  });

  it('calculates expanded height as panelHeight + 100', () => {
    const node = {
      data: { collapsed: false, panelHeight: 150 }
    };
    expect(getNodeDimensions(node).height).toBe(250); // 150 + 100
  });
});

describe('getNodeAbsolutePosition', () => {
  it('returns origin for null node', () => {
    expect(getNodeAbsolutePosition(null, [])).toEqual({ x: 0, y: 0 });
  });

  it('uses positionAbsolute when available', () => {
    const node = {
      position: { x: 100, y: 100 },
      positionAbsolute: { x: 200, y: 300 }
    };
    expect(getNodeAbsolutePosition(node, [])).toEqual({ x: 200, y: 300 });
  });

  it('uses computed.positionAbsolute when available', () => {
    const node = {
      position: { x: 100, y: 100 },
      computed: { positionAbsolute: { x: 250, y: 350 } }
    };
    expect(getNodeAbsolutePosition(node, [])).toEqual({ x: 250, y: 350 });
  });

  it('falls back to position when no absolute position', () => {
    const node = {
      position: { x: 100, y: 200 }
    };
    expect(getNodeAbsolutePosition(node, [])).toEqual({ x: 100, y: 200 });
  });

  it('adds parent position for nested nodes', () => {
    const parent = {
      id: 'parent',
      position: { x: 50, y: 50 }
    };
    const child = {
      id: 'child',
      parentId: 'parent',
      position: { x: 100, y: 100 }
    };
    expect(getNodeAbsolutePosition(child, [parent, child])).toEqual({ x: 150, y: 150 });
  });
});

describe('getNodeCenter', () => {
  it('calculates center from position and dimensions', () => {
    const node = {
      position: { x: 100, y: 100 },
      data: { width: 200, panelHeight: 100, collapsed: false }
    };
    // Position (100, 100), width 200, height 200 (100 + 100)
    // Center: (100 + 100, 100 + 100) = (200, 200)
    expect(getNodeCenter(node, [])).toEqual({ x: 200, y: 200 });
  });

  it('uses measured dimensions for center calculation', () => {
    const node = {
      position: { x: 0, y: 0 },
      measured: { width: 100, height: 50 }
    };
    expect(getNodeCenter(node, [])).toEqual({ x: 50, y: 25 });
  });
});

describe('calculateConnectionInfo', () => {
  const createNode = (x: number, y: number, width = 320, height = 200) => ({
    position: { x, y },
    measured: { width, height }
  });

  it('chooses right/left sides when target is to the right', () => {
    const source = createNode(0, 0);
    const target = createNode(500, 0);
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('right');
    expect(info.targetSide).toBe('left');
  });

  it('chooses left/right sides when target is to the left', () => {
    const source = createNode(500, 0);
    const target = createNode(0, 0);
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('left');
    expect(info.targetSide).toBe('right');
  });

  it('chooses bottom/top sides when target is below', () => {
    const source = createNode(0, 0);
    const target = createNode(0, 500);
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('bottom');
    expect(info.targetSide).toBe('top');
  });

  it('chooses top/bottom sides when target is above', () => {
    const source = createNode(0, 500);
    const target = createNode(0, 0);
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('top');
    expect(info.targetSide).toBe('bottom');
  });

  it('prefers horizontal when dx > dy', () => {
    const source = createNode(0, 0);
    const target = createNode(300, 100); // dx=300, dy=100
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('right');
    expect(info.targetSide).toBe('left');
  });

  it('prefers vertical when dy > dx', () => {
    const source = createNode(0, 0);
    const target = createNode(100, 300); // dx=100, dy=300
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    expect(info.sourceSide).toBe('bottom');
    expect(info.targetSide).toBe('top');
  });

  it('calculates correct connection points on node borders', () => {
    const source = createNode(0, 0, 100, 100); // center at (50, 50)
    const target = createNode(200, 0, 100, 100); // center at (250, 50)
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    // Source right edge: x = 0 + 100 = 100, y = 50
    expect(info.sourcePoint).toEqual({ x: 100, y: 50 });
    // Target left edge: x = 200, y = 50
    expect(info.targetPoint).toEqual({ x: 200, y: 50 });
  });
});

describe('getSideRotation', () => {
  it('returns 0° for bottom (marker points UP toward node)', () => {
    expect(getSideRotation('bottom')).toBe(0);
  });

  it('returns 180° for top (marker points DOWN toward node)', () => {
    expect(getSideRotation('top')).toBe(180);
  });

  it('returns 90° for left (marker points RIGHT toward node)', () => {
    expect(getSideRotation('left')).toBe(90);
  });

  it('returns -90° for right (marker points LEFT toward node)', () => {
    expect(getSideRotation('right')).toBe(-90);
  });

  describe('marker orientation correctness', () => {
    // These tests verify the crow's foot notation direction semantics
    
    it('bottom connection: trident points toward node above', () => {
      // When edge exits from bottom, the marker should point UP toward the node
      // 0° rotation keeps the marker pointing UP (negative Y direction)
      expect(getSideRotation('bottom')).toBe(0);
    });

    it('left connection: trident points toward node on the right', () => {
      // When edge connects on left side of node, node is to the RIGHT
      // 90° rotation makes marker point RIGHT
      expect(getSideRotation('left')).toBe(90);
    });

    it('right connection: trident points toward node on the left', () => {
      // When edge connects on right side of node, node is to the LEFT
      // -90° rotation makes marker point LEFT
      expect(getSideRotation('right')).toBe(-90);
    });
  });
});

describe('buildOrthogonalPath', () => {
  it('builds horizontal path (right to left)', () => {
    const path = buildOrthogonalPath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left'
    );
    // Should go: start → mid horizontal → mid vertical (same Y) → end
    expect(path).toBe('M 100 50 L 150 50 L 150 50 L 200 50');
  });

  it('builds vertical path (bottom to top)', () => {
    const path = buildOrthogonalPath(
      { x: 50, y: 100 },
      { x: 50, y: 200 },
      'bottom',
      'top'
    );
    // Should go: start → mid vertical → mid horizontal (same X) → end
    expect(path).toBe('M 50 100 L 50 150 L 50 150 L 50 200');
  });

  it('applies baseOffset perpendicular to direction', () => {
    // Horizontal edge with vertical offset
    const path = buildOrthogonalPath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      20 // baseOffset
    );
    // Y coordinates should be offset by 20
    expect(path).toContain('70'); // 50 + 20
  });

  it('applies labelOffsetX to horizontal edges', () => {
    const path = buildOrthogonalPath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      0,
      30 // labelOffsetX
    );
    // midX should be (100+200)/2 + 30 = 180
    expect(path).toContain('180');
  });

  it('applies labelOffsetY to vertical edges', () => {
    const path = buildOrthogonalPath(
      { x: 50, y: 100 },
      { x: 50, y: 200 },
      'bottom',
      'top',
      0,
      0,
      30 // labelOffsetY
    );
    // midY should be (100+200)/2 + 30 = 180
    expect(path).toContain('180');
  });
});

describe('calculateMarkerPosition', () => {
  it('applies padding away from node for bottom connection', () => {
    const pos = calculateMarkerPosition({ x: 100, y: 100 }, 'bottom', 0, 10);
    expect(pos).toEqual({ x: 100, y: 110 }); // y increased (away from node above)
  });

  it('applies padding away from node for top connection', () => {
    const pos = calculateMarkerPosition({ x: 100, y: 100 }, 'top', 0, 10);
    expect(pos).toEqual({ x: 100, y: 90 }); // y decreased (away from node below)
  });

  it('applies padding away from node for left connection', () => {
    const pos = calculateMarkerPosition({ x: 100, y: 100 }, 'left', 0, 10);
    expect(pos).toEqual({ x: 90, y: 100 }); // x decreased (away from node on right)
  });

  it('applies padding away from node for right connection', () => {
    const pos = calculateMarkerPosition({ x: 100, y: 100 }, 'right', 0, 10);
    expect(pos).toEqual({ x: 110, y: 100 }); // x increased (away from node on left)
  });

  it('applies baseOffset perpendicular to connection direction', () => {
    // For left/right connections, offset is applied to Y
    const posLeft = calculateMarkerPosition({ x: 100, y: 100 }, 'left', 20, 0);
    expect(posLeft.y).toBe(120);
    
    // For top/bottom connections, offset is applied to X
    const posTop = calculateMarkerPosition({ x: 100, y: 100 }, 'top', 20, 0);
    expect(posTop.x).toBe(120);
  });

  it('combines baseOffset and padding correctly', () => {
    const pos = calculateMarkerPosition({ x: 100, y: 100 }, 'bottom', 15, 8);
    // baseOffset applied to X (perpendicular), padding to Y
    expect(pos).toEqual({ x: 115, y: 108 });
  });
});

describe('edge routing integration', () => {
  // Integration tests that verify complete edge routing scenarios
  
  it('routes edge correctly between horizontally arranged nodes', () => {
    const source = {
      position: { x: 0, y: 0 },
      measured: { width: 100, height: 100 }
    };
    const target = {
      position: { x: 300, y: 0 },
      measured: { width: 100, height: 100 }
    };
    
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    // Should connect right side of source to left side of target
    expect(info.sourceSide).toBe('right');
    expect(info.targetSide).toBe('left');
    
    // Source point at right edge (x=100), target at left edge (x=300)
    expect(info.sourcePoint.x).toBe(100);
    expect(info.targetPoint.x).toBe(300);
    
    // Markers should point toward their respective nodes
    expect(getSideRotation(info.sourceSide)).toBe(-90); // Points LEFT toward source
    expect(getSideRotation(info.targetSide)).toBe(90);  // Points RIGHT toward target
  });

  it('routes edge correctly between vertically arranged nodes', () => {
    const source = {
      position: { x: 0, y: 0 },
      measured: { width: 100, height: 100 }
    };
    const target = {
      position: { x: 0, y: 300 },
      measured: { width: 100, height: 100 }
    };
    
    const info = calculateConnectionInfo(source, target, [source, target]);
    
    // Should connect bottom of source to top of target
    expect(info.sourceSide).toBe('bottom');
    expect(info.targetSide).toBe('top');
    
    // Markers should point toward their respective nodes
    expect(getSideRotation(info.sourceSide)).toBe(0);   // Points UP toward source
    expect(getSideRotation(info.targetSide)).toBe(180); // Points DOWN toward target
  });
});

