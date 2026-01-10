import { describe, it, expect } from 'vitest';
import {
  calculateBaseOffset,
  calculateLabelPosition,
  buildEdgePath,
  EDGE_CALCULATION_CONSTANTS,
  type EdgeCalculationContext
} from './edge-calculations';

describe('EDGE_CALCULATION_CONSTANTS', () => {
  it('has parallel edge spacing constant', () => {
    expect(EDGE_CALCULATION_CONSTANTS.PARALLEL_EDGE_SPACING).toBe(50);
  });

  it('has loop radius constant', () => {
    expect(EDGE_CALCULATION_CONSTANTS.LOOP_RADIUS).toBe(60);
  });

  it('has marker padding constant', () => {
    expect(EDGE_CALCULATION_CONSTANTS.MARKER_PADDING).toBe(8);
  });

  it('has loop label offset constant', () => {
    expect(EDGE_CALCULATION_CONSTANTS.LOOP_LABEL_OFFSET).toBe(20);
  });
});

describe('calculateBaseOffset', () => {
  it('returns 0 for single edge (no parallel edges)', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 1,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    
    expect(calculateBaseOffset(context)).toBe(0);
  });

  it('returns 0 for 2 parallel edges with index 0 (centered)', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 2,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    
    // totalWidth = (2 - 1) * 50 = 50
    // offset = (0 * 50) - (50 / 2) = -25
    expect(calculateBaseOffset(context)).toBe(-25);
  });

  it('returns positive offset for second edge in 2-edge group', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 1,
      totalParallel: 2,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    
    // totalWidth = (2 - 1) * 50 = 50
    // offset = (1 * 50) - (50 / 2) = 25
    expect(calculateBaseOffset(context)).toBe(25);
  });

  it('calculates correct offsets for 3 parallel edges', () => {
    const context1: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 3,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const context2: EdgeCalculationContext = {
      parallelIndex: 1,
      totalParallel: 3,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const context3: EdgeCalculationContext = {
      parallelIndex: 2,
      totalParallel: 3,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    
    // totalWidth = (3 - 1) * 50 = 100
    // offsets: -50, 0, 50
    expect(calculateBaseOffset(context1)).toBe(-50);
    expect(calculateBaseOffset(context2)).toBe(0);
    expect(calculateBaseOffset(context3)).toBe(50);
  });

  it('calculates correct offsets for 4 parallel edges', () => {
    const context1: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 4,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const context2: EdgeCalculationContext = {
      parallelIndex: 3,
      totalParallel: 4,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 0, y: 0 },
      targetPoint: { x: 0, y: 0 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    
    // totalWidth = (4 - 1) * 50 = 150
    // offsets: -75, -25, 25, 75
    expect(calculateBaseOffset(context1)).toBe(-75);
    expect(calculateBaseOffset(context2)).toBe(75);
  });
});

describe('calculateLabelPosition', () => {
  it('positions label at midpoint for horizontal edge (right to left)', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, // baseOffset
      false, // isSelfEdge
      0, // storedOffsetX
      0, // storedOffsetY
      0, // dragOffsetX
      0 // dragOffsetY
    );
    
    // Midpoint of (100, 50) and (200, 50)
    expect(pos.x).toBe(150);
    expect(pos.y).toBe(50);
  });

  it('positions label at midpoint for horizontal edge (left to right)', () => {
    const connectionInfo = {
      sourceSide: 'left' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 200, y: 50 },
      targetPoint: { x: 100, y: 50 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 0, 0, 0, 0
    );
    
    expect(pos.x).toBe(150);
    expect(pos.y).toBe(50);
  });

  it('positions label at midpoint for vertical edge (bottom to top)', () => {
    const connectionInfo = {
      sourceSide: 'bottom' as const,
      targetSide: 'top' as const,
      sourcePoint: { x: 50, y: 100 },
      targetPoint: { x: 50, y: 200 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 0, 0, 0, 0
    );
    
    expect(pos.x).toBe(50);
    expect(pos.y).toBe(150);
  });

  it('positions label at midpoint for vertical edge (top to bottom)', () => {
    const connectionInfo = {
      sourceSide: 'top' as const,
      targetSide: 'bottom' as const,
      sourcePoint: { x: 50, y: 200 },
      targetPoint: { x: 50, y: 100 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 0, 0, 0, 0
    );
    
    expect(pos.x).toBe(50);
    expect(pos.y).toBe(150);
  });

  it('applies baseOffset to Y coordinate for horizontal edges', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      20, // baseOffset
      false, // isSelfEdge
      0, // storedOffsetX
      0, // storedOffsetY
      0, // dragOffsetX
      0 // dragOffsetY
    );
    
    // Y should be offset by 20
    expect(pos.x).toBe(150);
    expect(pos.y).toBe(50 + 20);
  });

  it('applies baseOffset to X coordinate for vertical edges', () => {
    const connectionInfo = {
      sourceSide: 'bottom' as const,
      targetSide: 'top' as const,
      sourcePoint: { x: 50, y: 100 },
      targetPoint: { x: 50, y: 200 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      20, // baseOffset
      false, // isSelfEdge
      0, // storedOffsetX
      0, // storedOffsetY
      0, // dragOffsetX
      0 // dragOffsetY
    );
    
    // X should be offset by 20
    expect(pos.x).toBe(50 + 20);
    expect(pos.y).toBe(150);
  });

  it('applies storedOffsetX to horizontal edge label position', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 30, // storedOffsetX
      0, 0, 0
    );
    
    expect(pos.x).toBe(150 + 30);
    expect(pos.y).toBe(50);
  });

  it('applies storedOffsetY to vertical edge label position', () => {
    const connectionInfo = {
      sourceSide: 'bottom' as const,
      targetSide: 'top' as const,
      sourcePoint: { x: 50, y: 100 },
      targetPoint: { x: 50, y: 200 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 0, 30, // storedOffsetY
      0, 0
    );
    
    expect(pos.x).toBe(50);
    expect(pos.y).toBe(150 + 30);
  });

  it('combines stored and drag offsets for X', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 30, 0, 15, // dragOffsetX
      0
    );
    
    expect(pos.x).toBe(150 + 30 + 15);
  });

  it('combines stored and drag offsets for Y', () => {
    const connectionInfo = {
      sourceSide: 'bottom' as const,
      targetSide: 'top' as const,
      sourcePoint: { x: 50, y: 100 },
      targetPoint: { x: 50, y: 200 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, false, 0, 30, 0, 15 // dragOffsetY
    );
    
    expect(pos.y).toBe(150 + 30 + 15);
  });

  it('positions label outside self-loop to the right', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, // baseOffset
      true, // isSelfEdge
      0, // storedOffsetX
      0, // storedOffsetY
      0, // dragOffsetX
      0 // dragOffsetY
    );
    
    // Label should be to the right of the node: 100 + 60 + 20 = 180
    // Y at midpoint of source and target: (50 + 90) / 2 = 70
    expect(pos.x).toBe(180);
    expect(pos.y).toBe(70);
  });

  it('applies baseOffset to Y in self-loop scenario', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      20, // baseOffset
      true, // isSelfEdge
      0, // storedOffsetX
      0, // storedOffsetY
      0, // dragOffsetX
      0 // dragOffsetY
    );
    
    // Y should be offset by baseOffset
    expect(pos.y).toBe(70 + 20);
    expect(pos.x).toBe(180);
  });

  it('applies stored offsets to self-loop label', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, true, 10, 20, // storedOffsetX, storedOffsetY
      0, 0
    );
    
    // X: 100 + 60 + 20 + 10 = 190
    // Y: 70 + 20 = 90
    expect(pos.x).toBe(190);
    expect(pos.y).toBe(90);
  });

  it('applies drag offsets to self-loop label', () => {
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 }
    };
    
    const pos = calculateLabelPosition(
      connectionInfo,
      0, true, 0, 0, 15, 10 // dragOffsetX, dragOffsetY
    );
    
    // X: 100 + 60 + 20 + 15 = 195
    // Y: 70 + 10 = 80
    expect(pos.x).toBe(195);
    expect(pos.y).toBe(80);
  });
});

