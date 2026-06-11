# Casa EP — photoreal renders with Blender/Cycles
# Geometry reconstructed from the R01 floor plans (same coordinates as the
# Three.js walkthrough in ../index.html).
#
# Coordinates used by the build helpers match the JS app:
#   x = east, y = UP, z = south   (helpers convert to Blender's Z-up)
#
# Usage:  blender -b -P casa_ep.py -- <mode> [quick]
#   modes: plan_ground | plan_upper | plan_basement |
#          exterior_pool | aerial | int_gourmet | int_estar | int_master

import bpy, bmesh, sys, math
from math import radians, sin, cos, pi
from mathutils import Vector

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODE  = argv[0] if argv else 'aerial'
QUICK = 'quick' in argv

FLOOR_G, FLOOR_U, FLOOR_B = 0.0, 3.5, -3.3
CEIL_G, CEIL_U, ROOF_T = 3.2, 6.7, 0.35

# what gets built / clipped per mode
CFG = {
  'plan_ground':   dict(site=1, ground=1, upper=0, roof=0, base=0, clip=('ground', 1.35)),
  'plan_upper':    dict(site=1, ground=1, upper=1, roof=0, base=0, clip=('upper', FLOOR_U+1.35)),
  'plan_basement': dict(site=0, ground=0, upper=0, roof=0, base=1, clip=('base', FLOOR_B+1.35)),
  'exterior_pool': dict(site=1, ground=1, upper=1, roof=1, base=0, clip=None),
  'aerial':        dict(site=1, ground=1, upper=1, roof=1, base=0, clip=None),
  'int_gourmet':   dict(site=1, ground=1, upper=1, roof=1, base=0, clip=None),
  'int_estar':     dict(site=1, ground=1, upper=1, roof=1, base=0, clip=None),
  'int_master':    dict(site=1, ground=1, upper=1, roof=1, base=0, clip=None),
}[MODE]

bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene

# ===================================================================== materials
def _nodes(m):
    m.use_nodes = True
    nt = m.node_tree
    return nt, nt.nodes['Principled BSDF'], nt.nodes

def world_pos(nt):
    g = nt.nodes.new('ShaderNodeNewGeometry')
    return g.outputs['Position']

