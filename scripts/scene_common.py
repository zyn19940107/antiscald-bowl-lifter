"""Common geometry / material helpers for the two-clip bowl lifter simulation.

Units: meters.  Blender: Z up.  Bowl axis at plan origin.
"""
import math
import bpy
import numpy as np

TAU = 2.0 * math.pi


# ---------------------------------------------------------------- math utils
def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def ease_in_out(x):
    return smoothstep(x)


def ease_out_cubic(x):
    x = np.clip(x, 0.0, 1.0)
    return 1.0 - (1.0 - x) ** 3


def ease_in_cubic(x):
    x = np.clip(x, 0.0, 1.0)
    return x ** 3


def ramp(t, t0, t1, ease=ease_in_out):
    """0 before t0, 1 after t1, eased in between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return float(ease((t - t0) / (t1 - t0)))


def lerp(a, b, u):
    return a + (b - a) * u


def lerp_vec(a, b, u):
    return tuple(lerp(x, y, u) for x, y in zip(a, b))


def catmull_rom(points, n_per_seg=18, closed=False):
    """Dense polyline through control points (centripetal Catmull-Rom)."""
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return pts.copy()
    if closed:
        p = np.vstack([pts[-1], pts, pts[0], pts[1]])
        nseg = len(pts)
    else:
        p = np.vstack([pts[0], pts, pts[-1]])
        nseg = len(pts) - 1
    out = [p[1].copy()]
    for i in range(1, nseg + 1):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        # centripetal knots
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0) ** 0.5, 1e-5)
        t2 = t1 + max(np.linalg.norm(p2 - p1) ** 0.5, 1e-5)
        t3 = t2 + max(np.linalg.norm(p3 - p2) ** 0.5, 1e-5)
        ts = np.linspace(t1, t2, n_per_seg, endpoint=False)[1:]
        for t in ts:
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
            out.append(c)
    out.append(p[-2].copy())
    return np.array(out)


def arc_points(radius, a0, a1, n=80, z=0.0):
    """Plan-view circular arc points (angles in radians, x=cos,y=sin)."""
    a = np.linspace(a0, a1, n)
    return np.stack([radius * np.cos(a), radius * np.sin(a), np.full_like(a, z)], axis=1)


# ---------------------------------------------------------------- mesh build
def _tangents(pts):
    T = np.zeros_like(pts)
    if len(pts) == 1:
        return np.array([[0.0, 0.0, 1.0]])
    T[1:-1] = pts[2:] - pts[:-2]
    T[0] = pts[1] - pts[0]
    T[-1] = pts[-1] - pts[-2]
    n = np.linalg.norm(T, axis=1)
    n[n < 1e-12] = 1.0
    return T / n[:, None]


def tube_data(pts, radius, sides=10, cap=True):
    """Sweep a circle along pts (parallel-transport-ish frames)."""
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 2:
        return np.zeros((0, 3)), []
    T = _tangents(pts)
    # initial normal
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(T[0], up)) > 0.95:
        up = np.array([1.0, 0.0, 0.0])
    N = np.cross(T[0], up)
    N /= np.linalg.norm(N)
    normals = np.zeros_like(pts)
    for i in range(len(pts)):
        N = N - np.dot(N, T[i]) * T[i]
        ln = np.linalg.norm(N)
        if ln < 1e-8:
            alt = np.array([1.0, 0.0, 0.0]) if abs(T[i][0]) < 0.9 else np.array([0.0, 1.0, 0.0])
            N = alt - np.dot(alt, T[i]) * T[i]
            ln = np.linalg.norm(N)
        N = N / ln
        normals[i] = N
    B = np.cross(T, normals)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    verts = []
    for i in range(len(pts)):
        for k in range(sides):
            verts.append(pts[i] + radius * (math.cos(ang[k]) * normals[i] + math.sin(ang[k]) * B[i]))
    verts = np.array(verts)
    faces = []
    for i in range(len(pts) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            a = i * sides + k
            b = i * sides + k2
            c = (i + 1) * sides + k2
            d = (i + 1) * sides + k
            faces.append((a, b, c, d))
    if cap:
        c0 = len(verts)
        verts = np.vstack([verts, pts[0]])
        c1 = len(verts)
        verts = np.vstack([verts, pts[-1]])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k))
            base = (len(pts) - 1) * sides
            faces.append((c1, base + k, base + k2))
    return verts, faces


class MeshBuilder:
    """Accumulates geometry with per-face material indices, emits one mesh."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.smooth = []

    def _append(self, verts, faces, mat, smooth=True):
        base = len(self.verts)
        self.verts.extend([tuple(map(float, v)) for v in verts])
        for f in faces:
            self.faces.append(tuple(base + i for i in f))
            self.mats.append(mat)
            self.smooth.append(smooth)

    def add_tube(self, pts, radius, mat, sides=10, cap=True):
        if len(pts) < 2:
            return
        v, f = tube_data(pts, radius, sides)
        self._append(v, f, mat)

    def add_raw(self, verts, faces, mat, smooth=True):
        self._append(np.asarray(verts, dtype=float), faces, mat, smooth)

    def build_object(self, name, materials, collection=None):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.validate(verbose=False)
        obj = bpy.data.objects.new(name, mesh)
        (collection or bpy.context.scene.collection).objects.link(obj)
        for m in materials:
            mesh.materials.append(m)
        for i, poly in enumerate(mesh.polygons):
            poly.use_smooth = self.smooth[i] if i < len(self.smooth) else True
        nmat = max(1, len(materials))
        for i, poly in enumerate(mesh.polygons):
            mi = self.mats[i] if i < len(self.mats) else 0
            poly.material_index = min(max(int(mi), 0), nmat - 1)
        return obj