describe('buildEdgePath', () => {
  it('builds orthogonal path for horizontal edge', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      0,
      false, // isSelfEdge
      0,
      0
    );
    
    expect(path).toBe('M 100 50 L 150 50 L 150 50 L 200 50');
  });

  it('builds orthogonal path for vertical edge', () => {
    const path = buildEdgePath(
      { x: 50, y: 100 },
      { x: 50, y: 200 },
      'bottom',
      'top',
      0,
      false,
      0,
      0
    );
    
    expect(path).toBe('M 50 100 L 50 150 L 50 150 L 50 200');
  });

  it('builds self-loop path for self-edge', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 100, y: 90 },
      'right',
      'right',
      0,
      true, // isSelfEdge
      0,
      0
    );
    
    // Should create a cubic curve to the right
    expect(path).toBe('M 100 50 C 160 50, 160 90, 100 90');
  });

  it('applies baseOffset to horizontal edge path', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      20, // baseOffset
      false,
      0,
      0
    );
    
    // Y coordinates should be offset by 20
    expect(path).toContain('70');
  });

  it('applies baseOffset to vertical edge path', () => {
    const path = buildEdgePath(
      { x: 50, y: 100 },
      { x: 50, y: 200 },
      'bottom',
      'top',
      20, // baseOffset
      false,
      0,
      0
    );
    
    // X coordinates should be offset by 20
    expect(path).toContain('70');
  });

  it('applies baseOffset to self-loop path', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 100, y: 90 },
      'right',
      'right',
      20, // baseOffset
      true,
      0,
      0
    );
    
    // Y coordinates should be offset by 20
    expect(path).toContain('70');
    expect(path).toContain('110');
  });

  it('applies labelOffsetX to horizontal edge path', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      0,
      false,
      30, // labelOffsetX
      0
    );
    
    // Midpoint X should be (100+200)/2 + 30 = 180
    expect(path).toContain('180');
  });

  it('applies labelOffsetY to vertical edge path', () => {
    const path = buildEdgePath(
      { x: 50, y: 100 },
      { x: 50, y: 200 },
      'bottom',
      'top',
      0,
      false,
      0,
      30 // labelOffsetY
    );
    
    // Midpoint Y should be (100+200)/2 + 30 = 180
    expect(path).toContain('180');
  });

  it('combines baseOffset and labelOffsetX for horizontal edges', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 200, y: 50 },
      'right',
      'left',
      20, // baseOffset
      false,
      30, // labelOffsetX
      0
    );
    
    expect(path).toContain('70'); // Y offset by 20
    expect(path).toContain('180'); // X offset by 30
  });

  it('ignores labelOffsetX for self-loop edges', () => {
    const path = buildEdgePath(
      { x: 100, y: 50 },
      { x: 100, y: 90 },
      'right',
      'right',
      0,
      true, // isSelfEdge
      50, // labelOffsetX - should be ignored
      0
    );
    
    // Self-loop doesn't use labelOffsetX
    expect(path).toBe('M 100 50 C 160 50, 160 90, 100 90');
  });
});

