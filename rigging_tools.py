# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Author: Adhi Hargo (cadmus.sw@gmail.com)

import bpy
import math
import rigify
import random
import re
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, BoolVectorProperty, EnumProperty,\
    FloatProperty, StringProperty, PointerProperty
from bpy.types import Menu, Operator, Panel
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

PRF_ROOT = "root-"
PRF_TIP = "tip-"
PRF_HOOK = "hook-"
BBONE_BASE_SIZE = 0.01

class ADH_RenameRegex(Operator):
    """Renames selected objects or bones using regular expressions. Depends on re, standard library module."""
    bl_idname = 'object.adh_rename_regex'
    bl_label = 'Rename Regex'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_objects != []

    def execute(self, context):
        props = context.scene.adh_rigging_tools
        search_str = props.regex_search_pattern
        replacement_str = props.regex_replacement_string
        substring_re = re.compile(search_str)
        if context.mode == 'OBJECT':
            item_list = context.selected_objects
        elif context.mode == 'POSE':
            item_list = context.selected_pose_bones
        elif context.mode == 'EDIT_ARMATURE':
            item_list = context.selected_bones
        else:
            return {'CANCELLED'}

        for item in item_list:
            item.name = substring_re.sub(replacement_str, item.name)

        # In pose mode, operator's result won't show immediately. This
        # solves it somehow: only the View3D area will refresh
        # promptly.
        if context.mode == 'POSE':
            context.area.tag_redraw()

        return {'FINISHED'}

class ADH_AddSubdivisionSurfaceModifier(Operator):
    """Add subdivision surface modifier to selected objects, if none given yet."""
    bl_idname = 'mesh.adh_add_subsurf_modifier'
    bl_label = 'Add Subdivision Surface Modifier'
    bl_options = {'REGISTER', 'UNDO'}

    show_viewport = BoolProperty(
        name = 'Show in Viewport',
        default = False,
        description = "Show Subdivision Surface modifier's effect in viewport"
        )

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'\
            and context.selected_objects != []

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
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

class ADH_ApplyLattices(Operator):
    """Applies all lattice modifiers, deletes all shapekeys. Used for lattice-initialized shapekey creation."""
    bl_idname = 'mesh.adh_apply_lattices'
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

class ADH_AbstractMaskOperator:
    MASK_NAME = 'Z_ADH_MASK'

    @classmethod
    def poll(self, context):
        return context.active_object != None\
            and context.active_object.type == 'MESH'

    orig_vg = None

    def save_vg(self, context):
        self.orig_vg = context.object.vertex_groups.active

    def restore_vg(self, context):
        if self.orig_vg:
            context.object.vertex_groups.active_index = self.orig_vg.index

    def setup_mask_modifier(self, context):
        mesh = context.active_object
        mm = mesh.modifiers.get(self.MASK_NAME)
        if not mm or mm.type != 'MASK':
            mm = mesh.modifiers.new(self.MASK_NAME, 'MASK')
        mm.show_render = False
        mm.show_expanded = False
        mm.vertex_group = self.MASK_NAME

class ADH_DeleteMask(Operator, ADH_AbstractMaskOperator):
    """Delete mask and its vertex group."""
    bl_idname = 'mesh.adh_delete_mask'
    bl_label = 'Delete Mask'
    bl_options = {'REGISTER'}

    def execute(self, context):
        mesh = context.active_object

        mm = mesh.modifiers.get(self.MASK_NAME)
        if mm and mm.type == 'MASK':
            mesh.modifiers.remove(mm)

        vg = mesh.vertex_groups.get(self.MASK_NAME)
        if vg:
            mesh.vertex_groups.remove(vg)

        return {'FINISHED'}

