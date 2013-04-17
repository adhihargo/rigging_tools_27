# Author: Adhi Hargo (cadmus.sw@gmail.com)
# License: GPL v2

import bpy
import math
import rigify
import re
from mathutils import Vector, Matrix

bl_info = {
    "name": "ADH Rigging Tools",
    "author": "Adhi Hargo",
    "version": (1, 0, 0),
    "blender": (2, 65, 0),
    "location": "View3D > Tools > ADH Rigging Tools",
    "description": "Several simple tools to aid rigging.",
    "warning": "",
    "wiki_url": "https://github.com/adhihargo/rigging_tools",
    "tracker_url": "https://github.com/adhihargo/rigging_tools/issues",
    "category": "Rigging"}

bpy.types.Scene.adh_regex_search_pattern = bpy.props.StringProperty(
    name='',
    description='Regular pattern to match against',
    options={'SKIP_SAVE'})
bpy.types.Scene.adh_regex_replacement_string = bpy.props.StringProperty(
    name='',
    description='String to replace each match',
    options={'SKIP_SAVE'})


class ADH_AddSubdivisionSurfaceModifier(bpy.types.Operator):
    """Add subdivision surface modifier to selected objects, if none given yet."""
    bl_idname = 'object.adh_add_subsurf_modifier'
    bl_label = 'Add Subdivision Surface Modifier'
    bl_options = {'REGISTER', 'UNDO'}

    show_viewport = bpy.props.BoolProperty(
        name = 'Show in Viewport',
        default = False,
        description = "Show Subdivision Surface modifier's effect in viewport"
        )

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'\
            and context.selected_objects != []

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects
                  if obj.type == 'MESH']
        for obj in meshes:
            sml = [m for m in obj.modifiers if m.type == 'SUBSURF']
            if sml == []:
                sm = obj.modifiers.new('Subsurf', 'SUBSURF')
                sm.show_viewport = self.show_viewport
                sm.show_expanded = False
            else:
                for sm in sml:
                    sm.show_viewport = self.show_viewport
                    sm.show_expanded = False

        return {'FINISHED'}

class ADH_ApplyLattices(bpy.types.Operator):
    """Applies all lattice modifiers, deletes all shapekeys. Used for lattice-initialized shapekey creation."""
    bl_idname = 'object.adh_apply_lattices'
    bl_label = 'Apply Lattices'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'\
            and context.selected_objects != []\
            and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if obj.data.shape_keys:
            for i in range (len(obj.data.shape_keys.key_blocks), 0, -1):
                obj.active_shape_key_index = i - 1
                bpy.ops.object.shape_key_remove()
        for m in obj.modifiers:
            if m.type == 'LATTICE':
                bpy.ops.object.modifier_apply(modifier=m.name)

        return {'FINISHED'}

class ADH_CopyCustomShapes(bpy.types.Operator):
    """Copies custom shapes from one armature to another (on bones with similar name)."""
    bl_idname = 'object.adh_copy_shapes'
    bl_label = 'Copy Custom Shapes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        non_armatures_selected = [o.type for o in context.selected_objects
                                  if o.type != 'ARMATURE']
        return len(context.selected_objects) >= 2 and not non_armatures_selected

    def execute(self, context):
        src_armature = context.active_object
        dst_armatures = context.selected_objects
        dst_armatures.remove(src_armature)

        for bone in src_armature.pose.bones:
            for armature in dst_armatures:
                try:
                    armature.pose.bones[bone.name].custom_shape =\
                        bone.custom_shape
                except:
                    pass

        return {'FINISHED'}