describe('edge calculations integration', () => {
  it('calculates complete edge properties for single horizontal edge', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 1,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const baseOffset = calculateBaseOffset(context);
    const labelPos = calculateLabelPosition(
      connectionInfo,
      baseOffset,
      context.isSelfEdge,
      0, 0, 0, 0
    );
    const path = buildEdgePath(
      connectionInfo.sourcePoint,
      connectionInfo.targetPoint,
      connectionInfo.sourceSide,
      connectionInfo.targetSide,
      baseOffset,
      context.isSelfEdge,
      0, 0
    );
    
    expect(baseOffset).toBe(0);
    expect(labelPos.x).toBe(150);
    expect(labelPos.y).toBe(50);
    expect(path).toBe('M 100 50 L 150 50 L 150 50 L 200 50');
  });

  it('calculates complete edge properties for parallel edges', () => {
    const context1: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 3,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const baseOffset = calculateBaseOffset(context1);
    const path = buildEdgePath(
      connectionInfo.sourcePoint,
      connectionInfo.targetPoint,
      connectionInfo.sourceSide,
      connectionInfo.targetSide,
      baseOffset,
      context1.isSelfEdge,
      0, 0
    );
    
    expect(baseOffset).toBe(-50);
    expect(path).toContain('0'); // Y offset: 50 - 50 = 0
  });

  it('calculates complete edge properties for self-loop', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 1,
      isSelfEdge: true,
      sourceSide: 'right',
      targetSide: 'right',
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'right' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 100, y: 90 }
    };
    
    const baseOffset = calculateBaseOffset(context);
    const labelPos = calculateLabelPosition(
      connectionInfo,
      baseOffset,
      context.isSelfEdge,
      0, 0, 0, 0
    );
    const path = buildEdgePath(
      connectionInfo.sourcePoint,
      connectionInfo.targetPoint,
      connectionInfo.sourceSide,
      connectionInfo.targetSide,
      baseOffset,
      context.isSelfEdge,
      0, 0
    );
    
    expect(baseOffset).toBe(0);
    expect(labelPos.x).toBe(180);
    expect(labelPos.y).toBe(70);
    expect(path).toBe('M 100 50 C 160 50, 160 90, 100 90');
  });

  it('handles user-dragged label offsets correctly', () => {
    const context: EdgeCalculationContext = {
      parallelIndex: 0,
      totalParallel: 1,
      isSelfEdge: false,
      sourceSide: 'right',
      targetSide: 'left',
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 },
      storedOffsetX: 0,
      storedOffsetY: 0,
      dragOffsetX: 0,
      dragOffsetY: 0
    };
    const connectionInfo = {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
      sourcePoint: { x: 100, y: 50 },
      targetPoint: { x: 200, y: 50 }
    };
    
    const storedOffsetX = 30;
    const storedOffsetY = 20;
    const dragOffsetX = 10;
    const dragOffsetY = 15;
    
    const baseOffset = calculateBaseOffset(context);
    const labelPos = calculateLabelPosition(
      connectionInfo,
      baseOffset,
      context.isSelfEdge,
      storedOffsetX, storedOffsetY,
      dragOffsetX, dragOffsetY
    );
    const path = buildEdgePath(
      connectionInfo.sourcePoint,
      connectionInfo.targetPoint,
      connectionInfo.sourceSide,
      connectionInfo.targetSide,
      baseOffset,
      context.isSelfEdge,
      storedOffsetX + dragOffsetX,
      storedOffsetY + dragOffsetY
    );
    
    // Label position should include both offsets
    expect(labelPos.x).toBe(150 + storedOffsetX + dragOffsetX);
    expect(labelPos.y).toBe(50);
    
    // Path should include the combined offset
    expect(path).toContain(String(150 + storedOffsetX + dragOffsetX));
  });
});