def mat_plain(name, col, rough=0.8, metal=0.0, bump_noise=None):
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if bump_noise:
        scale, strength = bump_noise
        n = ns.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = 6
        nt.links.new(world_pos(nt), n.inputs['Vector'])
        bp = ns.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength
        nt.links.new(n.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_slats(name, axis='Z', col1=(0.42,0.28,0.16), col2=(0.56,0.41,0.25), scale=10.0):
    """wood louvres: bands across the given world axis, dark grooves + bump"""
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    sep = ns.new('ShaderNodeSeparateXYZ'); nt.links.new(world_pos(nt), sep.inputs['Vector'])
    comp = sep.outputs[{'X':0,'Y':1,'Z':2}[axis]]
    w = ns.new('ShaderNodeTexWave'); w.wave_type='BANDS'; w.bands_direction='X'
    w.inputs['Scale'].default_value = scale; w.inputs['Distortion'].default_value = 0.0
    cmb = ns.new('ShaderNodeCombineXYZ'); nt.links.new(comp, cmb.inputs['X'])
    nt.links.new(cmb.outputs['Vector'], w.inputs['Vector'])
    ramp = ns.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.12   # groove
    ramp.color_ramp.elements[0].color = (0.05,0.032,0.02,1)
    ramp.color_ramp.elements[1].position = 0.25
    ramp.color_ramp.elements[1].color = (1,1,1,1)
    nt.links.new(w.outputs['Fac'], ramp.inputs['Fac'])
    nz = ns.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2
    nt.links.new(world_pos(nt), nz.inputs['Vector'])
    mixc = ns.new('ShaderNodeMix'); mixc.data_type='RGBA'
    mixc.inputs['A'].default_value = (*col1,1); mixc.inputs['B'].default_value = (*col2,1)
    nt.links.new(nz.outputs['Fac'], mixc.inputs['Factor'])
    mul = ns.new('ShaderNodeMix'); mul.data_type='RGBA'; mul.blend_type='MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    nt.links.new(mixc.outputs['Result'], mul.inputs['A'])
    nt.links.new(ramp.outputs['Color'], mul.inputs['B'])
    nt.links.new(mul.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    bp = ns.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35
    nt.links.new(w.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_bricks(name, w_, h_, mortar, col1, col2, mortar_col, rough=0.5, bump=0.15):
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    br = ns.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Color1'].default_value = (*col1,1)
    br.inputs['Color2'].default_value = (*col2,1)
    br.inputs['Mortar'].default_value = (*mortar_col,1)
    br.inputs['Mortar Size'].default_value = mortar
    br.inputs['Brick Width'].default_value = w_
    br.inputs['Row Height'].default_value = h_
    br.offset = 0.5
    nt.links.new(world_pos(nt), br.inputs['Vector'])
    nz = ns.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6
    nz.inputs['Detail'].default_value = 8
    nt.links.new(world_pos(nt), nz.inputs['Vector'])
    mixc = ns.new('ShaderNodeMix'); mixc.data_type='RGBA'; mixc.blend_type='OVERLAY'
    mixc.inputs['Factor'].default_value = 0.25
    nt.links.new(br.outputs['Color'], mixc.inputs['A'])
    nt.links.new(nz.outputs['Color'], mixc.inputs['B'])
    nt.links.new(mixc.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    bp = ns.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
    nt.links.new(br.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_glass_archviz(name):
    """transmissive glass whose shadow rays pass through (bright interiors)"""
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    b.inputs['Base Color'].default_value = (0.85, 0.93, 0.94, 1)
    b.inputs['Roughness'].default_value = 0.0
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.45
    transp = ns.new('ShaderNodeBsdfTransparent')
    lp = ns.new('ShaderNodeLightPath')
    mix = ns.new('ShaderNodeMixShader')
    out = nt.nodes['Material Output']
    nt.links.new(lp.outputs['Is Shadow Ray'], mix.inputs['Fac'])
    nt.links.new(b.outputs['BSDF'], mix.inputs[1])
    nt.links.new(transp.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m

def mat_water(name):
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    b.inputs['Base Color'].default_value = (0.25, 0.62, 0.66, 1)
    b.inputs['Roughness'].default_value = 0.08
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['IOR'].default_value = 1.33
    n = ns.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 1.4
    n.inputs['Detail'].default_value = 8
    nt.links.new(world_pos(nt), n.inputs['Vector'])
    bp = ns.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.12
    nt.links.new(n.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_grass(name):
    m = bpy.data.materials.new(name); nt, b, ns = _nodes(m)
    n = ns.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 14
    n.inputs['Detail'].default_value = 10; n.inputs['Roughness'].default_value = 0.7
    nt.links.new(world_pos(nt), n.inputs['Vector'])
    mixc = ns.new('ShaderNodeMix'); mixc.data_type='RGBA'
    mixc.inputs['A'].default_value = (0.16, 0.30, 0.08, 1)
    mixc.inputs['B'].default_value = (0.30, 0.42, 0.15, 1)
    nt.links.new(n.outputs['Fac'], mixc.inputs['Factor'])
    nt.links.new(mixc.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 1.0
    n2 = ns.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 60
    n2.inputs['Detail'].default_value = 12
    nt.links.new(world_pos(nt), n2.inputs['Vector'])
    bp = ns.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5
    nt.links.new(n2.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

M = dict(
  plasterExt = mat_plain('plasterExt', (0.83,0.79,0.71), 0.9, bump_noise=(9, .06)),
  plasterInt = mat_plain('plasterInt', (0.90,0.87,0.80), 0.92, bump_noise=(9, .04)),
  slat   = mat_slats('slat', 'Z', scale=11),          # horizontal louvres (brise/rails/garage)
  slatC  = mat_slats('slatC', 'Y', scale=8),          # ceiling slats run E-W
  deck   = mat_bricks('deck', 2.4, 0.145, 0.006, (0.40,0.27,0.16), (0.33,0.215,0.12), (0.06,0.04,0.025), 0.6, 0.2),
  trav   = mat_bricks('trav', 1.0, 1.0, 0.005, (0.78,0.72,0.62), (0.72,0.66,0.55), (0.45,0.40,0.33), 0.32, 0.05),
  stone  = mat_bricks('stone', 0.45, 0.16, 0.012, (0.55,0.48,0.38), (0.42,0.36,0.28), (0.18,0.15,0.12), 0.85, 0.5),
  conc   = mat_plain('conc', (0.52,0.50,0.46), 0.9, bump_noise=(14,.1)),
  grass  = mat_grass('grass'),
  water  = mat_water('water'),
  glass  = mat_glass_archviz('glass'),
  frame  = mat_plain('frame', (0.05,0.045,0.04), 0.5),
  poolShell = mat_plain('poolShell', (0.22,0.52,0.55), 0.5),
  furnWood = mat_plain('furnWood', (0.30,0.19,0.10), 0.55, bump_noise=(20,.05)),
  furnDark = mat_plain('furnDark', (0.06,0.05,0.04), 0.6),
  fabric   = mat_plain('fabric', (0.70,0.66,0.57), 0.95, bump_noise=(40,.15)),
  fabricOlv= mat_plain('fabricOlv', (0.23,0.28,0.13), 0.95, bump_noise=(40,.15)),
  fabricRust=mat_plain('fabricRust', (0.42,0.16,0.08), 0.9, bump_noise=(40,.15)),
  white    = mat_plain('white', (0.92,0.92,0.90), 0.25),
  counter  = mat_plain('counter', (0.10,0.085,0.07), 0.2),
  screen   = mat_plain('screen', (0.01,0.012,0.015), 0.15, 0.5),
  trunk    = mat_plain('trunk', (0.32,0.24,0.16), 0.95, bump_noise=(10,.4)),
  leaf     = mat_plain('leaf', (0.16,0.30,0.07), 0.65),
  carDark  = mat_plain('carDark', (0.02,0.022,0.028), 0.25, 0.9),
  carRed   = mat_plain('carRed', (0.30,0.02,0.02), 0.3, 0.6),
  rug      = mat_plain('rug', (0.62,0.56,0.43), 1.0, bump_noise=(60,.3)),
)
M['leaf'].use_backface_culling = False

# ===================================================================== builders
_cube_meshes = {}
def _cube_mesh(mat):
    if mat.name not in _cube_meshes:
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        me = bpy.data.meshes.new('c_'+mat.name); bm.to_mesh(me); bm.free()
        me.materials.append(mat)
        _cube_meshes[mat.name] = me
    return _cube_meshes[mat.name]

CLIP = None          # (lambda-active ceiling cut height) while building a clipped floor
def box(mat, x0,y0,z0, x1,y1,z1, parent=None):
    """x east, y UP, z south — converted to Blender Z-up here."""
    y0,y1 = min(y0,y1), max(y0,y1)
    if CLIP is not None:
        if y0 >= CLIP: return None
        y1 = min(y1, CLIP)
    ob = bpy.data.objects.new('b', _cube_mesh(mat))
    ob.location = ((x0+x1)/2, (z0+z1)/2, (y0+y1)/2)
    ob.scale = (abs(x1-x0) or .001, abs(z1-z0) or .001, abs(y1-y0) or .001)
    if parent: ob.parent = parent
    SC.collection.objects.link(ob)
    return ob

def empty_at(x, y, z, yaw=0.0):
    e = bpy.data.objects.new('e', None)
    e.location = (x, z, y)
    e.rotation_euler = (0, 0, -yaw)     # JS yaw (around up axis) → Blender -Z rot
    SC.collection.objects.link(e)
    return e

def wall(x0,z0, x1,z1, y0=0.0, h=3.2, t=0.18, mat=None, openings=()):
    mat = mat or M['plasterExt']
    horiz = abs(x1-x0) > abs(z1-z0)
    ln = abs(x1-x0) if horiz else abs(z1-z0)
    sg = (1 if (x1-x0)>=0 else -1) if horiz else (1 if (z1-z0)>=0 else -1)
    def seg(a,b, sy0,sy1, m):
        if b-a < 0.01 or sy1-sy0 < 0.01: return
        th = 0.05 if m is M['glass'] else t
        if horiz:
            xa, xb = x0+sg*a, x0+sg*b
            box(m, min(xa,xb),sy0,z0-th/2, max(xa,xb),sy1,z0+th/2)
        else:
            za, zb = z0+sg*a, z0+sg*b
            box(m, x0-th/2,sy0,min(za,zb), x0+th/2,sy1,max(za,zb))
    cur = 0.0
    for o in sorted(openings, key=lambda o:o['a']):
        seg(cur, o['a'], y0, y0+h, mat)
        oy0 = o.get('y0', 0.9 if o['kind']=='win' else 0.0)
        oy1 = o.get('y1', 2.4 if o['kind']=='win' else 2.3)
        if oy0 > 0: seg(o['a'], o['b'], y0, y0+oy0, mat)
        if oy1 < h: seg(o['a'], o['b'], y0+oy1, y0+h, mat)
        if o['kind'] in ('glass','win'): seg(o['a'], o['b'], y0+oy0, y0+oy1, M['glass'])
        cur = o['b']
    seg(cur, ln, y0, y0+h, mat)

def O(a,b,kind,y0=None,y1=None):
    d = dict(a=a,b=b,kind=kind)
    if y0 is not None: d['y0']=y0
    if y1 is not None: d['y1']=y1
    return d

def slab(mat, x0,z0,x1,z1, yTop=0.0, th=0.3, slat_bottom=False):
    box(mat, x0,yTop-th,z0, x1,yTop,z1)
    if slat_bottom and CLIP is None:
        box(M['slatC'], x0+.02,yTop-th-.012,z0+.02, x1-.02,yTop-th-.002,z1-.02)

def railing(x0,z0,x1,z1, y0, h=1.05):
    if abs(x1-x0) > abs(z1-z0): box(M['slat'], min(x0,x1),y0,z0-.04, max(x0,x1),y0+h,z0+.04)
    else: box(M['slat'], x0-.04,y0,min(z0,z1), x0+.04,y0+h,max(z0,z1))

def flight(xa,xb, zTop,zBot, yTop,yBot, mat=None):
    mat = mat or M['trav']
    steps = round(abs(yTop-yBot)/0.175)
    run = (zBot-zTop)/steps
    for i in range(steps):
        y1 = yBot + (steps-i)/steps*(yTop-yBot)
        z0 = zTop + i*run
        box(mat, xa,yBot,z0, xb,y1,z0+run)

# ---------------------------------------------------------------- furniture
def sofa(x,z, w,d, yaw=0.0, y=0.0, mat=None):
    mat = mat or M['fabric']
    e = empty_at(x,y,z,yaw)
    box(mat, -w/2,0.12,-d/2, w/2,0.45,d/2, e)
    box(mat, -w/2,0.45,-d/2, w/2,0.85,-d/2+0.22, e)
    box(mat, -w/2,0.30,-d/2, -w/2+0.18,0.62,d/2, e)
    box(mat, w/2-0.18,0.30,-d/2, w/2,0.62,d/2, e)

def bed(x,z, w=2.0, ln=2.1, yaw=0.0, y=0.0):
    e = empty_at(x,y,z,yaw)
    box(M['furnWood'], -w/2-.1,0,-ln/2-.1, w/2+.1,0.3,ln/2+.1, e)
    box(M['white'], -w/2,0.3,-ln/2, w/2,0.58,ln/2, e)
    box(M['fabric'], -w/2+.08,0.58,-ln/2+.06, w/2-.08,0.72,-ln/2+0.62, e)
    box(M['fabricOlv'], -w/2+.05,0.50,ln/2-1.0, w/2-.05,0.62,ln/2-0.1, e)  # folded throw
    box(M['furnWood'], -w/2,0,-ln/2-0.18, w/2,1.1,-ln/2-0.06, e)

def table(x,z, w,d, y=0.0, h=0.74, mat=None):
    mat = mat or M['furnWood']
    box(mat, x-w/2,y+h-0.05,z-d/2, x+w/2,y+h,z+d/2)
    for sx,sz in ((-1,-1),(1,-1),(-1,1),(1,1)):
        box(M['furnDark'], x+sx*(w/2-.06)-.03,y,z+sz*(d/2-.06)-.03, x+sx*(w/2-.06)+.03,y+h-.05,z+sz*(d/2-.06)+.03)

def cyl(mat, x,y,z, r, h, parent=None):
    if CLIP is not None and y >= CLIP: return None
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new('cy'); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new('cy', me); ob.location = (x, z, y+h/2)
    if parent: ob.parent = parent; ob.location = (x, z, y+h/2)
    SC.collection.objects.link(ob); return ob

def round_table(x,z, r=1.15, y=0.0, h=0.74):
    cyl(M['furnWood'], x, y+h-0.03, z, r, 0.06)
    cyl(M['furnDark'], x, y, z, 0.14, h-0.03)

def chair(x,z, yaw=0.0, y=0.0, mat=None):
    mat = mat or M['fabricOlv']
    e = empty_at(x,y,z,yaw)
    box(mat, -.23,.2,-.23, .23,.45,.23, e)
    box(mat, -.23,.45,.13, .23,.9,.23, e)
    box(M['furnDark'], -.2,0,-.2, .2,.2,.2, e)

def chairs_around(x,z, r, n, y=0.0):
    for i in range(n):
        a = i/n*2*pi
        chair(x+cos(a)*r, z+sin(a)*r, -a-pi/2, y)

def rug(x,z, w,d, y=0.0):
    box(M['rug'], x-w/2,y+0.004,z-d/2, x+w/2,y+0.018,z+d/2)

def tv(x,z, w, yaw=0.0, y=0.0):
    e = empty_at(x,y,z,yaw)
    box(M['screen'], -w/2,1.0,-0.03, w/2,1.0+w*0.42,0.03, e)

def counter_run(x0,z0,x1,z1, y=0.0, h=0.92):
    box(M['furnWood'], min(x0,x1),y,min(z0,z1), max(x0,x1),y+h-.04,max(z0,z1))
    box(M['counter'], min(x0,x1)-.02,y+h-.04,min(z0,z1)-.02, max(x0,x1)+.02,y+h,max(z0,z1)+.02)

def wardrobe(x0,z0,x1,z1, y=0.0, h=2.4): box(M['furnWood'], x0,y,z0, x1,y+h,z1)
def shelves(x0,z0,x1,z1, y=0.0, h=2.2):  box(M['furnWood'], x0,y,z0, x1,y+h,z1)

def car(x,z, yaw=0.0, y=0.0, mat=None):
    mat = mat or M['carDark']
    e = empty_at(x,y,z,yaw)
    box(mat, -.95,.32,-2.25, .95,.78,2.25, e)
    box(mat, -.85,.78,-1.1, .85,1.28,0.9, e)
    box(M['screen'], -.80,.82,-1.05, .80,1.24,0.85, e)
    for sx,sz in ((-1,-1.45),(1,-1.45),(-1,1.45),(1,1.45)):
        w = cyl(M['furnDark'], 0,0,0, .34,.24)
        if w: w.parent = e; w.rotation_euler = (0, pi/2, 0); w.location = (sx*.95, sz, .34)

def lounger(x,z, yaw=0.0):
    e = empty_at(x,0,z,yaw)
    box(M['deck'], -.4,.25,-1.0, .4,.4,1.0, e)
    box(M['fabric'], -.38,.4,-1.0, .38,.5,1.0, e)
    box(M['fabric'], -.38,.4,.55, .38,.95,1.0, e)

def bath(x0,z0,x1,z1, y=0.0):
    counter_run(x0+0.1,z0+0.2, x0+0.65,z1-0.2, y, 0.86)
    cyl(M['white'], x1-0.5, y, z0+0.5, 0.24, 0.42)
    box(M['glass'], x1-1.1,y,z1-1.1, x1-1.06,y+2.0,z1-0.1)
    box(M['glass'], x1-1.1,y,z1-0.14, x1-0.1,y+2.0,z1-0.1)

def palm(x,z,h=7.0):
    cyl(M['trunk'], x,0,z, 0.16, h)
    for i in range(8):
        a = i/8*2*pi
        e = empty_at(x,h,z,a)
        f = box(M['leaf'], 0.25,-0.26,-0.32, 2.6,0.0,0.32, e)
        if f: f.rotation_euler = (0, 0.5, 0); f.scale.z = 0.04

def tree(x,y,z,h=3.2,r=2.2):
    cyl(M['trunk'], x,y,z, 0.16, h)
    import random; random.seed(int(x*7+z*13))
    for i in range(4):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r*(0.55+random.random()*0.4))
        me = bpy.data.meshes.new('lf'); bm.to_mesh(me); bm.free(); me.materials.append(M['leaf'])
        for poly in me.polygons: poly.use_smooth = True
        ob = bpy.data.objects.new('lf', me)
        ob.location = (x+(random.random()-.5)*r, z+(random.random()-.5)*r, y+h+(random.random()-.4)*r*.7)
        SC.collection.objects.link(ob)

# ===================================================================== SITE
SITE = dict(x0=-4, z0=-4, x1=38, z1=38)
if CFG['site']:
    box(M['grass'], -500,-0.6,-500, 500,-0.45,500)
    s = SITE
    slab(M['grass'], s['x0'],s['z0'], 0,s['z1'])
    slab(M['grass'], 0,s['z0'], s['x1'],0)
    slab(M['grass'], 33,0, s['x1'],s['z1'])
    slab(M['grass'], 0,28.0, 23,36.9)
    slab(M['grass'], 0,36.9, 23,s['z1'])
    slab(M['conc'], 23,36.9, 33,s['z1'])
    slab(M['trav'], 0,9.6, 25,12.0)
    slab(M['trav'], 18.5,12.0, 25,24.5)
    slab(M['grass'], 0,12.0, 18.5,15.0)
    slab(M['deck'], 0,15.0, 18.5,28.0)
    slab(M['deck'], 18.5,24.5, 23,28.0)
    # perimeter stone wall (gate gap at the driveway)
    box(M['stone'], s['x0'],0,s['z0'], s['x1'],1.9,s['z0']+.45)
    box(M['stone'], s['x0'],0,s['z1']-.45, 23,1.9,s['z1'])
    box(M['stone'], 33,0,s['z1']-.45, s['x1'],1.9,s['z1'])
    box(M['stone'], s['x0'],0,s['z0'], s['x0']+.45,1.9,s['z1'])
    box(M['stone'], s['x1']-.45,0,s['z0'], s['x1'],1.9,s['z1'])

    # ---- pool (same blob as the walkthrough)
    cx, czp = 8.2, 21.4
    pts = []
    N = 26
    for i in range(N):
        a = i/N*2*pi
        rx = 5.8*(1+0.16*sin(a*2.3+1.2)+0.08*sin(a*4.7))
        rz = 4.3*(1+0.18*sin(a*1.7+0.4)+0.07*cos(a*3.3))
        pts.append((cx+cos(a)*rx, czp+sin(a)*rz))
    # water surface
    bm = bmesh.new()
    vs = [bm.verts.new((px, pz, -0.18)) for px,pz in pts]
    bm.faces.new(vs)
    me = bpy.data.meshes.new('water'); bm.to_mesh(me); me.materials.append(M['water'])
    ob = bpy.data.objects.new('water', me); SC.collection.objects.link(ob)
    # shell: blob extruded down
    bm = bmesh.new()
    vs = [bm.verts.new((px, pz, 0.02)) for px,pz in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0,0,-1.7), verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces: face.normal_flip()
    me = bpy.data.meshes.new('shell'); bm.to_mesh(me); me.materials.append(M['poolShell'])
    ob = bpy.data.objects.new('shell', me); SC.collection.objects.link(ob)
    # island + tree
    cyl(M['grass'], 11.4,-0.45,22.2, 1.6, 0.5)
    tree(11.4, 0.05, 22.2, 2.4, 1.4)
    tree(2.6, 0, 14.0, 3.0, 1.5)
    if not MODE.startswith('plan'):   # palm crowns would overhang the cutaway plans
        for px,pz in [(-2,-2),(5,-2.5),(14,-2.6),(24,-2.4),(35,-2),(35.5,12),(35.5,24),(-2.4,6),(-2.6,16),
                      (-2.4,26),(-2,33),(3,30),(10,30.5),(17,30.8),(2.2,13.5),(20,36),(35,33)]:
            palm(px,pz, 6+((px*3+pz)%5)*0.5)
    # terrace + pool furniture
    sofa(9.5,11.2, 3.0,1.0, 0)
    round_table(9.5,12.6, 0.55, 0, 0.32)
    for lx,lz,ly in [(3.2,27.2,0),(5.2,27.4,0),(7.2,27.2,0),(16.6,17.0,pi),(15.0,27.0,0)]:
        lounger(lx,lz,ly)

# ===================================================================== GROUND
if CFG['ground']:
    slab(M['trav'], 0,0, 26.3,9.6, 0, 0.3, True)
    slab(M['trav'], 26.3,0, 27.45,0.5)
    slab(M['trav'], 26.3,5.5, 27.45,9.6)
    slab(M['trav'], 27.45,0, 33,9.6, 0, 0.3, True)
    slab(M['trav'], 25,9.6, 33,24.5, 0, 0.3, True)
    slab(M['conc'], 23,24.5, 33,36.9)

    if CFG['clip'] and CFG['clip'][0]=='ground': CLIP = CFG['clip'][1]

    wall(0,0, 33,0, t=.25, openings=[O(1.0,4.6,'win'), O(6.0,15.0,'win',2.3,3.1),
                                     O(16.2,20.6,'win',1.0,2.4), O(28.3,32.2,'win')])
    wall(0,0, 0,9.6, t=.25, openings=[O(1.0,4.0,'win'), O(5.6,8.6,'win')])
    wall(0,9.6, 5.5,9.6, t=.25, openings=[O(1.2,4.4,'open',y1=2.5)])
    for cx_ in (5.62, 10.5, 15.38):
        box(M['frame'], cx_-0.12,0,9.48, cx_+0.12,3.2,9.72)
    box(M['plasterExt'], 5.5,2.6,9.42, 15.5,3.2,9.78)
    wall(15.5,9.6, 25,9.6, openings=[O(0.4,3.4,'glass',0,2.6), O(3.5,5.4,'open',y1=2.6), O(5.5,9.1,'glass',0,2.6)])
    wall(25,9.6, 25,24.5, openings=[O(0.9,3.9,'open',y1=2.6), O(4.0,6.3,'glass',0,2.6),
                                    O(6.4,9.4,'open',y1=2.6), O(9.5,13.9,'glass',0,2.6)])
    wall(33,0, 33,36.9, t=.25, openings=[O(1.0,4.0,'win'), O(10.4,13.6,'win'), O(15.0,21.5,'win',0.6,2.6)])
    wall(25,24.5, 33,24.5, mat=M['plasterInt'], openings=[O(1.2,2.2,'open')])
    wall(23,24.5, 23,36.9, t=.25)
    wall(23,36.9, 33,36.9, t=.25, openings=[O(1.4,9.2,'open',y1=2.4)])
    wall(0,4.8, 5.5,4.8, mat=M['plasterInt'])
    wall(5.5,0, 5.5,9.6, mat=M['plasterInt'], openings=[O(1.9,2.9,'open'), O(6.6,7.6,'open')])
    wall(15.5,0, 15.5,6.0, mat=M['plasterInt'], openings=[O(2.4,3.6,'open')])
    wall(15.5,6.0, 22,6.0, mat=M['plasterInt'], openings=[O(1.6,2.7,'open')])
    wall(21.5,0, 21.5,6.0, mat=M['plasterInt'], openings=[O(1.0,1.9,'open'), O(4.0,4.9,'open')])
    wall(21.5,3.0, 24,3.0, mat=M['plasterInt'])
    wall(24,0, 24,6.0, mat=M['plasterInt'])
    wall(24,6.0, 27.5,6.0, mat=M['plasterInt'], openings=[O(1.3,2.5,'open')])
    wall(27.5,0, 27.5,7.8, mat=M['plasterInt'], openings=[O(6.4,7.4,'open')])
    wall(27.5,5.0, 33,5.0, mat=M['plasterInt'], openings=[O(0.7,1.6,'open')])
    wall(27.5,7.8, 33,7.8, mat=M['plasterInt'])
    wall(22,6.0, 22,8.0, mat=M['plasterInt'])
    wall(22,8.0, 24,8.0, mat=M['plasterInt'], openings=[O(0.5,1.4,'open')])
    railing(25.3,0.3, 25.3,4.9, 0, 1.0)
    railing(26.25,1.6, 26.25,5.5, 0, 1.0)
    railing(26.25,5.5, 27.45,5.5, 0, 1.0)
    flight(24.05,25.25, 0.5,5.5, FLOOR_U, FLOOR_G)
    flight(26.3,27.45, 0.6,5.4, FLOOR_G, FLOOR_B)

    # furniture
    round_table(13.2,4.6, 1.25); chairs_around(13.2,4.6, 1.95, 8)
    counter_run(6.0,0.4, 11.5,1.4)
    sofa(7.6,6.6, 2.8,1.0, pi)
    chair(6.2,5.2, pi/3); chair(9.2,5.0, -pi/4, 0, M['fabricRust'])
    rug(7.8,5.8, 3.6,2.8)
    counter_run(15.8,0.35, 21.2,1.0)
    counter_run(17.2,3.0, 20.2,4.0)
    tv(5.65,7.5, 1.6, pi/2)
    shelves(0.15,0.4, 0.55,4.4)
    table(2.8,2.4, 1.2,1.2, 0, 0.5)
    box(M['fabricOlv'], 1.2,0,3.4, 1.9,0.45,4.1)
    box(M['fabricRust'], 3.6,0,0.8, 4.3,0.45,1.5)
    box(M['furnDark'], 0.3,0,5.3, 1.1,1.35,8.9)
    box(M['furnDark'], 1.7,0,5.3, 2.5,1.35,8.9)
    box(M['fabric'], 3.6,0,6.0, 4.6,0.5,8.2)
    bed(30.4,2.4, 1.9,2.1, pi/2)
    wardrobe(27.65,0.15, 28.05,4.4)
    bath(27.5,5.0, 33,7.8)
    table(29,11.9, 3.6,1.2)
    for i in range(5):
        chair(27.6+i*0.72, 11.0, 0); chair(27.6+i*0.72, 12.8, pi)
    sofa(29,16.6, 3.6,1.05, 0)
    sofa(26.6,19.2, 1.0,2.6, 0, 0, M['fabricOlv'])
    chair(31.6,19.6, -pi/2, 0, M['fabricRust']); chair(31.6,21.2, -pi/2)
    round_table(29.2,19.4, 0.65, 0, 0.36); round_table(30.4,20.6, 0.45, 0, 0.3)
    rug(29.3,19.2, 5.4,4.6); tv(29,24.4, 2.4, pi)
    car(25.6,28.2, 0); car(25.6,33.4, 0, 0, M['carRed']); car(30.4,28.2, 0)
    CLIP = None

# ===================================================================== UPPER
if CFG['upper']:
    def uslab(x0,z0,x1,z1): slab(M['trav'], x0,z0,x1,z1, FLOOR_U, FLOOR_U-CEIL_G, True)
    uslab(0,0, 9.2,9.6); uslab(9.2,7.8, 15.5,9.6); uslab(15.5,0, 24,9.6)
    uslab(24,5.9, 25.35,9.6); uslab(25.35,0, 33,9.6)
    uslab(25,9.6, 33,23.2); uslab(23,23.2, 33,35.2)

    if CFG['clip'] and CFG['clip'][0]=='upper': CLIP = CFG['clip'][1]
    U = dict(y0=FLOOR_U, h=CEIL_U-FLOOR_U)
    wall(0,0, 33,0, **U, t=.25, openings=[O(0.8,3.8,'win'), O(5.4,8.4,'win'),
                                          O(16.2,20.4,'win'), O(28.0,32.4,'win',0.7,2.5)])
    wall(0,0, 0,9.6, **U, t=.25, openings=[O(5.4,8.8,'win')])
    wall(0,9.6, 9.2,9.6, **U, openings=[O(0.8,8.4,'glass',0,2.5)])
    wall(9.2,9.6, 25,9.6, **U, openings=[O(0.4,15.2,'glass',0,2.5)])
    wall(25,9.6, 25,23.2, **U, openings=[O(0.5,13.1,'glass',0,2.5)])
    wall(33,0, 33,23.2, **U, t=.25, openings=[O(1.0,3.5,'win',0.7,2.5), O(11.2,14.1,'win'), O(14.9,17.8,'win')])
    wall(33,23.2, 33,35.2, **U, t=.25, openings=[O(4.0,9.0,'win')])
    wall(23,35.2, 33,35.2, **U, t=.25, openings=[O(1.5,5.5,'win',0.7,2.5)])
    wall(23,23.2, 23,35.2, **U, t=.25, openings=[O(1.0,8.5,'glass',0,2.5)])
    wall(23,23.2, 25,23.2, **U)
    pInt = M['plasterInt']
    wall(4.6,0, 4.6,4.8, **U, mat=pInt)
    wall(0,4.8, 9.2,4.8, **U, mat=pInt, openings=[O(1.6,2.6,'open'), O(6.2,7.2,'open')])
    wall(9.2,0, 9.2,7.8, **U, mat=pInt)
    wall(9.2,7.8, 9.2,9.6, **U, mat=pInt, openings=[O(0.2,1.6,'open')])
    wall(15.5,0, 15.5,7.8, **U, mat=pInt)
    wall(15.5,7.8, 24,7.8, **U, mat=pInt, openings=[O(1.0,2.0,'open'), O(5.8,6.8,'open')])
    wall(18.5,4.0, 18.5,7.8, **U, mat=pInt)
    wall(15.5,4.0, 21.5,4.0, **U, mat=pInt, openings=[O(1.2,2.1,'open'), O(4.2,5.1,'open')])
    wall(21.5,0, 21.5,7.8, **U, mat=pInt)
    wall(24,0, 24,5.9, **U, mat=pInt)
    wall(27.5,0, 27.5,6.2, **U, mat=pInt, openings=[O(5.0,6.0,'open')])
    wall(27.5,6.2, 33,6.2, **U, mat=pInt)
    wall(26.8,7.8, 26.8,23.2, **U, mat=pInt, openings=[O(0.6,1.5,'open'), O(3.6,4.6,'open'),
        O(7.3,8.3,'open'), O(10.9,11.8,'open'), O(13.7,14.6,'open')])
    wall(25,7.8, 26.8,7.8, **U, mat=pInt)
    wall(26.8,10.8, 33,10.8, **U, mat=pInt)
    wall(29.6,7.8, 29.6,10.8, **U, mat=pInt, openings=[O(1.1,2.0,'open')])
    wall(26.8,14.5, 33,14.5, **U, mat=pInt)
    wall(26.8,18.2, 33,18.2, **U, mat=pInt)
    wall(29.6,18.2, 29.6,21.2, **U, mat=pInt, openings=[O(1.1,2.0,'open')])
    wall(26.8,21.2, 33,21.2, **U, mat=pInt)
    wall(26.8,23.2, 33,23.2, **U, mat=pInt, openings=[O(0.5,1.5,'open')])
    wall(29,23.2, 29,32.8, **U, mat=pInt, openings=[O(1.0,2.0,'open'), O(5.0,6.0,'open')])
    wall(29,26.8, 33,26.8, **U, mat=pInt, openings=[O(0.6,1.5,'open')])
    wall(23,32.8, 33,32.8, **U, mat=pInt, openings=[O(2.0,3.0,'open')])
    railing(25.35,1.4, 25.35,5.9, FLOOR_U)
    railing(24,5.9, 25.35,5.9, FLOOR_U)
    railing(9.2,7.8, 15.5,7.8, FLOOR_U)

    for ox in (0.4, 5.0):
        table(ox+2.0,1.6, 1.8,0.85, FLOOR_U)
        chair(ox+2.0,2.6, pi, FLOOR_U, M['furnDark'])
        shelves(ox+0.2,0.2, ox+0.5,4.2, FLOOR_U, 2.2)
    sofa(4.4,6.6, 3.2,1.05, pi, FLOOR_U); rug(4.4,7.4, 4.2,3.0, FLOOR_U)
    tv(4.4,9.4, 2.0, pi, FLOOR_U)
    bed(18.5,2.0, 1.9,2.1, 0, FLOOR_U)
    bath(15.5,4.0, 18.5,7.8, FLOOR_U); shelves(18.7,4.2, 21.3,4.8, FLOOR_U)
    sofa(30.2,2.0, 3.4,1.1, 0, FLOOR_U); tv(30.2,6.1, 2.6, pi, FLOOR_U)
    rug(30.2,3.2, 4.4,3.2, FLOOR_U)
    bed(30.4,12.6, 1.8,2.05, pi/2, FLOOR_U)
    bed(30.4,16.4, 1.8,2.05, pi/2, FLOOR_U)
    bath(29.6,7.8, 33,10.8, FLOOR_U); bath(29.6,18.2, 33,21.2, FLOOR_U)
    shelves(26.95,8.0, 29.45,8.6, FLOOR_U); shelves(26.95,20.6, 29.45,21.1, FLOOR_U)
    shelves(27.0,21.4, 32.8,22.0, FLOOR_U)
    bed(25.6,27.6, 2.0,2.2, pi/2, FLOOR_U)
    chair(24.0,31.4, pi*0.8, FLOOR_U); chair(25.6,31.6, pi, FLOOR_U, M['fabricRust'])
    rug(25.8,28.6, 4.6,4.0, FLOOR_U); tv(28.9,28.0, 2.2, -pi/2, FLOOR_U)
    shelves(29.2,23.4, 32.8,24.0, FLOOR_U)
    bath(29,26.8, 33,32.8, FLOOR_U)
    CLIP = None

# ===================================================================== ROOF
if CFG['roof']:
    def roof_slab(x0,z0,x1,z1):
        box(M['plasterExt'], x0,CEIL_U,z0, x1,CEIL_U+ROOF_T,z1)
        box(M['slatC'], x0+.02,CEIL_U-0.012,z0+.02, x1-.02,CEIL_U-0.002,z1-.02)
    roof_slab(-1.5,-1.5, 34.5,11.1)
    roof_slab(23.5,11.1, 34.5,21.7)
    roof_slab(21.5,21.7, 34.5,36.7)
    box(M['slatC'], 5.5,CEIL_U-0.65,9.78, 15.5,CEIL_U-0.45,12.0)

# ===================================================================== BASEMENT
if CFG['base']:
    if MODE == 'plan_basement':
        slab(M['conc'], -10,-10, 45,45, FLOOR_B-0.35, 0.3)   # backdrop ground
    slab(M['conc'], 15.5,-0.2, 33.2,26.9, FLOOR_B)
    if CFG['clip'] and CFG['clip'][0]=='base': CLIP = CFG['clip'][1]
    B = dict(y0=FLOOR_B, h=3.0); pInt = M['plasterInt']
    wall(15.5,0, 15.5,26.7, **B, mat=pInt, t=.25)
    wall(33,0, 33,26.7, **B, mat=pInt, t=.25)
    wall(15.5,0, 33,0, **B, mat=pInt, t=.25)
    wall(15.5,26.7, 33,26.7, **B, mat=pInt, t=.25)
    wall(15.5,3.4, 21.9,3.4, **B, mat=pInt, openings=[O(1.1,2.0,'open'), O(4.3,5.2,'open')])
    wall(18.7,0, 18.7,3.4, **B, mat=pInt)
    wall(15.5,5.2, 21.5,5.2, **B, mat=pInt, openings=[O(0.8,1.7,'open'), O(4.0,4.9,'open')])
    wall(17.2,3.4, 17.2,5.2, **B, mat=pInt)
    wall(18.7,3.4, 18.7,5.2, **B, mat=pInt)
    wall(21.5,3.4, 21.5,9.6, **B, mat=pInt, openings=[O(3.0,4.0,'open')])
    wall(21.9,0, 21.9,3.4, **B, mat=pInt)
    wall(24,0, 24,6.0, **B, mat=pInt)
    wall(24,6.0, 27.5,6.0, **B, mat=pInt, openings=[O(1.3,2.5,'open')])
    wall(27.5,0, 27.5,9.6, **B, mat=pInt, openings=[O(6.6,7.6,'open')])
    wall(27.5,5.4, 33,5.4, **B, mat=pInt, openings=[O(0.8,1.7,'open')])
    wall(30.2,5.4, 30.2,9.6, **B, mat=pInt)
    wall(15.5,9.6, 33,9.6, **B, mat=pInt, openings=[O(6.8,8.0,'open'), O(10.0,11.2,'open')])
    wall(15.5,18.8, 33,18.8, **B, mat=pInt, openings=[O(9.0,10.2,'open')])
    wall(23.6,18.8, 23.6,26.7, **B, mat=pInt)
    flight(26.3,27.45, 0.6,5.4, FLOOR_G, FLOOR_B)
    bed(17.0,1.6, 1.4,2.0, pi/2, FLOOR_B); bed(20.2,1.6, 1.4,2.0, pi/2, FLOOR_B)
    sofa(18.4,8.6, 2.6,1.0, pi, FLOOR_B); tv(18.4,5.5, 1.6, 0, FLOOR_B)
    counter_run(27.7,0.3, 32.7,1.0, FLOOR_B)
    box(M['white'], 31.5,FLOOR_B,1.4, 32.7,FLOOR_B+1.0,2.6)
    car(18.5,14.2, pi/2, FLOOR_B); car(24.5,14.2, pi/2, FLOOR_B, M['carRed'])
    car(29.5,14.2, pi/2, FLOOR_B)
    box(M['furnDark'], 24.5,FLOOR_B,20.0, 26.5,FLOOR_B+1.6,22.0)
    box(M['furnDark'], 28.0,FLOOR_B,20.0, 30.0,FLOOR_B+1.6,22.0)
    box(M['furnDark'], 31.0,FLOOR_B,20.0, 32.6,FLOOR_B+1.8,25.5)
    CLIP = None

# ===================================================================== sky & sun
world = bpy.data.worlds.new('w'); SC.world = world
world.use_nodes = True
wn = world.node_tree
sky = wn.nodes.new('ShaderNodeTexSky')
sky.sky_type = 'NISHITA'
SUN_ELEV = dict(plan_ground=62, plan_upper=62, plan_basement=62,
                exterior_pool=32, aerial=45, int_gourmet=38, int_estar=38, int_master=38)[MODE]
sky.sun_elevation = radians(SUN_ELEV)
sky.sun_rotation = radians(305)      # light arriving from the south-west
sky.sun_intensity = 1.0
sky.altitude = 50
bg = wn.nodes['Background']
wn.links.new(sky.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 1.0
SC.view_settings.view_transform = 'AgX'
SC.view_settings.look = 'AgX - Base Contrast' if MODE.startswith('int_') else 'AgX - Punchy'
SC.view_settings.exposure = -4.0 if MODE.startswith('int_') else (-5.3 if MODE=='plan_basement' else -4.7)     # physical Nishita sky is ~extremely bright

# interior fill lights for eye-level interior shots (warm, point straight down)
if MODE.startswith('int_'):
    def area(x, z, y, size=1.5, watts=900):
        li = bpy.data.lights.new('fill', 'AREA'); li.energy = watts; li.size = size
        li.color = (1.0, 0.88, 0.72)
        ob = bpy.data.objects.new('fill', li); ob.location = (x, z, y)
        SC.collection.objects.link(ob)
    for ax, az in [(10.5,4.8),(18.5,3.0),(29,12),(29,19),(13,4)]:
        area(ax, az, CEIL_G-0.15)
    for ax, az in [(26,28),(31,29.8),(30,3)]:
        area(ax, az, CEIL_U-0.25)

# ===================================================================== camera
def cam_lookat(px,py,pz, tx,ty,tz, lens=32):
    c = bpy.data.cameras.new('cam'); c.lens = lens
    ob = bpy.data.objects.new('cam', c)
    ob.location = (px, pz, py)                      # convert (x, up, south)
    d = Vector((tx-px, tz-pz, ty-py))
    ob.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    SC.collection.objects.link(ob); SC.camera = ob
    return ob

CAMS = {
  'plan_ground':   ((16.5, 46, 33), (16.5, 0.4, 15.5), 33),
  'plan_upper':    ((16.5, 48, 34), (16.5, 3.8, 16.5), 33),
  'plan_basement': ((24.2, 32, 26), (24.2, -3.0, 12.8), 36),
  'exterior_pool': ((-1.5, 2.1, 18.0), (28, 1.8, 17.5), 24),
  'aerial':        ((-17, 30, 47), (17, 0.5, 14), 32),
  'int_gourmet':   ((6.3, 1.55, 1.2), (14, 1.3, 8.5), 20),
  'int_estar':     ((31.8, 1.55, 23.2), (25.5, 1.4, 14.5), 20),
  'int_master':    ((28.3, FLOOR_U+1.55, 24.0), (23.5, FLOOR_U+1.0, 31), 20),
}
(pp, tt, lens) = CAMS[MODE]
cam_lookat(pp[0],pp[1],pp[2], tt[0],tt[1],tt[2], lens)

# ===================================================================== render
SC.render.engine = 'CYCLES'
SC.cycles.device = 'CPU'
SC.cycles.samples = 16 if QUICK else (64 if MODE.startswith('plan') or MODE=='aerial' else 112)
SC.cycles.use_adaptive_sampling = True
SC.cycles.adaptive_threshold = 0.06 if QUICK else 0.035
SC.cycles.use_denoising = True
SC.cycles.time_limit = 120 if QUICK else 540
SC.cycles.caustics_reflective = False
SC.cycles.caustics_refractive = False
SC.cycles.max_bounces = 8
SC.cycles.transparent_max_bounces = 16
SC.render.resolution_x = 640 if QUICK else 1600
SC.render.resolution_y = 400 if QUICK else 1000
SC.render.filepath = f'/tmp/renders/{MODE}{"_q" if QUICK else ""}.png'
bpy.ops.render.render(write_still=True)
print('DONE', SC.render.filepath)