class ADH_CreateCustomShape(bpy.types.Operator):
    """Creates mesh for custom shape for selected bones, at active bone's position, using its name as suffix."""
    bl_idname = 'object.adh_create_shape'
    bl_label = 'Create Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}

    widget_shape = bpy.props.EnumProperty(
        name = 'Shape',
        items = [('sphere', 'Sphere', '8x4 edges'),
                 ('ring', 'Ring', '24 vertices'),
                 ('square', 'Square', ''),
                 ('triangle', 'Triangle', ''),
                 ('bidirection', 'Bidirection', ''),
                 ('box', 'Box', ''),
                 ('fourways', 'Four-Ways', 'Circle with arrows to four directions - 40 vertices'),
                 ('fourgaps', 'Four-Gaps', 'Broken circle that complements Four-Ways - 20 vertices')])

    widget_size = bpy.props.FloatProperty(
        name = 'Size',
        default = 1.0,
        min = 0,
        max = 2,
        step = 10,
        description = "Widget's scale as relative to bone.",
        )

    widget_pos = bpy.props.FloatProperty(
        name = 'Position',
        default = 0.5,
        min = -.5,
        max = 1.5,
        step = 5,
        precision = 1,
        description = "Widget's position along bone's length. 0.0 = base, 1.0 = tip.",
        )

    widget_rot = bpy.props.FloatProperty(
        name = 'Rotation',
        default = 0,
        min = -90,
        max = 90,
        step = 10,
        precision = 1,
        description = "Widget's rotation along bone's X axis.",
        )

    widget_prefix = bpy.props.StringProperty(
        name = 'Prefix',
        description = "Prefix for the new widget's name",
        default = 'wgt-'
        )

    widget_layers = bpy.props.BoolVectorProperty(
        name = "Layers",
        description = "Object layers where new widgets will be placed",
        subtype = 'LAYER',
        size = 20,
        default = [x == 19 for x in range(0, 20)]
        )

    @classmethod
    def poll(self, context):
        return context.mode == 'POSE'\
            and context.active_pose_bone != None

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.prop(self, 'widget_shape', expand=False, text='')

        col = layout.column(align=1)
        col.prop(self, 'widget_size', slider=True)
        col.prop(self, 'widget_pos', slider=True)
        col.prop(self, 'widget_rot', slider=True)

        col = layout.column(align=1)
        col.label('Prefix:')
        col.prop(self, 'widget_prefix', text='')
        col.label('Layers:')
        col.prop(self, 'widget_layers', text='')

    def create_widget(self, rig, bone_name, bone_transform_name):
        """Creates an empty widget object for a bone, and returns the object. Taken with minor modification from Rigify.
        """
        obj_name = self.widget_prefix + bone_name
        scene = bpy.context.scene
        # Check if it already exists
        if obj_name in scene.objects:
            mesh = bpy.data.meshes.new(obj_name)
            obj = scene.objects[obj_name]
            obj.data = mesh
        else:
            mesh = bpy.data.meshes.new(obj_name)
            obj = bpy.data.objects.new(obj_name, mesh)
            scene.objects.link(obj)

            rigify.utils.obj_to_bone(obj, rig, bone_name)
            obj.layers = self.widget_layers

        return obj