def lathe_data(profile, n_theta, mat_of_seg, mod_fn=None):
    """Return (verts, faces, mats) for a closed solid of revolution.

    profile: open polyline (r,z); endpoints with r==0 become fan poles.
    mat_of_seg(i) gives material index for the strip between profile i and i+1.
    """
    prof = np.asarray(profile, dtype=float)
    n = len(prof)
    verts = []
    ring_start = []
    theta = np.linspace(0, TAU, n_theta, endpoint=False)
    for (r, z) in prof:
        if r < 1e-9:
            ring_start.append(len(verts))
            verts.append((0.0, 0.0, float(z)))
        else:
            ring_start.append(len(verts))
            for th in theta:
                rr = float(r)
                if mod_fn is not None:
                    rr = mod_fn(float(r), float(z), float(th))
                verts.append((rr * math.cos(th), rr * math.sin(th), float(z)))
    faces = []
    mats = []

    def ri(i, k):
        return ring_start[i] + (k % n_theta)

    for i in range(n - 1):
        r0, r1 = prof[i, 0], prof[i + 1, 0]
        mat = mat_of_seg(i)
        if r0 < 1e-9 and r1 < 1e-9:
            continue
        if r0 < 1e-9:
            p = ring_start[i]
            for k in range(n_theta):
                faces.append((p, ri(i + 1, k), ri(i + 1, k + 1)))
                mats.append(mat)
        elif r1 < 1e-9:
            p = ring_start[i + 1]
            for k in range(n_theta):
                faces.append((p, ri(i, k + 1), ri(i, k)))
                mats.append(mat)
        else:
            for k in range(n_theta):
                faces.append((ri(i, k), ri(i, k + 1), ri(i + 1, k + 1), ri(i + 1, k)))
                mats.append(mat)
    return np.array(verts), faces, mats


# ---------------------------------------------------------------- materials
def principled(name, base=(0.8, 0.8, 0.8, 1.0), metallic=0.0, roughness=0.4,
               ior=1.5, coat=0.0, coat_rough=0.05, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    def setv(key, val):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = val
    setv("Base Color", base)
    setv("Metallic", metallic)
    setv("Roughness", roughness)
    setv("IOR", ior)
    setv("Coat Weight", coat)
    setv("Coat Roughness", coat_rough)
    if emission is not None:
        setv("Emission Color", emission)
        setv("Emission Strength", emission_strength)
    return mat


def add_scale_bump(mat, scale=140.0, strength=0.25, detail=0.0):
    """Voronoi-based fish scale bump for the plastic handle."""
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = 'F1'
    vor.inputs["Scale"].default_value = scale
    nt.links.new(mapping.outputs["Vector"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(ramp.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def add_roughness_variation(mat, base=0.5, variation=0.15, scale=30.0):
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = max(0.0, base - variation)
    mr.inputs["To Max"].default_value = min(1.0, base + variation)
    nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])


def wood_material(name, light=(0.42, 0.27, 0.13, 1.0), dark=(0.24, 0.135, 0.055, 1.0),
                  grain_scale=55.0, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.35, 1.0, 1.0)
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    # long grain lines
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'
    wave.inputs["Scale"].default_value = grain_scale
    wave.inputs["Distortion"].default_value = 14.0
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 2.0
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    # broad tonal variation
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = 'RGBA'
    mix1.inputs["Factor"].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], mix1.inputs["Factor"])
    mix1.inputs["A"].default_value = light
    mix1.inputs["B"].default_value = dark
    # darken the grain lines
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = 'RGBA'
    mix2.blend_type = 'MULTIPLY'
    mix2.inputs["Factor"].default_value = 0.55
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    nt.links.new(ramp.outputs["Color"], mix2.inputs["B"])
    nt.links.new(mix2.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    # subtle bump
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------- scene utils
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def look_at(obj, target):
    import mathutils
    d = mathutils.Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_area_light(name, loc, target, energy, size, color=(1, 1, 1), shape='DISK'):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.color = color
    light.shape = shape
    if shape == 'RECTANGLE':
        light.size = size
        light.size_y = size * 0.7
    else:
        light.size = size
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    look_at(obj, target)
    return obj


def add_camera(name, loc, target, lens=50.0, fstop=4.0, focus_dist=None, sensor=36.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.dof.use_dof = True
    cam.dof.aperture_fstop = fstop
    obj = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    look_at(obj, target)
    if focus_dist is None:
        import mathutils
        focus_dist = (mathutils.Vector(target) - mathutils.Vector(loc)).length
    cam.dof.focus_distance = focus_dist
    return obj