class ADH_MaskSelectedVertices(Operator, ADH_AbstractMaskOperator):
    """Add selected vertices to mask"""
    bl_idname = 'mesh.adh_mask_selected_vertices'
    bl_label = 'Mask Selected Vertices'
    bl_options = {'REGISTER'}

    action = EnumProperty(
        name = 'Action',
        items = [('add', 'Add', 'Add selected vertices to mask.'),
                 ('remove', 'Remove', 'Remove selected vertices from mask.'),
                 ('invert', 'Invert', 'Invert mask')],
        default = 'add',
        options = {'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        mesh = context.active_object
        self.save_vg(context)

        if event.shift: self.action = 'remove'
        elif event.ctrl: self.action = 'invert'

        vg = mesh.vertex_groups.get(self.MASK_NAME)
        if not vg:
            vg = mesh.vertex_groups.new(self.MASK_NAME)
        mesh.vertex_groups.active_index = vg.index

        if self.action == 'invert':
            bpy.ops.object.vertex_group_invert()

        self.setup_mask_modifier(context)

        mesh.data.update()
        selected_verts = [vert.index for vert in mesh.data.vertices
                          if vert.select == True]

        if self.action == 'add':
            if context.object.mode == 'EDIT':
                bpy.ops.object.vertex_group_assign()
            else:
                vg.add(selected_verts, 1.0, 'REPLACE')
        elif self.action == 'remove':
            if context.object.mode == 'EDIT':
                bpy.ops.object.vertex_group_remove_from()
            else:
                vg.remove(selected_verts)

        self.restore_vg(context)

        return {'FINISHED'}

class ADH_CopyCustomShapes(Operator):
    """Copies custom shapes from one armature to another (on bones with similar name)."""
    bl_idname = 'armature.adh_copy_shapes'
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

class ADH_UseSameCustomShape(Operator):
    """Copies active pose bone's custom shape to each selected pose bone."""
    bl_idname = 'armature.adh_use_same_shape'
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

class ADH_CreateCustomShape(Operator):
    """Creates mesh for custom shape for selected bones, at active bone's position, using its name as suffix."""
    bl_idname = 'armature.adh_create_shape'
    bl_label = 'Create Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}

    widget_shape = EnumProperty(
        name = 'Shape',
        items = [('sphere', 'Sphere', '8x4 edges'),
                 ('ring', 'Ring', '24 vertices'),
                 ('square', 'Square', ''),
                 ('triangle', 'Triangle', ''),
                 ('bidirection', 'Bidirection', ''),
                 ('box', 'Box', ''),
                 ('fourways', 'Four-Ways', 'Circle with arrows to four directions - 40 vertices'),
                 ('fourgaps', 'Four-Gaps', 'Broken circle that complements Four-Ways - 20 vertices'),
                 ('selected', 'Selected', 'Shape of selected object')])

    widget_size = FloatProperty(
        name = 'Size',
        default = 1.0,
        min = 0,
        max = 2,
        step = 10,
        description = "Widget's scale as relative to bone.")

    widget_pos = FloatProperty(
        name = 'Position',
        default = 0.5,
        min = -.5,
        max = 1.5,
        step = 5,
        precision = 1,
        description = "Widget's position along bone's length. 0.0 = base, 1.0 = tip.")

    widget_rot = FloatProperty(
        name = 'Rotation',
        default = 0,
        min = -90,
        max = 90,
        step = 10,
        precision = 1,
        description = "Widget's rotation along bone's X axis.")

    widget_prefix = StringProperty(
        name = 'Prefix',
        description = "Prefix for the new widget's name",
        default = 'WGT-')

    widget_layers = BoolVectorProperty(
        name = "Layers",
        description = "Object layers where new widgets will be placed",
        subtype = 'LAYER',
        size = 20,
        default = [x == 19 for x in range(0, 20)],
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

    def create_widget_from_object(self, rig, bone, widget_src):
        obj_name = self.widget_prefix + bone.name
        scene = bpy.context.scene

        widget_data = bpy.data.meshes.new_from_object(scene, widget_src,
                                                      True, 'PREVIEW')
        matrix_src = widget_src.matrix_world
        matrix_bone = rig.matrix_world * bone.matrix
        matrix_wgt = matrix_bone.inverted() * matrix_src
        widget_data.transform(matrix_wgt)

        if obj_name in scene.objects:
            obj = scene.objects[obj_name]
            obj.data = mesh
        else:
            obj = bpy.data.objects.new(obj_name, widget_data)
            obj.layers = self.widget_layers
            obj.draw_type = 'WIRE'
            scene.objects.link(obj)

        bone.custom_shape = obj
        rigify.utils.obj_to_bone(obj, rig, bone.name)

        return obj

    def create_widget(self, rig, bone_name, bone_transform_name):
        """Creates an empty widget object for a bone, and returns the object. Taken with minor modification from Rigify.
        """
        obj_name = self.widget_prefix + bone_name
        scene = bpy.context.scene
        # Check if it already exists
        mesh = bpy.data.meshes.new(obj_name)
        if obj_name in scene.objects:
            obj = scene.objects[obj_name]
            obj.data = mesh
        else:
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
        scene = context.scene

        widget = None
        widget_srcs = [obj for obj in context.selected_objects
                       if obj.type == 'MESH']
            
        func = getattr(self, "create_%s_widget" % self.widget_shape, None)
        if func == None and len(widget_srcs) == 1:
            widget = self.create_widget_from_object(rig, bone, widget_srcs[0])
        else:
            widget = func(rig, bone.name,
                          self.widget_size, self.widget_pos, self.widget_rot)

        for bone in context.selected_pose_bones:
            bone.custom_shape = widget

        return {'FINISHED'}
            
    def invoke(self, context, event):
        return self.execute(context)

class ADH_SelectCustomShape(Operator):
    """Selects custom shape object of active bone."""
    bl_idname = 'armature.adh_select_shape'
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

class ADH_CreateHooks(Operator):
    """Creates parentless bone for each selected bones (local copy-transformed) or lattice points."""
    bl_idname = 'armature.adh_create_hooks'
    bl_label = 'Create Hooks'
    bl_options = {'REGISTER', 'UNDO'}

    hook_layers = BoolVectorProperty(
        name = "Hook Layers",
        description = "Armature layers where new hooks will be placed",
        subtype = 'LAYER',
        size = 32,
        default = [x == 30 for x in range(0, 32)]
        )

    invoked = False

    def setup_copy_constraint(self, armature, bone_name):
        bone = armature.pose.bones[bone_name]
        ct_constraint = bone.constraints.new('COPY_TRANSFORMS')
        ct_constraint.owner_space = 'LOCAL'
        ct_constraint.target_space = 'LOCAL'
        ct_constraint.target = armature
        ct_constraint.subtarget = PRF_HOOK + bone_name

    def hook_on_lattice(self, context, lattice, armature):
        objects = context.scene.objects

        prev_lattice_mode = lattice.mode
        bpy.ops.object.mode_set(mode='OBJECT') # Needed for matrix calculation

        armature_mat_inv = armature.matrix_world.inverted()
        lattice_mat = lattice.matrix_world
        global_lat_point_co = lambda p: armature_mat_inv * (lattice_mat * p)
        get_selected_points = lambda lat: [
            point for point in lat.data.points if point.select]
        lattice_pos = get_selected_points(lattice)
        bone_pos = [global_lat_point_co(point.co) for point in lattice_pos]
        bone_names = [
            "%(prefix)s%(lat)s.%(sum)1.1e%(suffix)s" %
            dict(prefix=PRF_HOOK, lat=lattice.name,
                 sum=math.fsum([2*abs(global_lat_point_co(point).x),
                                3*abs(global_lat_point_co(point).y),
                                5*abs(global_lat_point_co(point).z)]),
                 suffix=".R" if global_lat_point_co(point).x < 0\
                 else ".L" if point.x > 0 else "")
            for point in bone_pos]

        objects.active = armature
        prev_mode = armature.mode
        bpy.ops.object.mode_set(mode='EDIT')
        for index, point_co in enumerate(bone_pos):
            bone_name = bone_names[index]
            bone = armature.data.edit_bones.new(bone_name)
            bone.head = point_co
            bone.tail = point_co + Vector([0, 0, BBONE_BASE_SIZE * 5])
            bone.bbone_x = BBONE_BASE_SIZE
            bone.bbone_z = BBONE_BASE_SIZE
            bone.layers = self.hook_layers
            bone.use_deform = False
        armature.data.layers = list(
            map(any, zip(armature.data.layers, self.hook_layers)))
        bpy.ops.object.mode_set(mode=prev_mode)

        objects.active = lattice
        bpy.ops.object.mode_set(mode='EDIT')
        selected_points = get_selected_points(lattice) # previous one lost after toggling
        for point in selected_points:
            point.select = False
        for index, point in enumerate(selected_points):
            bone_name = bone_names[index]
            mod = lattice.modifiers.new(bone_name, 'HOOK')
            mod.object = armature
            mod.subtarget = bone_name
            point.select=True
            bpy.ops.object.hook_assign(modifier=bone_name)
            bpy.ops.object.hook_reset(modifier=bone_name)
            point.select=False
        for point in selected_points:
            point.select = True
        bpy.ops.object.mode_set(mode=prev_lattice_mode)

        return {'FINISHED'}

    def hook_on_bone(self, context, armature):
        prev_mode = armature.mode
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in context.selected_bones:
            hook_name = PRF_HOOK + bone.name
            hook = armature.data.edit_bones.new(hook_name)
            hook.head = bone.head
            hook.tail = bone.tail
            hook.bbone_x = bone.bbone_x * 2
            hook.bbone_z = bone.bbone_z * 2
            hook.layers = self.hook_layers
            hook.use_deform = False
            hook.roll = bone.roll
        bpy.ops.object.mode_set(mode='POSE')
        for bone in context.selected_pose_bones:
            self.setup_copy_constraint(armature, bone.name)
        bpy.ops.object.mode_set(mode=prev_mode)

        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        return context.active_object != None\
            and context.active_object.type in ['ARMATURE', 'LATTICE']

    def draw(self, context):
        layout = self.layout

        if self.invoked:
            return

        row = layout.row(align=True)
        row.prop(self, "hook_layers")

    def execute(self, context):
        obj1 = context.active_object
        if obj1.type == 'LATTICE':
            selected = [obj for obj in context.selected_objects if obj != obj1]
            if not selected:
                return {'CANCELLED'}
            obj2 = selected[0]
            return self.hook_on_lattice(context, obj1, obj2)
        else:
            return self.hook_on_bone(context, obj1)

    def invoke(self, context, event):
        retval = context.window_manager.invoke_props_dialog(self)
        self.invoked = True
        return retval

class ADH_CreateSpokes(Operator):
    """Creates parentless bones in selected armature from the 3D cursor, ending at each selected vertices of active mesh object."""
    bl_idname = 'armature.adh_create_spokes'
    bl_label = 'Create Spokes'
    bl_options = {'REGISTER', 'UNDO'}

    parent = BoolProperty(
        name = "Parent",
        description = "Create parent bone, one for each if armature selected.",
        default = False
        )

    tip = BoolProperty(
        name = "Tracked Tip",
        description = "Create tip bone and insert Damped Track constraint"+\
            " with the tip as target.",
        default = False
        )

    spoke_layers = BoolVectorProperty(
        name = "Spoke Layers",
        description = "Armature layers where spoke bones will be placed",
        subtype = 'LAYER',
        size = 32,
        default = [x == 29 for x in range(0, 32)]
        )

    aux_layers = BoolVectorProperty(
        name = "Parent and Tip Layers",
        description = "Armature layers where spoke tip and parent bones"+\
            " will be placed",
        subtype = 'LAYER',
        size = 32,
        default = [x == 30 for x in range(0, 32)]
        )

    basename = StringProperty(
        name = "Bone Name",
        default = "spoke",
        )

    invoked = False

    def setup_bone_parent(self, armature, bone, parent_bone):
        # Create per-bone parent if no parent set
        if not parent_bone and self.parent:
            parent_bone = armature.data.edit_bones.new(PRF_ROOT + bone.name)
            parent_bone.tail = bone.head + Vector([0, 0, -.05])
            parent_bone.head = bone.head
            parent_bone.bbone_x = bone.bbone_x * 2
            parent_bone.bbone_z = bone.bbone_x * 2
            parent_bone.layers = self.aux_layers
            parent_bone.align_orientation(bone)
            parent_bone.use_deform = False

            delta = parent_bone.head - parent_bone.tail
            parent_bone.head += delta
            parent_bone.tail += delta

        if parent_bone:
            bone.parent = parent_bone
            bone.use_connect = True

    def setup_bone_tip(self, armature, bone):
        if not self.tip:
            return
        tip_bone = armature.data.edit_bones.new(PRF_TIP + bone.name)
        tip_bone.head = bone.tail
        tip_bone.tail = bone.tail + Vector([.05, 0, 0])
        tip_bone.bbone_x = bone.bbone_x * 2
        tip_bone.bbone_z = bone.bbone_z * 2
        tip_bone.align_orientation(bone)
        tip_bone.layers = self.aux_layers
        tip_bone.use_deform = False

    def setup_bone_constraint(self, armature, bone_name):
        if not self.tip:
            return
        pbone = armature.pose.bones[bone_name]
        tip_name = PRF_TIP + bone_name
        dt_constraint = pbone.constraints.new('DAMPED_TRACK')
        dt_constraint.target = armature
        dt_constraint.subtarget = tip_name

    def setup_bone(self, armature, bone_name, head_co, tail_co, parent):
        bone = armature.data.edit_bones.new(bone_name)
        bone.head = head_co
        bone.tail = tail_co
        bone.bbone_x = BBONE_BASE_SIZE
        bone.bbone_z = BBONE_BASE_SIZE
        bone.use_deform = True
        bone.select = True
        bone.layers = self.spoke_layers
        self.setup_bone_parent(armature, bone, parent)
        self.setup_bone_tip(armature, bone)

    def set_armature_layers(self, armature):
        combined_layers = list(
            map(any,
                zip(armature.data.layers, self.spoke_layers, self.aux_layers)
                if (self.parent or self.tip) else
                zip(armature.data.layers, self.spoke_layers)))
        armature.data.layers = combined_layers

    def get_vertex_coordinates(self, mesh, armature):
        # Get vertex coordinates localized to armature's matrix
        mesh.update_from_editmode()
        armature_mat_inv = armature.matrix_world.inverted()
        mesh_mat = mesh.matrix_world
        return [armature_mat_inv * (mesh_mat * vert.co)
                for vert in mesh.data.vertices if vert.select == True]

    def create_spokes(self, context, mesh, armature):
        scene = context.scene

        vert_coordinates = self.get_vertex_coordinates(mesh, armature)
        cursor_co = armature.matrix_world.inverted() * scene.cursor_location

        bpy.ops.object.editmode_toggle()
        scene.objects.active = armature
        prev_mode = armature.mode

        bpy.ops.object.mode_set(mode='EDIT')
        for bone in context.selected_editable_bones:
            bone.select = False

        parent = None
        if self.parent:
            parent = armature.data.edit_bones.new(PRF_ROOT + self.basename)
            parent.head = cursor_co + Vector([0, 0, -1])
            parent.tail = cursor_co
        for index, vert_co in enumerate(vert_coordinates):
            bone_name = "%s.%d" % (self.basename, index)
            self.setup_bone(armature, bone_name, cursor_co, vert_co, parent)

        bpy.ops.object.mode_set(mode='POSE')
        for index in range(len(vert_coordinates)):
            bone_name = "%s.%d" % (self.basename, index)
            self.setup_bone_constraint(armature, bone_name)
        bpy.ops.object.mode_set(mode=prev_mode)

        self.set_armature_layers(armature)

        return {'FINISHED'}

    def create_spoke_tips(self, context, armature):
        prev_mode = armature.mode

        bpy.ops.object.mode_set(mode='EDIT')
        for bone in context.selected_bones:
            self.setup_bone_parent(armature, bone, None)
            self.setup_bone_tip(armature, bone)

        bpy.ops.object.mode_set(mode='POSE')
        for bone in context.selected_pose_bones:
            self.setup_bone_constraint(armature, bone.name)
        bpy.ops.object.mode_set(mode=prev_mode)

        self.set_armature_layers(armature)

        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        active = context.active_object
        return active != None and active.mode in ['EDIT', 'POSE']\
            and active.type in ['MESH', 'ARMATURE']\
            and len(context.selected_objects) <= 2

    def draw(self, context):
        layout = self.layout

        if self.invoked:
            return

        row = layout.row(align=True)
        row.prop(self, "basename")

        row = layout.row(align=True)
        row.prop(self, "parent", toggle=True)
        row.prop(self, "tip", toggle=True)

        column = layout.column()
        column.prop(self, "spoke_layers")

        column = layout.column()
        column.prop(self, "aux_layers")

    def execute(self, context):
        obj1 = context.active_object
        selected = [obj for obj in context.selected_objects if obj != obj1]
        obj2 = selected[0] if selected else None

        if obj1.type == 'MESH' and obj1.mode == 'EDIT'\
                and obj2 and obj2.type == 'ARMATURE':
            return self.create_spokes(context, obj1, obj2)
        elif obj1.type == 'ARMATURE':
            return self.create_spoke_tips(context, obj1)

        return {'CANCELLED'}

    def invoke(self, context, event):
        retval = context.window_manager.invoke_props_dialog(self)
        self.invoked = True
        return retval

class ADH_CreateBoneGroup(Operator):
    """Creates a new bone group named after active bone, consisting of all selected bones."""
    bl_idname = 'armature.adh_create_bone_group'
    bl_label = 'Create Bone Group'
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def random_theme():
        themes = ['THEME01', 'THEME02', 'THEME03', 'THEME04', 'THEME05',
                  'THEME06', 'THEME07', 'THEME08', 'THEME09', 'THEME10',
                  'THEME11', 'THEME12', 'THEME13', 'THEME14', 'THEME15']
        return random.choice(themes)

    @classmethod
    def poll(self, context):
        return context.active_pose_bone != None

    def execute(self, context):
        pose = context.active_object.pose
        bone_name = context.active_pose_bone.name

        bone_groups = [bg for bg in pose.bone_groups if bg.name == bone_name]
        if bone_groups != []:
            pose.bone_groups.active = bone_groups[0]
        else:
            bpy.ops.pose.group_assign()
            pose.bone_groups.active.name = bone_name
        pose.bone_groups.active.color_set = self.random_theme()
        
        return {'FINISHED'}

class ADH_RemoveVertexGroupsUnselectedBones(Operator):
    """Removes all vertex groups other than selected bones.

    Used right after automatic weight assignment, to remove unwanted bone influence."""
    bl_idname = 'armature.adh_remove_vertex_groups_unselected_bones'
    bl_label = 'Remove Vertex Groups of Unselected Bones'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_object != None\
            and context.selected_pose_bones != None

    def execute(self, context):
        bone_names = [b.name for b in context.selected_pose_bones]
        affected_objects = [o for o in context.selected_objects
                            if o.type == 'MESH']
        
        for obj in affected_objects:
            for vg in obj.vertex_groups:
                if not (vg.name in bone_names or vg.lock_weight):
                    obj.vertex_groups.remove(vg)

        return {'FINISHED'}

class ADH_BindToBone(Operator):
    """Binds all selected objects to selected bone, adding armature and vertex group if none exist yet."""
    bl_idname = 'armature.adh_bind_to_bone'
    bl_label = 'Bind Object to Bone'
    bl_options = {'REGISTER', 'UNDO'}

    only_selected = BoolProperty(
        name = "Only Selected",
        description = "Bind only selected vertices.",
        default = False,
        options = {'SKIP_SAVE'})

    @classmethod
    def poll(self, context):
        return len(context.selected_objects) >= 2\
            and context.active_pose_bone != None

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        armature = context.active_object
        bone = context.active_pose_bone
        for mesh in meshes:
            armature_mods = [m for m in mesh.modifiers
                             if m.type == 'ARMATURE' and m.object == armature]
            if not armature_mods:
                am = mesh.modifiers.new('Armature', 'ARMATURE')
                am.object = armature

            vertex_indices = [v.index for v in mesh.data.vertices if v.select]\
                if self.only_selected else range(len(mesh.data.vertices))
            vg = mesh.vertex_groups.get(bone.name, None)
            for other_vg in mesh.vertex_groups:
                if other_vg == vg:
                    continue
                other_vg.remove(vertex_indices)
            if not vg:
                vg = mesh.vertex_groups.new(bone.name)
            vg.add(vertex_indices, 1.0, 'REPLACE')

        return {'FINISHED'}

    def invoke(self, context, event):
        self.only_selected = event.shift
        return self.execute(context)

class ADH_SyncObjectDataNameToObject(Operator):
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

class ADH_SyncCustomShapePositionToBone(Operator):
    """Sync a mesh object's position to each selected bone using it as a custom shape. Depends on Rigify."""
    bl_idname = 'object.adh_sync_shape_position_to_bone'
    bl_label = 'Sync Custom Shape Position to Bone'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_object != None\
            and context.active_object.type == 'ARMATURE'\
            and context.mode == 'POSE'
    
    def execute(self, context):
        for bone in context.selected_pose_bones:
            obj = bone.custom_shape
            if obj:
                rigify.utils.obj_to_bone(obj, context.active_object,
                                         bone.name)

        return {'FINISHED'}

class ADH_RapidPasteDriver(Operator):
    """Paste driver until Escape button is pressed."""
    bl_idname = 'object.adh_rapid_paste_driver'
    bl_label = 'Rapid Paste Driver'
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _space = None

    @classmethod
    def poll(self, context):
        return context.space_data.type == 'PROPERTIES'

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        
        return {'CANCELLED'}

    def modal(self, context, event):
        wm = context.window_manager

        if event.type == 'ESC' or context.space_data != self._space:
            wm.event_timer_remove(self._timer)
            return {'FINISHED'}
        elif event.type == 'TIMER':
            bpy.ops.anim.paste_driver_button()

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        wm = context.window_manager

        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(0.1, context.window)
        self._space = context.space_data

        return {'RUNNING_MODAL'}

class ADH_MapShapeKeysToBones(Operator):
    """Create driver for shape keys, driven by selected bone of the same name."""
    bl_idname = 'object.adh_map_shape_keys_to_bones'
    bl_label = 'Map Shape Keys to Bones'
    bl_options = {'REGISTER', 'UNDO'}

    slider_axis = EnumProperty(
        name = "Slider Axis",
        items = [("LOC_X", "X", "X axis"), ("LOC_Y", "Y", "Y axis"),
                 ("LOC_Z", "Z", "X axis")],
        default = "LOC_X",
    )

    slider_distance = FloatProperty(
        name = "Slider Distance",
        min = -2.0, max = 2.0, default=0.2, step=0.05,
        subtype="DISTANCE", unit="LENGTH",
    )

    @classmethod
    def poll(self, context):
        return context.active_object != None\
            and context.active_object.type in ['MESH', 'LATTICE']\
            and len(context.selected_objects) == 2

    def execute(self, context):
        obj1, obj2 = context.selected_objects
        mesh = obj1.data
        armature = obj2
        if obj2.type in ["MESH", "LATTICE"]:
            mesh = obj2.data
            armature = obj1

        if armature.type != "ARMATURE":
            return {"CANCELLED"}

        mesh_keys = mesh.shape_keys
        if not mesh_keys.animation_data:
            mesh_keys.animation_data_create()

        slider_formula = "a * %0.1f" % (1.0 / self.slider_distance)\
                         if self.slider_distance != 0.0 else "a"
        for shape in mesh_keys.key_blocks:
            # Create driver only if the shape key isn't Basis, the
            # corresponding bone exists and is selected.
            bone = armature.data.bones.get(shape.name, None)
            if shape == mesh_keys.reference_key or not (bone and bone.select):
                continue

            data_path = 'key_blocks["%s"].value' % shape.name
            fc = mesh_keys.driver_add(data_path)

            dv = fc.driver.variables[0] if len(fc.driver.variables) > 0\
                 else fc.driver.variables.new()
            dv.name = "a"
            dv.type = "TRANSFORMS"

            target = dv.targets[0]
            target.id = armature
            target.bone_target = shape.name
            target.data_path = dv.targets[0].data_path
            target.transform_space = "LOCAL_SPACE"
            target.transform_type = self.slider_axis

            fc.driver.type = "SCRIPTED"
            fc.driver.expression = slider_formula

        return {"FINISHED"}

class ADH_CopyDriverSettings(Operator):
    """Copy driver settings."""
    bl_idname = 'anim.adh_copy_driver_settings'
    bl_label = 'Copy Driver Settings'
    bl_options = {'REGISTER', 'UNDO'}

    increment_dict = {}

    @classmethod
    def poll(self, context):
        return context.space_data.type == 'GRAPH_EDITOR'\
            and context.space_data.mode == 'DRIVERS'\
            and context.active_object != None\
            and context.space_data.dopesheet.show_only_selected

    def invoke(self, context, event):
        obj = context.active_object
        props = context.scene.adh_rigging_tools

        self.generate_increment_dict(props.driver_increment_index)
        shape_keys = getattr(obj.data, 'shape_keys', None)
        keyable_list = [shape_keys] if shape_keys else []
        for ms in obj.material_slots:
            if not ms:
                continue
            keyable_list.append(ms.material)
            for ts in ms.material.texture_slots:
                if not ts:
                    continue
                keyable_list.append(ts.texture)
        for ps in obj.particle_systems:
            keyable_list.append(ps.settings)
        keyable_list.append(obj)
        keyable_list.append(obj.data)

        self.process_keyable_list(context, keyable_list)

        return {'FINISHED'}

    def generate_increment_dict(self, increment_list_str):
        increment_dict_re = re.compile(r"(\d+)\D*([+-])\D*(\d+)\D*")

        start_pos = 0
        key = 0
        increment = 0
        while True:
            match_obj = increment_dict_re.search(increment_list_str, start_pos)
            if not match_obj:
                break

            key = int(match_obj.group(1))
            increment = int(match_obj.group(3))
            if(match_obj.group(2) == '-'):
                increment *= -1

            self.increment_dict[key] = increment
            start_pos = match_obj.end()

    def process_keyable_list(self, context, keyable_list):
        props = context.scene.adh_rigging_tools

        driver = None
        index = 1
        for keyable in keyable_list:
            if not keyable or not keyable.animation_data:
                continue
            for fc in keyable.animation_data.drivers:
                if not fc.select:
                    continue
                if driver:
                    self.copy_driver_variables(fc, driver, index)
                    index += 1
                else:
                    driver = fc.driver

    def copy_driver_variables(self, fc, driver, driver_index):
        fc.driver.show_debug_info = driver.show_debug_info
        fc.driver.type = driver.type
        fc.driver.expression = self.substitute_incremented(driver.expression,
                                                           driver_index)

        for dv in fc.driver.variables:
            fc.driver.variables.remove(dv)
        for dv in driver.variables:
            fdv = fc.driver.variables.new()
            fdv.name = dv.name
            fdv.type = dv.type
            target = fdv.targets[0]
            target.bone_target = dv.targets[0].bone_target
            target.id = dv.targets[0].id
            # target.id_type = dv.targets[0].id_type
            target.data_path = dv.targets[0].data_path
            target.transform_space = dv.targets[0].transform_space
            target.transform_type = dv.targets[0].transform_type

    def substitute_incremented(self, expression, multiplier):
        int_re = re.compile(r"\d+")

        start_pos = 0
        match_index = 1
        newExpression = ''
        while True:
            match_obj = int_re.search(expression, start_pos)
            if not match_obj:
                newExpression += expression[start_pos:]
                break

            newExpression += expression[start_pos:match_obj.start()]
            value = int(match_obj.group()) +\
                (self.increment_dict.get(match_index, 0) * multiplier)
            newExpression += str(value)

            match_index += 1
            start_pos = match_obj.end()

        return newExpression


def draw_armature_specials(self, context):
    layout = self.layout
    layout.separator()

    layout.menu("VIEW3D_MT_adh_armature_specials")
    
def draw_object_specials(self, context):
    layout = self.layout
    layout.separator()

    layout.menu("VIEW3D_MT_adh_object_specials")


class GRAPH_PT_adh_rigging_tools(Panel):
    bl_label = 'ADH Rigging Tools'
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        props = context.scene.adh_rigging_tools

        col = layout.column(align=1)
        col.prop(props, 'driver_increment_index')
        col.operator('anim.adh_copy_driver_settings')
        

class VIEW3D_PT_adh_rigging_tools(Panel):
    bl_label = 'ADH Rigging Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Tools'

    def draw(self, context):
        layout = self.layout
        props = context.scene.adh_rigging_tools

        col = layout.column(align=1)
        col.operator('object.adh_rename_regex')
        col.prop(props, 'regex_search_pattern')
        col.prop(props, 'regex_replacement_string')

        toggle_settings = lambda x:\
            dict(icon_only=True, emboss=False, icon='RADIOBUT_ON', text='') \
            if x else \
            dict(icon_only=False, emboss=False, icon='RADIOBUT_OFF')

        row = layout.row()
        row.prop(props, 'show_modifier_tools',
                 **toggle_settings(props.show_modifier_tools))
        if props.show_modifier_tools:
            col = row.column(align=1)
            col.operator('mesh.adh_add_subsurf_modifier', text='Add Subsurf')
            col.operator('mesh.adh_apply_lattices')
            row1 = col.row(align=1)
            row1.operator('mesh.adh_mask_selected_vertices')
            row1.operator('mesh.adh_delete_mask', text='', icon='X_VEC')

        row = layout.row()
        row.prop(props, 'show_custom_shape_tools',
                 **toggle_settings(props.show_custom_shape_tools))
        if props.show_custom_shape_tools:
            col = row.column(align=1)
            col.operator('armature.adh_copy_shapes')
            col.operator('armature.adh_use_same_shape')
            col.operator('armature.adh_create_shape')
            col.operator('armature.adh_select_shape')

        row = layout.row()
        row.prop(props, 'show_bone_tools',
                 **toggle_settings(props.show_bone_tools))
        if props.show_bone_tools:
            col = row.column(align=1)
            row1 = col.row(align=1)
            row1.operator('armature.adh_create_hooks', text='Hooks')
            row1.operator('armature.adh_create_spokes', text='Spokes')
            col.operator('armature.adh_create_bone_group')
            col.operator('armature.adh_remove_vertex_groups_unselected_bones',
                         text='Remove Unselected VG')
            col.operator('armature.adh_bind_to_bone')

        row = layout.row()
        row.prop(props, 'show_sync_tools',
                 **toggle_settings(props.show_sync_tools))
        if props.show_sync_tools:
            col = row.column(align=1)
            col.operator('object.adh_sync_data_name_to_object', text='ObData.name <- Ob.name')
            col.operator('object.adh_sync_shape_position_to_bone', text='CustShape.pos <- Bone.pos')

class VIEW3D_MT_adh_object_specials(Menu):
    bl_label = "ADH Rigging Tools"

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        col = row.column()
        col.operator('object.adh_map_shape_keys_to_bones')

        col = row.column()
        col.operator('object.adh_sync_data_name_to_object', text='ObData.name <- Ob.name')

class VIEW3D_MT_adh_armature_specials(Menu):
    bl_label = "ADH Rigging Tools"
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        
        col = row.column()
        col.operator('armature.adh_use_same_shape')
        col.operator('armature.adh_create_shape')
        col.operator('armature.adh_select_shape')

        col.separator()
        col.operator('object.adh_sync_shape_position_to_bone', text='CustShape.pos <- Bone.pos')

        col = row.column()
        col.operator('armature.adh_create_hooks')
        col.operator('armature.adh_create_spokes')
        col.operator('armature.adh_create_bone_group')
        col.operator('armature.adh_remove_vertex_groups_unselected_bones',
                     text='Remove Unselected VG')
        col.operator('armature.adh_bind_to_bone')

class ADH_RiggingToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # Preferences
    hide_particles_modifier = BoolProperty(
        name = "Hide Particles Modifier")
    hide_multires_modifier = BoolProperty(
        name = "Hide MultiRes Modifier")

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "hide_particles_modifier")
        layout.prop(self, "hide_multires_modifier")

class ADH_RiggingToolsProps(bpy.types.PropertyGroup):
    driver_increment_index = StringProperty(
        name='',
        description='Index of integer within driver expression to increment',
        options={'SKIP_SAVE'})
    regex_search_pattern = StringProperty(
        name='',
        description='Regular pattern to match against',
        options={'SKIP_SAVE'})
    regex_replacement_string = StringProperty(
        name='',
        description='String to replace each match',
        options={'SKIP_SAVE'})
    show_modifier_tools = BoolProperty(
        name='Modifier',
        description='Show modifier tools',
        default=True)
    show_custom_shape_tools = BoolProperty(
        name='Custom Shape',
        description='Show custom shape tools',
        default=True)
    show_bone_tools = BoolProperty(
        name='Bone',
        description='Show bone tools',
        default=True)
    show_sync_tools = BoolProperty(
        name='Sync',
        description='Show sync tools',
        default=True)

@persistent
def turn_off_glsl_handler(dummy):
    # A tweak for my old laptop. FIX when access through
    # bpy.data.window_managers no longer crashes.
    window = bpy.context.window
    if window != None:
        view_areas = [area for area in window.screen.areas
                      if area.type == 'VIEW_3D']
        for area in view_areas:
            area.spaces.active.viewport_shade = 'SOLID'

    scene = bpy.context.scene
    if scene and scene.game_settings.material_mode == 'GLSL':
        scene.game_settings.material_mode = 'MULTITEXTURE'

    prefs = bpy.context.user_preferences.addons[__name__].preferences
    for obj in scene.objects:
        for mod in obj.modifiers:
            if mod.type == "MULTIRES" and prefs.hide_multires_modifier:
                mod.levels = 0
                mod.sculpt_levels = 0
                mod.show_viewport = False
            elif mod.type.startswith("PARTICLE_") and prefs.hide_particles_modifier:
                mod.show_viewport = False

def register():
    bpy.utils.register_module(__name__)

    bpy.types.Scene.adh_rigging_tools = PointerProperty\
        (type = ADH_RiggingToolsProps)
    bpy.app.handlers.load_post.append(turn_off_glsl_handler)
    bpy.types.VIEW3D_MT_object_specials.append(draw_object_specials)
    bpy.types.VIEW3D_MT_armature_specials.append(draw_armature_specials)
    bpy.types.VIEW3D_MT_pose_specials.append(draw_armature_specials)

def unregister():
    bpy.utils.unregister_module(__name__)

    del bpy.types.Scene.adh_rigging_tools
    bpy.app.handlers.load_post.remove(turn_off_glsl_handler)
    bpy.types.VIEW3D_MT_object_specials.remove(draw_object_specials)
    bpy.types.VIEW3D_MT_armature_specials.remove(draw_armature_specials)
    bpy.types.VIEW3D_MT_pose_specials.remove(draw_armature_specials)

if __name__ == "__main__":
    register()
