from array import array
import moderngl
from .utils import read_txt
from .screen import screen

ctx = moderngl.create_context()

quad_buffer = ctx.buffer(data=array('f', [
    # position (x, y), uv coords (x, y)
    -1.0, 1.0, 0.0, 0.0,   # topleft
    1.0, 1.0, 1.0, 0.0,    # topright
    -1.0, -1.0, 0.0, 1.0,  # bottomleft
    1.0, -1.0, 1.0, 1.0,   # bottomright
]))

def surf2tex(surf):
    tex = ctx.texture(surf.get_size(), 4)
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.repeat_x = tex.repeat_y = False
    tex.swizzle = 'BGRA'
    tex.write(surf.get_view('1'))
    return tex

def update_tex(tex, surf):
    tex.write(surf.get_view('1'))
    return tex

class ShaderHandler:

    def __init__(self):
        vert_shader = read_txt('data/scripts/shaders/vert.glsl')
        frag_shader = read_txt('data/scripts/shaders/frag.glsl')
        self.program = ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)
        self.render_object = ctx.vertex_array(self.program, [(quad_buffer, '2f 2f', 'vert', 'texcoord')])
        self.surfs = {}
        self.vars = {}
        self.shader_surfs_ids = {}
        self.used_textures = []

    def render(self):
        self.transfer_surfs()
        self.transfer_vars()
        self.render_object.render(mode=moderngl.TRIANGLE_STRIP)

    def transfer_surfs(self):
        for surf_key, surf in self.surfs.items():
            if surf_key not in self.shader_surfs_ids:
                surf_id = len(self.shader_surfs_ids)
                self.shader_surfs_ids[surf_key] = surf_id
            else:
                surf_id = self.shader_surfs_ids[surf_key]

            tex = surf2tex(surf)
            tex.use(surf_id)
            self.program[surf_key] = surf_id
            self.used_textures.append(tex)

    def release_textures(self):
        for tex in self.used_textures:
            tex.release()
        self.used_textures.clear()

    def transfer_vars(self):
        for key, val in self.vars.items():
            self.program[key] = val

shader_handler = ShaderHandler()