# --------------- Long, boring widget creation functions ---------------

    def create_sphere_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(-0.3535533845424652*size, -0.3535533845424652*size, 2.9802322387695312e-08*size), (-0.5*size, 2.1855694143368964e-08*size, -1.7763568394002505e-15*size), (-0.3535533845424652*size, 0.3535533845424652*size, -2.9802322387695312e-08*size), (4.371138828673793e-08*size, 0.5*size, -2.9802322387695312e-08*size), (-0.24999994039535522*size, -0.3535533845424652*size, 0.2500000596046448*size), (-0.3535533845424652*size, 5.960464477539063e-08*size, 0.35355344414711*size), (-0.24999994039535522*size, 0.3535534143447876*size, 0.2500000298023224*size), (7.968597515173315e-08*size, -0.3535534143447876*size, 0.35355344414711*size), (8.585823962903305e-08*size, 5.960464477539063e-08*size, 0.5000001192092896*size), (7.968597515173315e-08*size, 0.3535534143447876*size, 0.3535533845424652*size), (0.25000008940696716*size, -0.3535533547401428*size, 0.25*size), (0.35355350375175476*size, 5.960464477539063e-08*size, 0.3535533845424652*size), (0.25000008940696716*size, 0.3535534143447876*size, 0.2499999701976776*size), (0.3535534739494324*size, -0.3535534143447876*size, -2.9802322387695312e-08*size), (0.5000001192092896*size, 2.9802315282267955e-08*size, -8.429370268459024e-08*size), (0.3535534739494324*size, 0.3535533845424652*size, -8.940696716308594e-08*size), (0.2500000298023224*size, -0.35355344414711*size, -0.2500000596046448*size), (0.3535533845424652*size, 0.0*size, -0.35355350375175476*size), (0.2500000298023224*size, 0.35355332493782043*size, -0.25000011920928955*size), (-4.494675920341251e-08*size, -0.35355344414711*size, -0.3535534143447876*size), (-8.27291728455748e-08*size, 0.0*size, -0.5*size), (-4.494675920341251e-08*size, 0.3535533845424652*size, -0.3535534739494324*size), (1.2802747306750462e-08*size, -0.5*size, 0.0*size), (-0.25000008940696716*size, -0.35355344414711*size, -0.24999994039535522*size), (-0.35355350375175476*size, 0.0*size, -0.35355332493782043*size), (-0.25000008940696716*size, 0.35355332493782043*size, -0.25*size), ]
            edges = [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (2, 6), (0, 4), (5, 1), (7, 8), (8, 9), (6, 9), (5, 8), (7, 4), (10, 11), (11, 12), (9, 12), (10, 7), (11, 8), (13, 14), (14, 15), (12, 15), (13, 10), (14, 11), (16, 17), (17, 18), (15, 18), (16, 13), (17, 14), (19, 20), (20, 21), (18, 21), (16, 19), (20, 17), (22, 23), (23, 24), (24, 25), (21, 25), (20, 24), (23, 19), (22, 0), (22, 4), (6, 3), (22, 7), (9, 3), (22, 10), (12, 3), (22, 13), (15, 3), (22, 16), (18, 3), (22, 19), (21, 3), (25, 3), (25, 2), (0, 23), (1, 24), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat

            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_ring_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            
            verts = [(0.0*size, 2.9802322387695312e-08*size, 0.5*size), (-0.129409521818161*size, 2.9802322387695312e-08*size, 0.4829629063606262*size), (-0.25*size, 2.9802322387695312e-08*size, 0.4330126941204071*size), (-0.3535533845424652*size, 2.9802322387695312e-08*size, 0.3535533845424652*size), (-0.4330127239227295*size, 1.4901161193847656e-08*size, 0.2499999850988388*size), (-0.4829629063606262*size, 1.4901161193847656e-08*size, 0.1294095367193222*size), (-0.5*size, 3.552713678800501e-15*size, 3.774895063202166e-08*size), (-0.4829629361629486*size, -1.4901161193847656e-08*size, -0.12940946221351624*size), (-0.4330127537250519*size, -1.4901161193847656e-08*size, -0.24999992549419403*size), (-0.3535534739494324*size, -2.9802322387695312e-08*size, -0.35355329513549805*size), (-0.25000011920928955*size, -2.9802322387695312e-08*size, -0.43301263451576233*size), (-0.12940968573093414*size, -2.9802322387695312e-08*size, -0.48296287655830383*size), (-1.9470718370939721e-07*size, -2.9802322387695312e-08*size, -0.5*size), (0.1294093132019043*size, -2.9802322387695312e-08*size, -0.482962965965271*size), (0.2499997913837433*size, -2.9802322387695312e-08*size, -0.43301281332969666*size), (0.3535532057285309*size, -2.9802322387695312e-08*size, -0.3535535931587219*size), (0.43301260471343994*size, -2.9802322387695312e-08*size, -0.25000014901161194*size), (0.48296284675598145*size, -1.4901161193847656e-08*size, -0.12940971553325653*size), (0.5*size, -1.4210854715202004e-14*size, -2.324561449995599e-07*size), (0.482962965965271*size, 1.4901161193847656e-08*size, 0.12940926849842072*size), (0.43301284313201904*size, 1.4901161193847656e-08*size, 0.2499997466802597*size), (0.3535536229610443*size, 2.9802322387695312e-08*size, 0.3535531759262085*size), (0.2500002980232239*size, 2.9802322387695312e-08*size, 0.43301254510879517*size), (0.12940987944602966*size, 2.9802322387695312e-08*size, 0.48296281695365906*size), ]
            edges = [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (10, 9), (11, 10), (12, 11), (13, 12), (14, 13), (15, 14), (16, 15), (17, 16), (18, 17), (19, 18), (20, 19), (21, 20), (22, 21), (23, 22), (0, 23), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat

            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_square_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(0.5*size, -0.5*size, 0.0*size), (-0.5*size, -0.5*size, 0.0*size), (0.5*size, 0.5*size, 0.0*size), (-0.5*size, 0.5*size, 0.0*size), ]
            edges = [(0, 1), (2, 3), (0, 2), (3, 1), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat

            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_triangle_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(0.0*size, 0.0*size, 0.0), (0.6*size, 1.0*size, 0.0), (-0.6*size, 1.0*size, 0.0), ]
            edges = [(1, 2), (0, 1), (2, 0), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat

            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_bidirection_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(0.0*size, -0.5*size, 0.0*size), (0.0*size, 0.5*size, 0.0*size), (0.15000000596046448*size, -0.3499999940395355*size, 0.0*size), (-0.15000000596046448*size, 0.3499999940395355*size, 0.0*size), (0.15000000596046448*size, 0.3499999940395355*size, 0.0*size), (-0.15000000596046448*size, -0.3499999940395355*size, 0.0*size), ]
            edges = [(2, 0), (4, 1), (5, 0), (3, 1), (0, 1), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat

            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_box_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(-0.5*size, -0.5, -0.5*size), (-0.5*size, 0.5, -0.5*size), (0.5*size, 0.5, -0.5*size), (0.5*size, -0.5, -0.5*size), (-0.5*size, -0.5, 0.5*size), (-0.5*size, 0.5, 0.5*size), (0.5*size, 0.5, 0.5*size), (0.5*size, -0.5, 0.5*size), ]
            edges = [(4, 5), (5, 1), (1, 0), (0, 4), (5, 6), (6, 2), (2, 1), (6, 7), (7, 3), (3, 2), (7, 4), (0, 3), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat
            
            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_fourways_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(0.5829628705978394*size, -1.4901161193847656e-08, 0.12940971553325653*size), (-0.129409521818161*size, 2.9802322387695312e-08, -0.4829629063606262*size), (-0.25*size, 2.9802322387695312e-08, -0.4330126941204071*size), (-0.3535533845424652*size, 2.9802322387695312e-08, -0.3535533845424652*size), (-0.4330127239227295*size, 1.4901161193847656e-08, -0.2499999850988388*size), (-0.4829629063606262*size, 1.4901161193847656e-08, -0.1294095367193222*size), (0.5829629898071289*size, 1.4901161193847656e-08, -0.12940926849842072*size), (-0.4829629361629486*size, -1.4901161193847656e-08, 0.12940946221351624*size), (-0.4330127537250519*size, -1.4901161193847656e-08, 0.24999992549419403*size), (-0.3535534739494324*size, -2.9802322387695312e-08, 0.35355329513549805*size), (-0.25000011920928955*size, -2.9802322387695312e-08, 0.43301263451576233*size), (-0.12940968573093414*size, -2.9802322387695312e-08, 0.48296287655830383*size), (-0.12940968573093414*size, -2.9802322387695312e-08, 0.5829628705978394*size), (0.1294093132019043*size, -2.9802322387695312e-08, 0.482962965965271*size), (0.2499997913837433*size, -2.9802322387695312e-08, 0.43301281332969666*size), (0.3535532057285309*size, -2.9802322387695312e-08, 0.3535535931587219*size), (0.43301260471343994*size, -2.9802322387695312e-08, 0.25000014901161194*size), (0.48296284675598145*size, -1.4901161193847656e-08, 0.12940971553325653*size), (0.1294093132019043*size, -2.9802322387695312e-08, 0.5829629898071289*size), (0.482962965965271*size, 1.4901161193847656e-08, -0.12940926849842072*size), (0.43301284313201904*size, 1.4901161193847656e-08, -0.2499997466802597*size), (0.3535536229610443*size, 2.9802322387695312e-08, -0.3535531759262085*size), (0.2500002980232239*size, 2.9802322387695312e-08, -0.43301254510879517*size), (0.12940987944602966*size, 2.9802322387695312e-08, -0.48296281695365906*size), (-0.1941145956516266*size, -2.9802322387695312e-08, 0.5829629898071289*size), (-2.102837726170037e-07*size, -3.218650945768786e-08, 0.7560000419616699*size), (0.19411394000053406*size, -2.9802322387695312e-08, 0.5829629898071289*size), (0.5829628705978394*size, -1.4901161193847656e-08, 0.1941145360469818*size), (0.7560000419616699*size, -1.5347723702281886e-14, 2.5105265422098455e-07*size), (0.5829629898071289*size, 1.4901161193847656e-08, -0.19411394000053406*size), (-0.5829628705978394*size, 1.4901161193847656e-08, -0.19411435723304749*size), (-0.7560000419616699*size, 3.8369309255704715e-15, -4.076887094583981e-08*size), (-0.5829629302024841*size, -1.4901161193847656e-08, 0.19411414861679077*size), (0.0*size, 3.218650945768786e-08, -0.7560000419616699*size), (-0.1941143274307251*size, 2.9802322387695312e-08, -0.5829628109931946*size), (0.1941147744655609*size, 2.9802322387695312e-08, -0.5829628109931946*size), (-0.5829629302024841*size, -1.4901161193847656e-08, 0.12940946221351624*size), (-0.5829628705978394*size, 1.4901161193847656e-08, -0.1294095367193222*size), (0.12940987944602966*size, 2.9802322387695312e-08, -0.5829628109931946*size), (-0.129409521818161*size, 2.9802322387695312e-08, -0.5829628705978394*size), ]
            edges = [(2, 1), (3, 2), (4, 3), (5, 4), (8, 7), (9, 8), (10, 9), (11, 10), (39, 34), (14, 13), (15, 14), (16, 15), (17, 16), (38, 23), (37, 5), (20, 19), (21, 20), (22, 21), (23, 22), (36, 32), (25, 24), (26, 25), (0, 17), (18, 13), (12, 24), (28, 27), (29, 28), (6, 29), (6, 19), (0, 27), (31, 30), (32, 31), (12, 11), (36, 7), (37, 30), (34, 33), (33, 35), (38, 35), (18, 26), (39, 1), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat
            
            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None

    def create_fourgaps_widget(self, rig, bone_name, size=1.0, pos=1.0, rot=0.0, bone_transform_name=None):
        obj = self.create_widget(rig, bone_name, bone_transform_name)
        if obj != None:
            verts = [(-0.1941143274307251*size, 2.9802322387695312e-08, -0.5829628109931946*size), (-0.30721572041511536*size, 3.6622967769517345e-08, -0.532113254070282*size), (-0.4344686269760132*size, 3.6622967769517345e-08, -0.4344686269760132*size), (-0.532113254070282*size, 1.8311483884758673e-08, -0.30721569061279297*size), (-0.5829628705978394*size, 1.4901161193847656e-08, -0.19411435723304749*size), (-0.5829629302024841*size, -1.4901161193847656e-08, 0.19411414861679077*size), (-0.5321133136749268*size, -1.8311483884758673e-08, 0.3072156310081482*size), (-0.43446874618530273*size, -3.6622967769517345e-08, 0.43446850776672363*size), (-0.3072158396244049*size, -3.6622967769517345e-08, 0.5321131348609924*size), (-0.1941145956516266*size, -2.9802322387695312e-08, 0.5829629898071289*size), (0.19411394000053406*size, -2.9802322387695312e-08, 0.5829629898071289*size), (0.30721548199653625*size, -3.6622967769517345e-08, 0.5321133732795715*size), (0.4344683885574341*size, -3.6622967769517345e-08, 0.4344688653945923*size), (0.5321131348609924*size, -3.6622967769517345e-08, 0.3072158992290497*size), (0.5829628705978394*size, -1.4901161193847656e-08, 0.1941145360469818*size), (0.5829629898071289*size, 1.4901161193847656e-08, -0.19411394000053406*size), (0.5321133732795715*size, 1.8311483884758673e-08, -0.3072154223918915*size), (0.43446895480155945*size, 3.6622967769517345e-08, -0.4344683885574341*size), (0.307216078042984*size, 3.6622967769517345e-08, -0.5321130156517029*size), (0.1941147744655609*size, 2.9802322387695312e-08, -0.5829628109931946*size), ]
            edges = [(1, 0), (2, 1), (3, 2), (4, 3), (6, 5), (7, 6), (8, 7), (9, 8), (11, 10), (12, 11), (13, 12), (14, 13), (16, 15), (17, 16), (18, 17), (19, 18), ]
            faces = []
            rot_mat = Matrix.Rotation(math.radians(rot), 4, 'X')
            trans_mat = Matrix.Translation(Vector((0.0, pos, 0.0)))
            mat = trans_mat * rot_mat
            
            mesh = obj.data
            mesh.from_pydata(verts, edges, faces)
            mesh.transform(mat)
            mesh.update()
            mesh.update()
            return obj
        else:
            return None


# ------------ End of long, boring widget creation functions -----------


    def execute(self, context):
        rig = context.active_object
        bone = context.active_pose_bone
        func = getattr(self, "create_%s_widget" % self.widget_shape)
        widget = func(rig, bone.name, self.widget_size, self.widget_pos, self.widget_rot)
        for bone in context.selected_pose_bones:
            bone.custom_shape = widget

        return {'FINISHED'}
            
class ADH_SelectCustomShape(bpy.types.Operator):
    """Selects custom shape object of active bone."""
    bl_idname = 'object.adh_select_shape'
    bl_label = 'Select Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_pose_bone != None\
            and context.active_pose_bone.custom_shape != None

    def execute(self, context):
        bone = context.active_pose_bone
        bone_shape = bone.custom_shape
        shape_layers = [l for l in bone_shape.layers] # can't index on bpy_prop_array
        if bone_shape:
            context.active_object.select = False
            bone_shape.hide = False
            bone_shape.select = True
            context.scene.layers[shape_layers.index(True)] = True
            context.scene.objects.active = bone.custom_shape
        else:
            return {'CANCELLED'}

        return {'FINISHED'}

class ADH_CreateHookBones(bpy.types.Operator):
    """Creates parentless bone for each selected bone, local copy-transformed. Used for lattice deformation."""
    bl_idname = 'object.adh_create_hook_bones'
    bl_label = 'Create Hook Bones'
    bl_options = {'REGISTER', 'UNDO'}

    hook_layers = bpy.props.BoolVectorProperty(
        name = "Hook Layers",
        description = "Armature layers where new hooks will be placed",
        subtype = 'LAYER',
        size = 32,
        default = [x == 30 for x in range(0, 32)]
        )

    @classmethod
    def poll(self, context):
        return context.active_object.type == 'ARMATURE'

    def execute(self, context):
        prev_mode = 'EDIT' if context.mode == 'EDIT_ARMATURE' else context.mode
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in context.selected_bones:
            hook_name = 'hook-%s' % bone.name
            hook = context.active_object.data.edit_bones.new(hook_name)
            hook.head = bone.head
            hook.tail = bone.tail
            hook.bbone_x = bone.bbone_x / 2
            hook.bbone_z = bone.bbone_z / 2
            hook.layers = self.hook_layers
            hook.roll = bone.roll
        bpy.ops.object.mode_set(mode='POSE')
        for bone in context.selected_pose_bones:
            hook = context.active_object.pose.bones['hook-%s' % bone.name]
            ct_constraint = hook.constraints.new('COPY_TRANSFORMS')
            ct_constraint.owner_space = 'LOCAL'
            ct_constraint.target_space = 'LOCAL'
            ct_constraint.target = context.active_object
            ct_constraint.subtarget = bone.name
        bpy.ops.object.mode_set(mode=prev_mode)

        return {'FINISHED'}

class ADH_DisplayWireForSkinnedObjects(bpy.types.Operator):
    """Used to ease bone placement."""
    bl_idname = 'object.adh_display_wire_if_skinned' # Ugly name, sorry.
    bl_label = 'Display Wire For Skinned Objects'
    bl_options = {'REGISTER', 'UNDO'}

    show_wire = bpy.props.BoolProperty(
        name = 'Show Wire',
        default = False,
        description = 'Toggle show wire for all objects using selected armature'
        )

    @classmethod
    def poll(self, context):
        return context.active_object \
            and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature_obj = context.active_object
        affected_objects = []
        
        for obj in context.selectable_objects:
            armature_mod = [m for m in obj.modifiers if
                            m.type == 'ARMATURE' and
                            m.object == armature_obj]
            if armature_mod:
                affected_objects.append(obj)
        
        for obj in affected_objects:
            obj.show_wire = self.show_wire

        return {'FINISHED'}

class ADH_RemoveVertexGroupsUnselectedBones(bpy.types.Operator):
    """Removes all vertex groups other than selected bones.

    Used right after automatic weight assignment, to remove unwanted bone influence."""
    bl_idname = 'object.adh_remove_vertex_groups_unselected_bones'
    bl_label = 'Remove Vertex Groups of Unselected Bones'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_pose_bones != None

    def execute(self, context):
        bone_names = [b.name for b in context.selected_pose_bones]
        affected_objects = [o for o in context.selected_objects
                            if o.type == 'MESH']
        
        for obj in affected_objects:
            for vg in obj.vertex_groups:
                if not vg.name in bone_names:
                    obj.vertex_groups.remove(vg)

        return {'FINISHED'}

class ADH_RenameRegex(bpy.types.Operator):
    """Renames selected objects or bones using regular expressions. Depends on re, standard library module."""
    bl_idname = 'object.adh_rename_regex'
    bl_label = 'Rename Regex'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_objects != []

    def execute(self, context):
        substring_re = re.compile(context.scene.adh_regex_search_pattern)
        if context.mode == 'OBJECT':
            item_list = context.selected_objects
        elif context.mode == 'POSE':
            item_list = context.selected_pose_bones
        elif context.mode == 'EDIT_ARMATURE':
            item_list = context.selected_bones
        else:
            return {'CANCELLED'}

        for item in item_list:
            item.name = substring_re.sub(context.scene.adh_regex_replacement_string,
                                         item.name)

        # In pose mode, operator's result won't show immediately. This
        # solves it somehow: only the View3D area will refresh
        # promptly.
        if context.mode == 'POSE':
            context.area.tag_redraw()

        return {'FINISHED'}

class ADH_SyncObjectDataNameToObject(bpy.types.Operator):
    """Sync an object data's name to the object's. Made it easier to reuse object data among separate files."""
    bl_idname = 'object.adh_sync_data_name_to_object'
    bl_label = 'Sync Object Data Name To Object'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            if obj and obj.data:
                obj.data.name = obj.name

        return {'FINISHED'}

class ADH_SyncCustomShapePositionToBone(bpy.types.Operator):
    """Sync a mesh object's position to each selected bone using it as a custom shape. Depends on Rigify."""
    bl_idname = 'object.adh_sync_shape_position_to_bone'
    bl_label = 'Sync Custom Shape Position to Bone'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_object.type == 'ARMATURE'\
            and context.mode == 'POSE'
    
    def execute(self, context):
        for bone in context.selected_pose_bones:
            obj = bone.custom_shape
            if obj:
                rigify.utils.obj_to_bone(obj, context.active_object,
                                         bone.name)

        return {'FINISHED'}

class ADH_UseSameCustomShape(bpy.types.Operator):
    """Copies active pose bone's custom shape to each selected pose bone."""
    bl_idname = 'object.adh_use_same_shape'
    bl_label = 'Use Same Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.active_pose_bone != None

    def execute(self, context):
        if context.active_pose_bone == None:
            return {'CANCELLED'}

        custom_shape = context.active_pose_bone.custom_shape
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                custom_shape = obj
                break

        for bone in context.selected_pose_bones:
            bone.custom_shape = custom_shape

        return {'FINISHED'}

class ADH_RiggingToolsPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_ADH_rigging_tools'
    bl_label = 'ADH Rigging Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=1)
        col.operator('object.adh_rename_regex')
        col.prop(context.scene, 'adh_regex_search_pattern')
        col.prop(context.scene, 'adh_regex_replacement_string')

        col = layout.column(align=1)
        col.operator('object.adh_add_subsurf_modifier', text='Add Subsurf')
        col.operator('object.adh_apply_lattices')

        col = layout.column(align=1)
        col.operator('object.adh_copy_shapes')
        col.operator('object.adh_use_same_shape')
        col.operator('object.adh_create_shape')
        col.operator('object.adh_select_shape')

        col = layout.column(align=1)
        col.operator('object.adh_create_hook_bones')
        col.operator('object.adh_display_wire_if_skinned', text='Display Wire')
        col.operator('object.adh_remove_vertex_groups_unselected_bones', text='Remove Unselected VG')

        col = layout.column(align=1)
        col.operator('object.adh_sync_data_name_to_object', text='ObData.name <- Ob.name')
        col.operator('object.adh_sync_shape_position_to_bone', text='CustShape.pos <- Bone.pos')

def register():
    bpy.utils.register_module(__name__)
    
def unregister():
    bpy.utils.unregister_module(__name__)

    del bpy.types.Scene.adh_regex_search_pattern
    del bpy.types.Scene.adh_regex_replacement_string

if __name__ == "__main__":
    register()
